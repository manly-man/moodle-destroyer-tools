from datetime import datetime
from util.werkzeug import cached_property
from moodle.parsers import file_meta_dict_from_url
from moodle.models import JsonDictWrapper, JsonListWrapper
from moodle.models import MoodleAssignment, MoodleCourse, MoodleUser, MoodleGroup, \
    MoodleSubmission, MoodlePlugin, MoodleEditorField, MoodleFileArea, MoodleSubmissionFile, \
    MoodleGrade, MoodleFileMeta


class GlobalConfig(JsonDictWrapper):
    @property
    def service(self): return self['service']

    @property
    def token(self):
        try:
            return self['token']
        except KeyError:
            token_not_found_msg = """
            'url' couldn't be found in your config file.
            Maybe it's corrupted.
            Either check the url in your config file
            or delete the entire file and create a new one.
            """
            raise SystemExit(token_not_found_msg)

    @property
    def user_id(self):
        try:
            return self['user_id']
        except KeyError:
            user_id_not_found_msg = """
            'user_id' couldn't be found in your config file.
            Maybe it's corrupted.
            Either check the url in your config file
            or delete the entire file and create a new one.
            """
            raise SystemExit(user_id_not_found_msg)

    @property
    def url(self):
        try:
            return self['url']
        except KeyError:
            url_not_found_msg = """
            'url' couldn't be found in your config file.
            Maybe it's corrupted.
            Either check the url in your config file
            or delete the entire file and create a new one.
            """
            raise SystemExit(url_not_found_msg)

    @property
    def user_name(self): return self['user_name']


class GradingFile(JsonDictWrapper):
    @property
    def assignment_id(self): return self['assignment_id']

    @property
    def team_submission(self): return self.get('team_submission', False)

    @team_submission.setter
    def team_submission(self, value): self._data['team_submission'] = value

    @property
    def grades(self): return self.GradeList(self['grades'])

    class GradeList(JsonListWrapper):
        def __iter__(self):
            for grade in self._data:
                yield self.Grade(grade)

        class Grade(JsonDictWrapper):
            @property
            def name(self): return self['name']

            @property
            def id(self): return self['id']

            @id.setter
            def id(self, value): self._data['id'] = value

            @property
            def grade(self): return self['grade']

            @property
            def feedback(self): return self['feedback']


class Course(MoodleCourse):
    def __init__(self, data):
        super().__init__(data)
        self._users = {}  # accessed via user.id
        self._groups = {}  # accessed via group.id
        self._assignments = {}

    @property
    def name(self): return self.full_name

    @property
    def users(self): return self._users

    @users.setter
    def users(self, data):
        if data is None:
            self.users = {}
            return
        if 'errorcode' in data:
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
        return '{:40} id:{:5d} short: {}'.format(self.full_name[0:39], self.id, self.short_name)

    def __repr__(self):
        return repr((self.full_name, self.id, self.short_name))

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


class User(MoodleUser):
    def __init__(self, data):
        super().__init__(data)
        self._groups = {}
        self.groups = super().groups.raw

    @property
    def name(self): return self.full_name

    @property
    def groups(self): return self._groups

    @groups.setter
    def groups(self, data):
        for g in data:
            group = Group(g)
            self._groups[group.id] = group

    def __str__(self):
        return '{:20} id:{:5d} groups:{}'.format(self.name, self.id, str(self.groups))


class Group(MoodleGroup):
    def __init__(self, data):
        super().__init__(data)
        self.members = []

    def __str__(self):
        return '{:10} id:{:5d} '.format(self.name, self.id)


class Assignment(MoodleAssignment):
    def __init__(self, data, course=None):
        super().__init__(data)
        self.course = course
        self._submissions = {}  # accessed via submission.id
        self._grades = {}  # are accessed via user_id

    @property
    def due_date(self): return datetime.fromtimestamp(super().due_date)

    @property
    def submissions(self): return self._submissions

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
        # TODO, instead of writing the submission.id, write the user.id instead.
        # TODO, add team_submission to the file, saves work when uploading grades.
        head = '{{"assignment_id": {:d}, "grades": [\n'
        end = '\n]}'
        line_format = '{{"name": "{}", "id": {:d}, "grade": {:3.1f}, "feedback":"" }}'
        content = []

        if self.is_team_submission:
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
        ignore_older_than = 25 * 7  # 25 weeks is approx. half a year.
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
        _configs = {}
        for config in self.configurations:
            if config.sub_type not in _configs:
                _configs[config.sub_type] = {config.plugin: {config.name: config.value}}
            elif config.plugin not in _configs[config.sub_type]:
                _configs[config.sub_type][config.plugin] = {config.name: config.value}
            else:
                _configs[config.sub_type][config.plugin][config.name] = config.value

        string = ''
        for sub_type, config_list in _configs.items():
            string += ' ' * indent + 'cfg-' + sub_type + ': '
            s_config = [plugin+'='+str(config) for plugin, config in config_list.items()]
            string += ', '.join(sorted(s_config))
            string += '\n'
        return string

    @property
    def valid_submissions(self):
        return [s for s in self.submissions.values() if s.has_content]

    @property
    def files(self):
        files = []
        for s in self.valid_submissions:
            files += s.files
        return [s.files for s in self.submissions.values()]

    @property
    def merged_html(self):
        # TODO use mathjax local, not remote cdn. maybe on init or auth?
        # html = ''
        html = '<head><meta charset="UTF-8"></head><body>' \
               '<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>'
        seperator_single = '\n\n\n<h1>{}</h1>\n\n\n'
        seperator_team = '\n\n\n<h1>{} - {}</h1>\n\n\n'
        assembled_tmp = []
        for s in self.valid_submissions:
            tmp = ''
            if s.has_editor_field_content and s.editor_field_content.strip() != '':
                if self.is_team_submission:
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

        html += ''.join(sorted(assembled_tmp))
        return html + '</body>'


class Submission(MoodleSubmission):
    def __init__(self, data, assignment=None):
        super().__init__(data)
        self._plugins = []
        self.assignment = assignment
        self._plugins = [Plugin(p, self) for p in self.plugin_list.raw]

    @property
    def plugins(self):
        return self._plugins

    def __str__(self):
        return 'id:{:7d} {:5d}:{:5d}'.format(self.id, self.user_id, self.group_id)

    @cached_property
    def has_content(self):
        return True in [p.has_content for p in self._plugins]

    def status_string(self, indent=0):
        if self.assignment is None:
            return ' ' * indent + str(self)
        elif self.assignment.is_team_submission and self.assignment.course is not None:
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
        if self.assignment.is_team_submission:
            grade, warnings = self.get_grade_or_reason_if_team_ungraded()
            return grade
        else:
            return self.assignment.grades.get(self.user_id, None)

    @cached_property
    def is_graded(self):
        if self.assignment.is_team_submission:
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
        if self.assignment.is_team_submission:
            group = self.assignment.course.groups[self.group_id]
            return group.name
        else:
            user = self.assignment.course.users[self.user_id]
            return user.name


class Grade(MoodleGrade):
    @property
    def date_created(self): return datetime.fromtimestamp(self.time_created)

    @property
    def date_modified(self): return datetime.fromtimestamp(self.time_modified)

    @property
    def value(self):
        value = self.grade
        if '' == value:
            return None
        else:
            return float(value)


class Plugin(MoodlePlugin):
    def __init__(self, data, submission):
        super().__init__(data)
        self.submission = submission
        self._editor_fields = [EditorField(e) for e in self.editor_fields.raw]
        self._file_areas = [FileArea(a, submission) for a in self.file_areas.raw]

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


class FileArea(MoodleFileArea):
    def __init__(self, data, submission):
        self.submission = submission
        super().__init__(data)
        self._files = [File(file, submission) for file in self.file_list.raw]

#        if Jn.files in self._data:
#            self.set_file_data(self.get(Jn.files))
        self.unparsed = data

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


class File(MoodleSubmissionFile):
    def __init__(self, data, submission):
        super().__init__(data)
        self.submission = submission
        self._new_path = None

    @property
    def path(self):
        if self._new_path is None:
            return self.file_path
        else:
            return self._new_path

    @path.setter
    def path(self, value):
        self._new_path = value

    @property
    def meta_data_params(self): return file_meta_dict_from_url(self.url)


class EditorField(MoodleEditorField):
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


class FileMeta(MoodleFileMeta):
    @property
    def date_created(self): return datetime.fromtimestamp(self.time_created)

    @property
    def date_modified(self): return datetime.fromtimestamp(self.time_modified)
