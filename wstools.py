#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import configargparse
from datetime import datetime
import glob
import json
import math
import re
import requests
import os
import wsclient

# TODO check if server supports wsfunction
# TODO remove all merging stuff, merge on sync, write only one file, update accordingly
# TODO after metadata is in one file: on sync: request submissions via last_changed.

__all__ = ['auth', 'init', 'pull', 'status', 'sync']
LOCAL_CONFIG_FOLDER = '.mdt/'
LOCAL_CONFIG = LOCAL_CONFIG_FOLDER + 'config'
LOCAL_CONFIG_USERS = LOCAL_CONFIG_FOLDER + 'users'
LOCAL_CONFIG_MOODLE = LOCAL_CONFIG_FOLDER + 'moodle'
LOCAL_CONFIG_COURSES = LOCAL_CONFIG_FOLDER + 'courses'
ASSIGNMENT_FOLDER = LOCAL_CONFIG_FOLDER + 'assignments/'
SUBMISSION_FOLDER = LOCAL_CONFIG_FOLDER + 'submissions/'
GRADE_FOLDER = LOCAL_CONFIG_FOLDER + 'grades/'


def create_global_config_file():
    file = ''
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isdir(os.environ['XDG_CONFIG_HOME']):
            file = os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isdir(os.path.expanduser('~/.config')):
        file = os.path.expanduser('~/.config/mdtconfig')
    else:
        file = os.path.expanduser('~/.mdtconfig')
    text = 'could not find global config, creating {}'
    print(text.format(file))
    open(file, 'w').close()
    return file


def find_global_config_file():
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isfile(os.environ['XDG_CONFIG_HOME']+'/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
        return os.path.expanduser('~/.config/mdtconfig')
    elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
        return os.path.expanduser('~/.mdtconfig')
    else:
        return create_global_config_file()


def get_config_file_list():
    global_config = find_global_config_file()
    cfg_files = [global_config]
    work_tree = get_work_tree_root()
    if work_tree is not None:
        # default_config_files order is crucial: work_tree cfg overrides global
        cfg_files.append(work_tree+'/.mdt/config')
    return cfg_files


def get_work_tree_root():
    """ determines the work tree root by looking at the .mdt folder in cwd or parent folders
    :returns the work tree root as String or None
    """
    cwd = os.getcwd()
    repo = None
    while not os.path.isdir('.mdt'):
        if '/' == os.getcwd():
            os.chdir(cwd)
            return None
        os.chdir(os.pardir)
    if os.path.isdir('.mdt'):
        repo = os.getcwd()
    os.chdir(cwd)
    return repo + '/'


def auth():
    import getpass
    import configparser

    password_text = """
      Please insert your Moodle password.
      It will not be saved, it is required to get a token.
      Attention: keep your token safe until MDL-53400 is resolved.
      Until then it CANNOT be reset.
    Password: """
    url_text = """
    The location of you moodle like "moodle.hostname.org"
    Moodle [{}]: """
    user_text = '    Your Moodle username [{}]: '

    [options, unparsed] = config.parse_known_args()

    def get_user_pref(text, option):
        pref = input(text.format(option))

        if pref == '':
            return option
        else:
            return pref

    if options.ask or options.url is None:
        options.url = get_user_pref(url_text, options.url)
    if options.ask or options.user is None:
        options.user = get_user_pref(user_text, options.user)

    password = getpass.getpass(prompt=password_text)

    options.token = wsclient.get_token(options, password=password)
    del password

    reply = wsclient.get_site_info(options)
    options.uid = reply['userid']
    # functions_json = reply['functions']
    # functions = [func_dict['name'] for func_dict in functions_json]
    # print(functions)

    with open(config._default_config_files[0], 'w') as cfgfile:
        del options.subcommand  # don't write subcommand to config
        del options.ask
        cfg_parser = configparser.ConfigParser()
        cfg_parser['global moodle settings'] = options.__dict__
        cfg_parser.write(cfgfile)


def _get_choices_from_list(choices, text):
    """Lets the user choose from a list

    Args:
        choices (list): the list the choose from
        text (str): the text to display for user input
    Returns:
        a list of indices chosen by the user
    """

    digits = str(math.ceil(math.log10(len(choices))))
    format_str = '{:'+digits+'d} {}'
    for n, c in enumerate(choices, 0):
        print(format_str.format(n, c))
    chosen = [int(c) for c in input(text).split()]
    return chosen


def init():
    """initializes working tree: creates local .mdt/config, with chosen courses"""
    [options, unparsed] = config.parse_known_args()

    client = wsclient.MoodleWebServiceClient(
        moodle_hostname=options.url,
        token=options.token
    )

    input_text = '\n  choose courses, seperate with space: '

    if len(config._default_config_files) > 1 and not options.force:
        print('repo already initilized, use --force to overwrite config')
        return

    course_data = wsclient.get_course_list(options, user_id=options.uid)
    course_data_temp = wsclient.get_course_list(options, user_id=options.uid)
    courses = [Course(c) for c in course_data_temp]
    courses.sort(key=lambda course: course.name)
    os.makedirs(LOCAL_CONFIG_FOLDER, exist_ok=True)

    if options.courseids is None or options.force:
        choices = _get_choices_from_list(courses, input_text)
        if len(choices) == 0:
            print('nothing chosen.')
            return
        chosen_courses = [courses[c] for c in choices]
        for c in chosen_courses:
            print(c)
            print('using: ' + c.name)
        options.courseids = [c.id for c in chosen_courses]
        saved_data = [c for c in course_data if c['id'] in options.courseids]
        with open(LOCAL_CONFIG_COURSES, 'w') as course_config:
            json.dump(saved_data, course_config)
    with open(LOCAL_CONFIG, 'w') as config_file:
        config_file.write('courseids = ' + str(options.courseids))


def _write_config(filename, data):
    with open(filename, 'w') as file:
        file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def _sync_assignments(options):
    print('syncing assignments… ', end='', flush=True)
    new_assignments = 0
    updated_assignments = 0
    config_dir = get_work_tree_root() + ASSIGNMENT_FOLDER

    os.makedirs(config_dir, exist_ok=True)
    assignment_list = wsclient.get_assignments(options, course_ids=options.courseids)
    for assignment in assignment_list:
        as_config_file = config_dir+str(assignment['id'])
        if os.path.isfile(as_config_file):
            with open(as_config_file, 'r') as local_file:
                local_as_config = json.load(local_file)
            if local_as_config['timemodified'] < assignment['timemodified']:
                _write_config(as_config_file, assignment)
                updated_assignments += 1
        else:
            _write_config(as_config_file, assignment)
            new_assignments += 1
    print('finished. new: {}, updated: {}, total: {}'.format(
        new_assignments, updated_assignments, str(len(assignment_list))))
    return assignment_list


def _sync_submissions(options):
    print('syncing submissions… ', end='', flush=True)
    config_dir = get_work_tree_root() + SUBMISSION_FOLDER

    os.makedirs(config_dir, exist_ok=True)
    submissions = wsclient.get_submissions(options, assignment_ids=options.assignmentids)
    for assignment in submissions:
        s_config_file = config_dir+str(assignment['assignmentid'])
        _write_config(s_config_file, assignment)
    print('finished: wrote {} submission files'.format(str(len(submissions))))
    return submissions


def _sync_file_meta(options):
    pass


def _sync_grades(options):
    print('syncing grades… ', end='', flush=True)
    config_dir = get_work_tree_root() + GRADE_FOLDER

    os.makedirs(config_dir, exist_ok=True)
    assignments = wsclient.get_grades(options, assignment_ids=options.assignmentids)
    for assignment in assignments:
        g_config_file = config_dir+str(assignment['assignmentid'])
        _write_config(g_config_file, assignment)
    print('finished. total: {}'.format(str(len(assignments))))
    return assignments


def _sync_users(options):
    print('syncing users…', end=' ', flush=True)
    u_config_file = get_work_tree_root() + LOCAL_CONFIG_USERS

    users = []
    for cid in options.courseids:
        users.append(wsclient.get_users(options, course_id=cid))
        print('{:5d}'.format(cid), end=' ', flush=True)

    _write_config(u_config_file, users)
    print('finished.')
    return users


def sync():
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    if get_work_tree_root() is None:
        return
    assignments = _sync_assignments(options)
    options.assignmentids = [a['id'] for a in assignments]
    submissions = _sync_submissions(options)
    grades = _sync_grades(options)
    users = _sync_users(options)


def _merge_json_data_in_folder(path):
    files = glob.glob(path + '*')
    data_list = [_load_json_file(file) for file in files]
    return data_list


def _load_json_file(filename):
    with open(filename) as file:
        return json.load(file)


def _unpack(elements):
    if elements is None:
        return None
    return [elem[0] for elem in elements if type(elem) is list]


def _merge_local_data(wd, courseids):
    courses = _load_json_file(wd + LOCAL_CONFIG_COURSES)
    assignments = _merge_json_data_in_folder(wd + ASSIGNMENT_FOLDER)
    submissions = _merge_json_data_in_folder(wd + SUBMISSION_FOLDER)
    grades = _merge_json_data_in_folder(wd + GRADE_FOLDER)
    users = _load_json_file(wd+LOCAL_CONFIG_USERS)

    merged = []
    for course in courses:
        for ulist in users:
            if ulist['courseid'] == course['id']:
                course['users'] = ulist['users']

        course_assignments = [a for a in assignments if a['course'] == course['id']]

        for assignment in course_assignments:
            for submission in submissions:
                if assignment['id'] == submission['assignmentid']:
                    assignment['submissions'] = submission['submissions']
            for grade in grades:
                if assignment['id'] == grade['assignmentid']:
                    assignment['grades'] = grade['grades']
        course['assignments'] = course_assignments

        merged.append(course)

    return merged


def status():
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    wd = get_work_tree_root()
    if wd is None:
        print('not in workdir, this commands needs to be')
        return

    course_data = _merge_local_data(wd, options.courseids)
    courses = [Course(c) for c in course_data]
    if options.assignmentids is not None and options.submissionids is None:
        for c in sorted(courses):
            print(c)
            assignments = c.get_assignments(options.assignmentids)
            a_status = [a.detailed_status_string() for a in assignments]
            for s in sorted(a_status):
                print(s)
    elif options.submissionids is not None:
        # TODO this.
        for c in sorted(courses):
            print(c)
            assignments = c.get_assignments(options.assignmentids)
            a_status = [a.detailed_status_string() for a in assignments]
            for s in sorted(a_status):
                print(s)
    elif options.full:
        for i in sorted(courses):
            i.print_status()
    else:
        for course in sorted(courses):
            course.print_short_status()


def pull():
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    wd = get_work_tree_root()
    if wd is None:
        print('not in workdir, this commands needs to be')
        return

    # this is for getting file metadata like size and such.
    # comp = re.compile(r'.*pluginfile.php'
    #                   r'/(?P<context_id>[0-9]*)'
    #                   r'/(?P<component>\w+)'
    #                   r'/(?P<file_area>\w+)'
    #                   r'/(?P<item_id>[0-9]*).*')
    # match = comp.match(url)
    # print(wsfunc.get_file_meta(options, **match.groupdict()))

    course_data = _merge_local_data(wd, options.courseids)
    courses = [Course(c) for c in course_data]
    assignments = []
    for c in courses:
        assignments += c.get_assignments(options.assignmentids)
    for a in assignments:
        a.download_files_and_write_html(token=options.token)


def safe_file_name(name):
    return re.sub(r'\W', '_', name)


class Course:
    def __init__(self, data):
        self.id = data.pop('id')
        self.name = data.pop('fullname')
        self.shortname = data.pop('shortname')

        self.users = {}
        self.groups = {}
        if 'users' in data:
            self.update_users(data.pop('users'))

        self.assignments = {}
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
        self.submissions = [Submission(s, assignment=self) for s in data.pop('submissions')]
        self.team_submission = 1 == data.pop('teamsubmission')
        self.due_date = datetime.fromtimestamp(data.pop('duedate'))
        self.name = data.pop('name')
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
        string = ' '*indent + str(self)
        s_status = [s.status_string(indent=indent+1) for s in self.get_valid_submissions()]
        for s in sorted(s_status):
            string += '\n' + s
        return string

    def get_valid_submissions(self):
        return [s for s in self.submissions if s.has_content()]

    def update_grades(self, data):
        grades = [Grade(g) for g in data]
        for g in grades:
            self.grades[g.user_id] = g

    def get_file_urls(self):
        urls = []
        for s in self.get_valid_submissions():
            urls += s.get_file_urls()
        return urls

    def merge_html(self):
        # TODO deduplicate for group submissions
        # TODO use mathjax local, not remote cdn.
        html = '<head><meta charset="UTF-8"></head><body>' \
               '<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>'
        for s in self.get_valid_submissions():
            if s.has_editor_field_content():
                if self.team_submission:
                    group = self.course.groups[s.group_id]
                    html += '\n\n\n<h1>{}</h1>\n\n\n'.format(group.name)
                else:
                    user = self.course.users[s.user_id]
                    html += '\n\n\n<h1>{}</h1>\n\n\n'.format(user.name)
                html += s.get_editor_field_content()
        return html + '</body>'

    def download_files_and_write_html(self, token):
        work_tree = get_work_tree_root()
        args = {'token': token}
        dirname = safe_file_name('{}--{:d}'.format(self.name, self.id))
        os.makedirs(work_tree + dirname, exist_ok=True)
        os.chdir(dirname)
        for file in self.get_file_urls():
            reply = requests.post(file['fileurl'], args)
            print(file['fileurl'])
            with open(os.getcwd() + file['filepath'], 'wb') as out_file:
                out_file.write(reply.content)
        with open(os.getcwd()+'/00_merged_submissions.html', 'w') as merged_html:
            merged_html.write(self.merge_html())

        os.chdir(get_work_tree_root())


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
            self.efields = [Editorfield(e) for e in data.pop('editorfields')]
        if 'fileareas' in data:
            self.fareas = [Filearea(f) for f in data.pop('fileareas')]
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


class Filearea:
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


class Editorfield:
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


config = configargparse.getArgumentParser(name='mdt', default_config_files=get_config_file_list())
config.add_argument('--url')
config.add_argument('--token')
subparsers = config.add_subparsers(help="SUBCMD help")

status_parser = subparsers.add_parser('status', help='display varios information about work tree')
status_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
status_parser.add_argument('-a', '--assignmentids', nargs='+', help='show detailed status for assignment id', type=int)
status_parser.add_argument('-s', '--submissionids', nargs='+', help='show detailed status for submission id', type=int)
status_parser.add_argument('--full', help='display all assignments', action='store_true')

sync_parser = subparsers.add_parser('sync', help='download metadata from server')
sync_parser.add_argument('--url')
sync_parser.add_argument('--token')
sync_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')

init_parser = subparsers.add_parser('init', help='initialize work tree')
init_parser.add_argument('--url')
init_parser.add_argument('--token')
init_parser.add_argument('--uid')
init_parser.add_argument('--force', help='overwrite the config', action='store_true')
init_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')

auth_parser = subparsers.add_parser('auth', help='retrieve access token from server')
auth_parser.add_argument('--url')
auth_parser.add_argument('--token')
auth_parser.add_argument('-u', '--user', help='username', required=False)
auth_parser.add_argument('-s', '--service', help='the webservice, has to be set explicitly', default='moodle_mobile_app')
auth_parser.add_argument('-a', '--ask', help='will ask for all credentials, again', action='store_true')

pull_parser = subparsers.add_parser('pull', help='retrieve files for grading')
pull_parser.add_argument('--url')
pull_parser.add_argument('--token')
pull_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
pull_parser.add_argument('-a', '--assignmentids', nargs='+', type=int, required=True)
pull_parser.add_argument('--all', help='pull all due submissions, even old ones', action='store_true')
