import os
import requests  # TODO remove all requests, move to communication

from datetime import datetime
import re
from util import worktree
from moodle.fieldnames import JsonFieldNames as Jn
import warnings


class Course:
    def __init__(self, data):
        self.id = data.pop('id')
        self.name = data.pop('fullname')
        self.shortname = data.pop('shortname')

        self.users = {}  # accessed via user.id
        self.groups = {}  # accessed via group.id
        if 'users' in data:
            self.update_users(data.pop('users'))

        self.assignments = {}  # accessed via assignment.id
        if 'assignments' in data:
            self.update_assignments(data.pop('assignments'))

        self.unparsed = data

    def __str__(self):
        return '{:40} id:{:5d} short: {}'.format(self.name[0:39], self.id, self.shortname)

    def print_status(self):
        print(self)
        assignments = [a.short_status_string(indent=1) for a in self.assignments.values()]
        for a in sorted(assignments):
            print(a)

    def print_short_status(self):
        print(self)
        a_status = [a.short_status_string() for a in self.assignments.values() if a.needs_grading()]
        for a in sorted(a_status):
            print(a)

    def get_assignments(self, id_list):
        return [self.assignments[aid] for aid in id_list if aid in self.assignments]

    def update_users(self, data):
        if 'errorcode' in data:
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
        self.name = data.pop('fullname')
        self.id = data.pop('id')
        self.roles = data.pop('roles')

        self.groups = {}
        for g in data.pop('groups'):
            group = Group(g)
            self.groups[group.id] = group

        self.unparsed = data

    def __str__(self):
        return '{:20} id:{:5d} groups:{}'.format(self.name, self.id, str(self.groups))


class Group:
    def __init__(self, data):
        self.name = data.pop('name')
        self.id = data.pop('id')
        self.description = data.pop('description')
        self.descriptionformat = data.pop('descriptionformat')
        self.members = []

    def __str__(self):
        return '{:10} id:{:5d}'.format(self.name, self.id)


class Assignment:
    def __init__(self, data, course=None):
        self.id = data.pop('id')
        self.team_submission = 1 == data.pop('teamsubmission')
        self.due_date = datetime.fromtimestamp(data.pop('duedate'))
        self.name = data.pop('name')
        self.submissions = {}  # accesed via submission.id
        self.max_points = data.pop('grade')  # documentation states, this would be the grade 'type'. Go figure?
        if 'submissions' in data:
            self.update_submissions(data.pop('submissions'))
        self.grades = {}  # are accessed via user_id
        if 'grades' in data:
            self.update_grades(data.pop('grades'))
        self.course = course
        # if len(data) > 1:
        #     print('warning, unparsed assignment data = {}'.format(data.keys()))

        self.unparsed = data

    def __str__(self):
        return '{:40} id:{:5d}'.format(self.name[0:39], self.id)

    def valid_submission_count(self):
        return len(self.get_valid_submissions())

    def is_due(self):
        now = datetime.now()
        diff = now - self.due_date
        ignore_older_than = 25 * 7
        return now > self.due_date and diff.days < ignore_older_than

    def grade_count(self):
        return len(self.grades)

    def needs_grading(self):
        all_graded = False not in [s.is_graded() for s in self.get_valid_submissions()]
        return self.is_due() and not all_graded

    def short_status_string(self, indent=0):
        fmt_string = ' ' * indent + str(self) + ' submissions:{:3d} due:{:1} graded:{:1}'
        return fmt_string.format(self.valid_submission_count(), self.is_due(), not self.needs_grading())

    def detailed_status_string(self, indent=0):
        string = ' ' * indent + str(self)
        s_status = [s.status_string(indent=indent + 1) for s in self.get_valid_submissions()]
        for s in sorted(s_status):
            string += '\n' + s
        return string

    def get_valid_submissions(self):
        return [s for s in self.submissions.values() if s.has_content()]

    def update_grades(self, data):
        grades = [Grade(g) for g in data]
        for g in grades:
            self.grades[g.user_id] = g

    def get_file_urls(self):
        urls = []
        for s in self.get_valid_submissions():
            urls += s.get_file_urls()
        return urls

    def update_submissions(self, data):
        # TODO find out what breaks after this change.
        for submission in data:
            sub = Submission(submission, assignment=self)
            if sub.has_content():
                self.submissions[sub.id] = sub

    def merge_html(self):
        # TODO deduplicate for group submissions
        # TODO use mathjax local, not remote cdn.
        html = '<head><meta charset="UTF-8"></head><body>' \
               '<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>'
        assembled_tmp = []
        for s in self.get_valid_submissions():
            tmp = ''
            if s.has_editor_field_content():
                if self.team_submission:
                    group = self.course.groups[s.group_id]
                    tmp += '\n\n\n<h1>{}</h1>\n\n\n'.format(group.name)
                else:
                    user = self.course.users[s.user_id]
                    html += '\n\n\n<h1>{}</h1>\n\n\n'.format(user.name)
                tmp += s.get_editor_field_content()
            assembled_tmp.append(tmp)
        for i in sorted(assembled_tmp):
            html += i
        return html + '</body>'

    def download_files_and_write_html(self, token):
        warnings.warn(
            "DEPRECATED",
            DeprecationWarning, stacklevel=2
        )

        def _safe_file_name(name):
            return re.sub(r'\W', '_', name)

        work_tree = worktree.get_work_tree_root()
        args = {'token': token}
        assignment_directory = _safe_file_name('{}--{:d}'.format(self.name, self.id))
        os.makedirs(work_tree + assignment_directory, exist_ok=True)
        os.chdir(work_tree + assignment_directory)
        for file in self.get_file_urls():
            reply = requests.post(file['fileurl'], args)
            print(file['fileurl'])
            with open(os.getcwd() + file['filepath'], 'wb') as out_file:
                out_file.write(reply.content)
        with open(os.getcwd() + '/00_merged_submissions.html', 'w') as merged_html:
            merged_html.write(self.merge_html())
        self.write_grading_file()
        os.chdir(work_tree)

    def write_grading_file(self):
        grade_file_head = '{{"assignment_id": {:d}, "grades": [\n'
        grade_file_end = '\n]}'
        grade_line_format = '{{"name": "{}", "id": {:d}, "grade": 0.0, "feedback":"" }}'
        grade_file_content = []
        filename = 'gradingfile.json'
        if self.team_submission:
            for s in self.get_valid_submissions():
                group = self.course.groups[s.group_id]
                grade_file_content.append(grade_line_format.format(group.name, s.id))
        else:
            for s in self.get_valid_submissions():
                user = self.course.users[s.user_id]
                grade_file_content.append(grade_line_format.format(user.name, s.id))
        # checks for existing file and chooses new name, maybe merge data?
        if os.path.isfile(filename):
            new_name = 'gradingfile_{:02d}.json'
            i = 0
            while os.path.isfile(new_name.format(i)):
                i += 1
            filename = new_name.format(i)
            print('grading file exists, writing to: {}'.format(filename))

        with open(filename, 'w') as grading_file:
            grading_file.write(
                grade_file_head.format(self.id) +
                ',\n'.join(sorted(grade_file_content)) +
                grade_file_end
            )

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


class Submission:
    def __init__(self, data, assignment=None):
        self.id = data.pop('id')
        self.user_id = data.pop('userid')
        self.group_id = data.pop('groupid')
        self.plugs = [Plugin(p) for p in data.pop('plugins')]
        self.assignment = assignment
        self.timemodified = data.pop('timemodified')
        self.timecreated = data.pop('timecreated')
        self.status = data.pop('status')
        self.attemptnumber = data.pop('attemptnumber')
        if len(data) > 1:
            print('warning, unparsed submission data = ' + str(data.keys()))
        self.unparsed = data

    def __str__(self):
        return 'id:{:7d} {:5d}:{:5d}'.format(self.id, self.user_id, self.group_id)

    def has_content(self):
        return True in [p.has_content() for p in self.plugs]

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

    def is_graded(self):
        if self.assignment.team_submission:
            return self.is_team_graded()
        else:
            return self.is_single_submission_graded()

    def is_team_graded(self):
        grade, warnings = self.get_grade_or_reason_if_team_ungraded()
        if grade is not None:
            return True
        else:
            return False

    def get_grade_or_reason_if_team_ungraded(self):
        graded_users, ungraded_users = self.get_team_members_and_grades()
        grade_set = set([grade.value for grade in graded_users.values()])
        set_size = len(grade_set)
        warnings = ''
        if len(graded_users) == 0:
            warnings += ' no grades'
        elif len(ungraded_users) > 1:
            warnings += ' has graded and ungraded users'
        if set_size > 1:
            warnings += ' grades not equal: ' + str(grade_set)
        if warnings == '':
            return grade_set.pop(), None
        else:
            return None, warnings

    def status_team_submission_string(self, indent=0):
        if self.group_id not in self.assignment.course.groups:
            return ' ' * indent + str(self) + ' could not find group?'
        group = self.assignment.course.groups[self.group_id]

        grade, warnings = self.get_grade_or_reason_if_team_ungraded()
        if grade is not None:
            return ' ' * indent + '{:20} id:{:7d} grade:{:4}'.format(group.name, self.id, grade)
        else:
            return ' ' * indent + '{:20} id:{:7d} WARNING:{}'.format(group.name, self.id, warnings)

    def is_single_submission_graded(self):
        return self.user_id in self.assignment.grades

    def status_single_submission_string(self, indent=0):
        user = self.assignment.course.users[self.user_id]
        if self.is_graded():
            grade = self.assignment.grades[self.user_id]
            return indent * ' ' + '{:20} grade:{:4}'.format(user.name[0:19], grade.value)
        else:
            return indent * ' ' + '{:20} ungraded'.format(user.name[0:19])

    def has_files(self):
        for p in self.plugs:
            if p.has_files():
                return True
        return False

    def get_file_urls(self):
        urls = []
        for p in self.plugs:
            urls += p.get_file_urls()

        if len(urls) > 1:
            return self.add_folder_prefix(urls)
        else:
            return self.add_file_prefix(urls)

    def has_editor_field_content(self):
        return True in [p.has_efield() for p in self.plugs]

    def get_editor_field_content(self):
        content = ''
        for p in self.plugs:
            if p.has_efield():
                content += p.get_editor_field_content()
        return content

    def get_prefix(self):
        if self.assignment.team_submission:
            group = self.assignment.course.groups[self.group_id]
            return group.name + '--'
        else:
            user = self.assignment.course.users[self.user_id]
            return user.name + '--'

    def add_file_prefix(self, urls):
        prefix = self.get_prefix()
        for u in urls:
            u['filepath'] = '/' + prefix + u['filepath'][1:]
        return urls

    def add_folder_prefix(self, urls):
        prefix = self.get_prefix()
        for u in urls:
            u['filepath'] = prefix + u['filepath']
        return urls


class Grade:
    def __init__(self, data):
        self.id = data.pop('id')
        self.value = float(data.pop('grade'))
        self.grader_id = data.pop('grader')
        self.user_id = data.pop('userid')
        self.attempt_number = data.pop('attemptnumber')
        self.date_created = datetime.fromtimestamp(data.pop('timecreated'))
        self.date_modified = datetime.fromtimestamp(data.pop('timemodified'))
        self.unparsed = data  # should be empty, completely parsed


class Plugin:
    def __init__(self, data):
        self.type = data.pop('type')
        self.name = data.pop('name')
        self.efields = []
        self.fareas = []
        if 'editorfields' in data:
            self.efields = [EditorField(e) for e in data.pop('editorfields')]
        if 'fileareas' in data:
            self.fareas = [FileArea(f) for f in data.pop('fileareas')]
        self.unparsed = data

    def __str__(self):
        if self.has_content():
            out = ''
            plug = 'plugin:[{}] '
            if self.has_efield():
                out += plug.format('efield')
            if self.has_files():
                out += plug.format('files')
            return out
        else:
            return ''

    def has_efield(self):
        return True in [e.has_content() for e in self.efields]

    def has_files(self):
        return True in [f.has_content() for f in self.fareas]

    def has_content(self):
        if self.has_efield() or self.has_files():
            return True
        else:
            return False

    def get_file_urls(self):
        urls = []
        for farea in self.fareas:
            urls += farea.get_file_urls()
        return urls

    def get_editor_field_content(self):
        content = ''
        if self.has_efield():
            for e in self.efields:
                if e.has_content():
                    content += e.get_content()
        return content


class FileArea:
    def __init__(self, data):
        self.area = data.pop('area')
        self.files = []
        if 'files' in data:
            self.files = data.pop('files')
        self.unparsed = data

    def __str__(self):
        out = self.area
        if self.has_content():
            out += ' has {:2d} files'.format(len(self.files))
        return out

    def has_content(self):
        return len(self.files) > 0

    def get_file_urls(self):
        return self.files


class EditorField:
    def __init__(self, data):
        self.data = data
        self.name = data.pop('name')
        self.descr = data.pop('description')
        self.text = data.pop('text')
        self.fmt = data.pop('format')
        self.unparsed = data

    def __str__(self):
        out = '{} {}'.format(self.name, self.descr)
        if self.has_content():
            out += ' has text format {:1d}'.format(self.fmt)
        return out

    def has_content(self):
        return self.text.strip() != ''

    def get_content(self):
        return self.text
