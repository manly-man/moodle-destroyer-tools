import os

from datetime import datetime
from moodle.fieldnames import JsonFieldNames as Jn


class Course:
    def __init__(self, data):
        self.id = data.pop(Jn.id)
        self.name = data.pop(Jn.full_name)
        self.short_name = data.pop(Jn.short_name)

        self.users = {}  # accessed via user.id
        self.groups = {}  # accessed via group.id
        if Jn.users in data:
            self.update_users(data.pop(Jn.users))

        self.assignments = {}  # accessed via assignment.id
        if Jn.assignments in data:
            self.update_assignments(data.pop(Jn.assignments))

        self.unparsed = data

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

    def update_users(self, data):
        if Jn.error_code in data:
            return
        users = [User(u) for u in data]
        for user in users:
            self.users[user.id] = user
            self.update_groups(user)

    def update_groups(self, user):
        for group_id, group in user.groups.items():
            if group_id not in self.groups:
                self.groups[group_id] = group
            group = self.groups[group_id]
            group.members.append(user)

    def update_assignments(self, data):
        assignments = [Assignment(a, course=self) for a in data]
        for a in assignments:
            self.assignments[a.id] = a


class User:
    def __init__(self, data):
        self.name = data.pop(Jn.full_name)
        self.id = data.pop(Jn.id)
        self.roles = data.pop(Jn.roles)

        self.groups = {}
        for g in data.pop(Jn.groups):
            group = Group(g)
            self.groups[group.id] = group

        self.unparsed = data

    def __str__(self):
        return '{:20} id:{:5d} groups:{}'.format(self.name, self.id, str(self.groups))


class Group:
    def __init__(self, data):
        self.name = data.pop(Jn.name)
        self.id = data.pop(Jn.id)
        self.description = data.pop(Jn.description)
        self.description_format = data.pop(Jn.description_format)
        self.members = []

    def __str__(self):
        return '{:10} id:{:5d}'.format(self.name, self.id)


class Assignment:
    def __init__(self, data, course=None):
        self.id = data.pop(Jn.id)
        self.team_submission = 1 == data.pop(Jn.team_submission)
        self.due_date = datetime.fromtimestamp(data.pop(Jn.due_date))
        self.name = data.pop(Jn.name)
        self.submissions = {}  # accesed via submission.id
        self.max_points = data.pop(Jn.grade)  # documentation states, this would be the grade 'type'. Go figure?
        if Jn.submissions in data:
            self.update_submissions(data.pop(Jn.submissions))
        self.grades = {}  # are accessed via user_id
        if Jn.grades in data:
            self.update_grades(data.pop(Jn.grades))
        self.course = course
        self.configs = {}
        self.update_config(data.pop(Jn.configs))
        self.course_module_id = data.pop(Jn.course_module_id)
        # if len(data) > 1:
        #     print('warning, unparsed assignment data = {}'.format(data.keys()))

        self.unparsed = data

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
        for sub_type, config_list in self.configs.items():
            string += ' ' * indent + 'cfg-' + sub_type + ': '
            s_config = [plugin+'='+str(config) for plugin, config in config_list.items()]
            string += ', '.join(sorted(s_config))
            string += '\n'
        return string

    @property
    def valid_submissions(self):
        return [s for s in self.submissions.values() if s.has_content]

    def update_grades(self, data):
        grades = [Grade(g) for g in data]
        for g in grades:
            self.grades[g.user_id] = g

    def update_config(self, configs):
        for config in configs:
            acfg = AssignmentConfig(config, assignment=self)
            if acfg.sub_type not in self.configs:
                self.configs[acfg.sub_type] = {acfg.plugin: {acfg.name: acfg.value}}
            elif acfg.plugin not in self.configs[acfg.sub_type]:
                self.configs[acfg.sub_type][acfg.plugin] = {acfg.name: acfg.value}
            else:
                self.configs[acfg.sub_type][acfg.plugin][acfg.name] = acfg.value

    @property
    def files(self):
        files = []
        for s in self.valid_submissions:
            files += s.files
        return [s.files for s in self.submissions.values()]

    def update_submissions(self, data):
        # TODO find out what breaks after this change.
        for submission in data:
            sub = Submission(submission, assignment=self)
            if sub.has_content:
                self.submissions[sub.id] = sub

    @property
    def merged_html(self):
        # TODO deduplicate for group submissions? seems unnecessary
        # TODO use mathjax local, not remote cdn. maybe on init or auth?
        html = '<head><meta charset="UTF-8"></head><body>' \
               '<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>'
        seperator = '\n\n\n<h1>{}</h1>\n\n\n'
        assembled_tmp = []
        for s in self.valid_submissions:
            tmp = ''
            if s.has_editor_field_content:
                if self.team_submission:
                    group = self.course.groups[s.group_id]
                    tmp += seperator.format(group.name)
                else:
                    user = self.course.users[s.user_id]
                    tmp += seperator.format(user.name)
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


class AssignmentConfig:
    def __init__(self, data, assignment):
        self.assignment = assignment
        self.id = data.pop(Jn.id)
        self.name = data.pop(Jn.name)
        self.plugin = data.pop(Jn.plugin)
        self.sub_type = data.pop(Jn.sub_type)
        self.value = data.pop(Jn.value)

    def __str__(self):
        return '{}[{}]={}'.format(self.plugin, self.name, self.value)


class Submission:
    def __init__(self, data, assignment=None):
        self.id = data.pop(Jn.id)
        self.user_id = data.pop(Jn.user_id)
        self.group_id = data.pop(Jn.group_id)
        self.plugins = [Plugin(p) for p in data.pop(Jn.plugins)]
        self.assignment = assignment
        self.time_modified = data.pop(Jn.time_modified)
        self.time_created = data.pop(Jn.time_created)
        self.status = data.pop(Jn.status)
        self.attempt_number = data.pop(Jn.attempt_number)
        if len(data) > 1:
            print('warning, unparsed submission data = ' + str(data.keys()))
        self.unparsed = data

    def __str__(self):
        return 'id:{:7d} {:5d}:{:5d}'.format(self.id, self.user_id, self.group_id)

    @property
    def has_content(self):
        return True in [p.has_content for p in self.plugins]

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
        for p in self.plugins:
            if p.has_files:
                return True
        return False

    @property
    def files(self):
        files = []
        for p in self.plugins:
            files += p.files
        return files

    @property
    def has_editor_field_content(self):
        return True in [p.has_editor_field for p in self.plugins]

    @property
    def editor_field_content(self):
        content = ''
        for p in self.plugins:
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


class Grade:
    def __init__(self, data):
        self.id = data.pop(Jn.id)
        value = data.pop(Jn.grade)
        if '' == value:
            self.value = None
        else:
            self.value = float(value)
        self.grader_id = data.pop(Jn.grader)
        self.user_id = data.pop(Jn.user_id)
        self.attempt_number = data.pop(Jn.attempt_number)
        self.date_created = datetime.fromtimestamp(data.pop(Jn.time_created))
        self.date_modified = datetime.fromtimestamp(data.pop(Jn.time_modified))
        self.unparsed = data  # should be empty, completely parsed


class Plugin:
    def __init__(self, data):
        self.type = data.pop(Jn.type)
        self.name = data.pop(Jn.name)
        self.editor_fields = []
        self.file_areas = []
        if Jn.editor_fields in data:
            self.editor_fields = [EditorField(e) for e in data.pop(Jn.editor_fields)]
        if Jn.file_areas in data:
            self.file_areas = [FileArea(f) for f in data.pop(Jn.file_areas)]
        self.unparsed = data

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
        return True in [e.has_content for e in self.editor_fields]

    @property
    def has_files(self):
        return True in [f.has_content for f in self.file_areas]

    @property
    def has_content(self):
        if self.has_editor_field or self.has_files:
            return True
        else:
            return False

    @property
    def files(self):
        file_list = []
        for area in self.file_areas:
            file_list += area.files
        return file_list

    @property
    def editor_field_content(self):
        content = ''
        if self.has_editor_field:
            for e in self.editor_fields:
                if e.has_content:
                    content += e.content
        return content


class FileArea:
    def __init__(self, data):
        self.area = data.pop(Jn.area)
        self._files = []
        if Jn.files in data:
            self.set_file_data(data.pop(Jn.files))
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
        self._files = [File(file) for file in data]


class File:
    def __init__(self, data):
        self.path = data.pop(Jn.file_path)
        self.url = data.pop(Jn.file_url)
        self.prefix = ''
        # TODO metadata attributes

    def add_metadata(self, data):
        pass


class EditorField:
    def __init__(self, data):
        self.name = data.pop(Jn.name)
        self.description = data.pop(Jn.description)
        self.text = data.pop(Jn.text)
        self.fmt = data.pop(Jn.format)
        self.unparsed = data

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
