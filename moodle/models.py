from datetime import datetime
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.parsers import file_meta_dict_from_url


class JsonDataWrapper:
    def __init__(self, json_data):
        self._data = json_data

    def get(self, name):
        try:
            return self._data[name]
        except Exception as e:
            print(name)
            raise e


class Course(JsonDataWrapper):
    def __init__(self, data):
        super().__init__(data)
        self._users = {}  # accessed via user.id
        self._groups = {}  # accessed via group.id
        self._assignments = {}

    @property
    def id(self): return self.get(Jn.id)

    @property
    def name(self): return self.get(Jn.full_name)

    @property
    def short_name(self): return self.get(Jn.short_name)

    @property
    def users(self):
        return self._users

    @users.setter
    def users(self, data):
        if data is None:
            self.users = {}
            return
        if Jn.error_code in data:
            return
        users = [User(u) for u in data]
        for user in users:
            self.users[user.id] = user
            self.groups = user

    @property
    def assignments(self): return self._assignments

    @assignments.setter
    def assignments(self, data):
        if data is None:
            self._assignments = {}
            return
        assignments = [Assignment(a, course=self) for a in data]
        for a in assignments:
            self._assignments[a.id] = a

    @property
    def groups(self): return self._groups

    @groups.setter
    def groups(self, user):
        for group_id, group in user.groups.items():
            if group_id not in self._groups:
                self._groups[group_id] = group
            group = self._groups[group_id]
            group.members.append(user)

    def __str__(self):
        return '{:40} id:{:5d} short: {}'.format(self.name[0:39], self.id, self.short_name)

    def __repr__(self):
        return repr((self.name, self.id, self.short_name))

    def print_status(self):
        print(self)
        assignments = [a.short_status_string(indent=1) for a in self.assignments.values()]
        for a in sorted(assignments):
            print(a)

    def print_short_status(self):
        print(self)
        a_status = [a.short_status_string(indent=1) for a in self.assignments.values() if a.needs_grading]
        for a in sorted(a_status):
            print(a)

    def get_assignments(self, id_list):
        return [a for aid, a in self.assignments.items() if aid in id_list]


class User(JsonDataWrapper):
    def __init__(self, data):
        super().__init__(data)
        self._groups = {}
        self.groups = self.get(Jn.groups)

    @property
    def name(self): return self.get(Jn.full_name)

    @property
    def id(self): return self.get(Jn.id)

    @property
    def roles(self): return self.get(Jn.roles)

    @property
    def groups(self): return self._groups

    @groups.setter
    def groups(self, data):
        for g in data:
            group = Group(g)
            self.groups[group.id] = group

    def __str__(self):
        return '{:20} id:{:5d} groups:{}'.format(self.name, self.id, str(self.groups))


class Group(JsonDataWrapper):
    def __init__(self, data):
        super().__init__(data)
        self.members = []

    @property
    def name(self): return self._data[Jn.name]

    @property
    def id(self): return self._data[Jn.id]

    @property
    def description(self): return self._data[Jn.description]

    @property
    def description_format(self): return self._data[Jn.description_format]

    def __str__(self):
        return '{:10} id:{:5d} '.format(self.name, self.id)


class Assignment(JsonDataWrapper):
    def __init__(self, data, course=None):
        super().__init__(data)
        self.course = course
        self._submissions = {}  # accesed via submission.id
        self._grades = {}  # are accessed via user_id
        self._configs = {}
        self.update_config(self.get(Jn.configs))

    @property
    def id(self): return self.get(Jn.id)

    @property
    def course_id(self): return self.get(Jn.course)

    @property
    def team_submission(self):
        return 1 == self.get(Jn.team_submission)

    @property
    def name(self): return self.get(Jn.name)

    @property
    def max_points(self): return self.get(Jn.grade)  # documentation states, this would be the grade 'type'. Go figure?

    @property
    def due_date(self): return datetime.fromtimestamp(self.get(Jn.due_date))

    @property
    def submissions(self): return self._submissions

    @property
    def course_module_id(self): return self.get(Jn.course_module_id)

    @submissions.setter
    def submissions(self, data):
        if data is None:
            self.submissions = {}
            return
        for submission in data:
            sub = Submission(submission, assignment=self)
            if sub.has_content:
                self.submissions[sub.id] = sub

    @property
    def grades(self):
        return self._grades

    @grades.setter
    def grades(self, data):
        if data is None:
            self.grades = {}
            return
        grades = [Grade(g) for g in data]
        for g in grades:
            self.grades[g.user_id] = g

    @property
    def grading_file_content(self):
        head = '{{"assignment_id": {:d}, "grades": [\n'
        end = '\n]}'
        line_format = '{{"name": "{}", "id": {:d}, "grade": {:3.1f}, "feedback":"" }}'
        content = []

        if self.team_submission:
            for s_id, s in self.submissions.items():
                group = self.course.groups[s.group_id]
                grade = 0.0
                if s.grade is not None:
                    grade = s.grade.value
                content.append(line_format.format(group.name, s.id, grade))
        else:
            for s_id, s in self.submissions.items():
                user = self.course.users[s.user_id]
                grade = 0.0
                if s.grade is not None:
                    grade = s.grade.value
                content.append(line_format.format(user.name, s.id, grade))

        return head.format(self.id) + ',\n'.join(sorted(content)) + end

    def __str__(self):
        return '{:40} id:{:5d}'.format(self.name[0:39], self.id)

    @property
    def valid_submission_count(self):
        return len(self.valid_submissions)

    @property
    def is_due(self):
        now = datetime.now()
        diff = now - self.due_date
        ignore_older_than = 25 * 7
        return now > self.due_date and diff.days < ignore_older_than

    @property
    def grade_count(self):
        return len(self.grades)

    @property
    def needs_grading(self):
        all_graded = False not in [s.is_graded for s in self.valid_submissions]
        return self.is_due and not all_graded

    def short_status_string(self, indent=0):
        fmt_string = ' ' * indent + str(self) + ' submissions:{:3d} due:{:1} graded:{:1}'
        return fmt_string.format(self.valid_submission_count, self.is_due, not self.needs_grading)

    def detailed_status_string(self, indent=0):
        string = ' ' * indent + str(self) + '\n'
        string += self.config_status_string(indent=indent+1)
        s_status = [s.status_string(indent=indent + 1) for s in self.valid_submissions]
        string += '\n'.join(sorted(s_status))
        return string

    def config_status_string(self, indent=0):
        string = ''
        for sub_type, config_list in self._configs.items():
            string += ' ' * indent + 'cfg-' + sub_type + ': '
            s_config = [plugin+'='+str(config) for plugin, config in config_list.items()]
            string += ', '.join(sorted(s_config))
            string += '\n'
        return string

    @property
    def valid_submissions(self):
        return [s for s in self.submissions.values() if s.has_content]

    def update_config(self, configs):
        # todo meh
        for config in configs:
            acfg = AssignmentConfig(config)
            if acfg.sub_type not in self._configs:
                self._configs[acfg.sub_type] = {acfg.plugin: {acfg.name: acfg.value}}
            elif acfg.plugin not in self._configs[acfg.sub_type]:
                self._configs[acfg.sub_type][acfg.plugin] = {acfg.name: acfg.value}
            else:
                self._configs[acfg.sub_type][acfg.plugin][acfg.name] = acfg.value

    @property
    def files(self):
        files = []
        for s in self.valid_submissions:
            files += s.files
        return [s.files for s in self.submissions.values()]

    @property
    def merged_html(self):
        # TODO use mathjax local, not remote cdn. maybe on init or auth?
        html = '<head><meta charset="UTF-8"></head><body>' \
               '<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>'
        seperator_single = '\n\n\n<h1>{}</h1>\n\n\n'
        seperator_team = '\n\n\n<h1>{} - {}</h1>\n\n\n'
        assembled_tmp = []
        for s in self.valid_submissions:
            tmp = ''
            if s.has_editor_field_content:
                if self.team_submission:
                    group = self.course.groups[s.group_id]
                    member_names = [user.name for user in group.members]
                    tmp += seperator_team.format(group.name, ', '.join(member_names))
                else:
                    user = self.course.users[s.user_id]
                    tmp += seperator_single.format(user.name)
                tmp += s.editor_field_content
            assembled_tmp.append(tmp)

        if len(assembled_tmp) == 0:
            return None

        for i in sorted(assembled_tmp):
            html += i
        return html + '</body>'

    def prepare_grade_upload_data(self, data):
        upload_data = {
            'assignment_id': self.id,
            'team_submission': self.team_submission
        }
        for grade_data in data:
            submission = self.submissions[grade_data['id']]
            if self.team_submission:
                group = self.course.groups[submission.group_id]
                user = group.members[0]
                grade_data['user_id'] = user.id
            else:
                grade_data['user_id'] = submission.user_id
        upload_data['grade_data'] = data
        return upload_data


class AssignmentConfig(JsonDataWrapper):

    @property
    def id(self): return self.get(Jn.id)

    @property
    def name(self): return self.get(Jn.name)

    @property
    def plugin(self): return self.get(Jn.plugin)

    @property
    def sub_type(self): return self.get(Jn.sub_type)

    @property
    def value(self): return self.get(Jn.value)

    def __str__(self):
        return '{}[{}]={}'.format(self.plugin, self.name, self.value)


class Submission(JsonDataWrapper):
    def __init__(self, data, assignment=None):
        super().__init__(data)
        self._plugins = []
        self.assignment = assignment
        self._plugins = [Plugin(p, self) for p in self.get(Jn.plugins)]

    @property
    def id(self): return self.get(Jn.id)

    @property
    def user_id(self): return self.get(Jn.user_id)

    @property
    def group_id(self): return self.get(Jn.group_id)

    @property
    def time_modified(self): return self.get(Jn.time_modified)

    @property
    def time_created(self): return self.get(Jn.time_created)

    @property
    def status(self): return self.get(Jn.status)

    @property
    def attempt_number(self): return self.get(Jn.attempt_number)

    @property
    def plugins(self):
        return self._plugins

    def __str__(self):
        return 'id:{:7d} {:5d}:{:5d}'.format(self.id, self.user_id, self.group_id)

    @property
    def has_content(self):
        return True in [p.has_content for p in self._plugins]

    def status_string(self, indent=0):
        if self.assignment is None:
            return ' ' * indent + str(self)
        elif self.assignment.team_submission and self.assignment.course is not None:
            return self.status_team_submission_string(indent=indent)
        else:
            return self.status_single_submission_string(indent=indent)

    def get_team_members_and_grades(self):
        group = self.assignment.course.groups[self.group_id]
        grades = self.assignment.grades
        members = group.members
        graded_users = {}
        ungraded_users = {}
        for user in members:
            if user.id in grades:
                graded_users[user.id] = grades[user.id]
            else:
                ungraded_users[user.id] = user

        return graded_users, ungraded_users

    @property
    def grade(self):
        if self.assignment.team_submission:
            grade, warnings = self.get_grade_or_reason_if_team_ungraded()
            return grade
        else:
            return self.assignment.grades.get(self.user_id, None)

    @property
    def is_graded(self):
        if self.assignment.team_submission:
            return self.is_team_graded
        else:
            return self.is_single_submission_graded

    @property
    def is_team_graded(self):
        grade, warnings = self.get_grade_or_reason_if_team_ungraded()
        if grade is not None:
            return True
        else:
            return False

    def get_grade_or_reason_if_team_ungraded(self):
        graded_users, ungraded_users = self.get_team_members_and_grades()
        grades = [grade for grade in graded_users.values()]
        grade_set = set([grade.value for grade in grades])
        set_size = len(grade_set)
        warnings = ''
        if len(graded_users) == 0:
            warnings += ' no grades'
        elif len(ungraded_users) > 1:
            warnings += ' has graded and ungraded users'
        if set_size > 1:
            warnings += ' grades not equal: ' + str(grade_set)
        if warnings == '':
            return grades.pop(), None
        else:
            return None, warnings

    def status_team_submission_string(self, indent=0):
        if self.group_id not in self.assignment.course.groups:
            return ' ' * indent + str(self) + ' could not find group?'
        group = self.assignment.course.groups[self.group_id]

        grade, warnings = self.get_grade_or_reason_if_team_ungraded()
        grader = 'NAME UNKNOWN?'
        if grade is not None:
            if grade.grader_id in self.assignment.course.users:
                grader = self.assignment.course.users[grade.grader_id].name
            return ' ' * indent + '{:20} id:{:7d} grade:{:4} graded_by:{:10}'.format(group.name, self.id, grade.value, grader)
        else:
            return ' ' * indent + '{:20} id:{:7d} WARNING:{}'.format(group.name, self.id, warnings)

    @property
    def is_single_submission_graded(self):
        return self.user_id in self.assignment.grades

    def status_single_submission_string(self, indent=0):
        user = self.assignment.course.users[self.user_id]
        if self.is_graded:
            grade = self.assignment.grades[self.user_id]
            grader = 'NAME UNKNOWN?'
            if grade.grader_id in self.assignment.course.users:
                grader = self.assignment.course.users[grade.grader_id].name
            return indent * ' ' + '{:20} grade:{:4} graded_by:{:10}'.format(user.name[0:19], grade.value, grader)
        else:
            return indent * ' ' + '{:20} ungraded'.format(user.name[0:19])

    @property
    def has_files(self):
        for p in self._plugins:
            if p.has_files:
                return True
        return False

    @property
    def files(self):
        files = []
        for p in self._plugins:
            files += p.files
        return files

    @property
    def has_editor_field_content(self):
        return True in [p.has_editor_field for p in self._plugins]

    @property
    def editor_field_content(self):
        content = ''
        for p in self._plugins:
            if p.has_editor_field:
                content += p.editor_field_content
        return content

    @property
    def prefix(self):
        if self.assignment.team_submission:
            group = self.assignment.course.groups[self.group_id]
            return group.name
        else:
            user = self.assignment.course.users[self.user_id]
            return user.name


class Grade(JsonDataWrapper):
    @property
    def id(self): return self._data[Jn.id]

    @property
    def grader_id(self): return self._data[Jn.grader]

    @property
    def user_id(self): return self._data[Jn.user_id]

    @property
    def attempt_number(self): return self._data[Jn.attempt_number]

    @property
    def date_created(self): return datetime.fromtimestamp(self._data[Jn.time_created])

    @property
    def date_modified(self): return datetime.fromtimestamp(self._data[Jn.time_modified])

    @property
    def value(self):
        value = self._data[Jn.grade]
        if '' == value:
            return None
        else:
            return float(value)


class Plugin(JsonDataWrapper):
    def __init__(self, data, submission):
        super().__init__(data)
        self._editor_fields = []
        self._file_areas = []
        self.submission = submission
        if Jn.editor_fields in self._data:
            self._editor_fields = [EditorField(e) for e in self.get(Jn.editor_fields)]
        if Jn.file_areas in self._data:
            self._file_areas = [FileArea(f, self.submission) for f in self.get(Jn.file_areas)]

    @property
    def type(self): return self.get(Jn.type)

    @property
    def name(self): return self.get(Jn.name)

    def __str__(self):
        if self.has_content:
            out = ''
            plug = 'plugin:[{}] '
            if self.has_editor_field:
                out += plug.format('efield')
            if self.has_files:
                out += plug.format('files')
            return out
        else:
            return ''

    @property
    def has_editor_field(self):
        return True in [e.has_content for e in self._editor_fields]

    @property
    def has_files(self):
        return True in [f.has_content for f in self._file_areas]

    @property
    def has_content(self):
        if self.has_editor_field or self.has_files:
            return True
        else:
            return False

    @property
    def files(self):
        file_list = []
        for area in self._file_areas:
            file_list += area.files
        return file_list

    @property
    def editor_field_content(self):
        content = ''
        if self.has_editor_field:
            for e in self._editor_fields:
                if e.has_content:
                    content += e.content
        return content


class FileArea(JsonDataWrapper):
    def __init__(self, data, submission):
        super().__init__(data)
        self._files = []
        self.submission = submission
        if Jn.files in self._data:
            self.set_file_data(self.get(Jn.files))
        self.unparsed = data

    @property
    def area(self): return self.get(Jn.area)

    def __str__(self):
        out = self.area
        if self.has_content:
            out += ' has {:2d} files'.format(len(self.files))
        return out

    @property
    def has_content(self):
        return len(self.files) > 0

    @property
    def files(self):
        return self._files

    def set_file_data(self, data):
        self._files = [File(file, self.submission) for file in data]


class File(JsonDataWrapper):
    def __init__(self, data, submission):
        super().__init__(data)
        self.submission = submission
        self._new_path = None

    @property
    def path(self):
        if self._new_path is None:
            return self.get(Jn.file_path)
        else:
            return self._new_path

    @path.setter
    def path(self, value):
        self._new_path = value

    @property
    def url(self): return self.get(Jn.file_url)

    @property
    def meta_data_params(self): return file_meta_dict_from_url(self.url)


class EditorField(JsonDataWrapper):
    @property
    def name(self): return self.get(Jn.name)

    @property
    def description(self): return self.get(Jn.description)

    @property
    def text(self): return self.get(Jn.text)

    @property
    def fmt(self): return self.get(Jn.format)

    def __str__(self):
        out = '{} {}'.format(self.name, self.description)
        if self.has_content:
            out += ' has text format {:1d}'.format(self.fmt)
        return out

    @property
    def has_content(self):
        return self.text.strip() != ''

    @property
    def content(self):
        return self.text


class FileMeta(JsonDataWrapper):
    @property
    def context_id(self): return self.get(Jn.context_id)

    @property
    def component(self): return self.get(Jn.component)

    @property
    def file_area(self): return self.get(Jn.file_area)

    @property
    def item_id(self): return self.get(Jn.item_id)

    @property
    def file_path(self): return self.get(Jn.file_path)

    @property
    def filename(self): return self.get(Jn.file_name)

    @property
    def isdir(self): return self.get(Jn.is_dir)

    @property
    def url(self): return self.get(Jn.url)

    @property
    def time_modified(self): return self.get(Jn.time_modified)

    @property
    def time_created(self): return self.get(Jn.time_created)

    @property
    def file_size(self): return self.get(Jn.file_size)

    @property
    def author(self): return self.get(Jn.author)

    @property
    def license(self): return self.get(Jn.license)
