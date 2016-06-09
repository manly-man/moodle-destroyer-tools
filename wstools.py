#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import configargparse
from moodle.communication import MoodleSession
import glob
import json
import math
import re
import os
import wsclient
from moodle.models import Course

# TODO remove all merging stuff, merge on sync, write only one file, update accordingly
# TODO after metadata is in one file: on sync: request submissions via last_changed.

__all__ = ['auth', 'grade', 'init', 'pull', 'status', 'sync']
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
            file = os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
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
        if os.path.isfile(os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
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
        cfg_files.append(work_tree + '/.mdt/config')
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
    The location of you moodle like "moodle.hostname.org/moodle"
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

    ms = MoodleSession(moodle_url=options.url)
    reply = ms.get_token(user_name=options.user, password=password, service=options.service)
    try:
        j = reply.json()
        options.token = j['token']
        ms.token = options.token
    except KeyError:
        print(j)
        raise SystemExit(1)

    del password

    reply = ms.get_site_info().json()
    options.uid = reply['userid']
    # functions_json = reply['functions']
    # functions = [func_dict['name'] for func_dict in functions_json]
    # print(functions)

    with open(config._default_config_files[0], 'w') as cfgfile:
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
    format_str = '{:' + digits + 'd} {}'
    for n, c in enumerate(choices, 0):
        print(format_str.format(n, c))
    chosen = [int(c) for c in input(text).split()]
    return chosen


def init():
    """initializes working tree: creates local .mdt/config, with chosen courses"""
    [options, unparsed] = config.parse_known_args()

    ms = MoodleSession(moodle_url=options.url, token=options.token)

    input_text = '\n  choose courses, seperate with space: '

    if len(config._default_config_files) > 1 and not options.force:
        print('repo already initilized, use --force to overwrite config')
        return

    course_data = ms.get_users_course_list(options.uid).json()
    course_data_temp = ms.get_users_course_list(options.uid).json()
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
        as_config_file = config_dir + str(assignment['id'])
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
        s_config_file = config_dir + str(assignment['assignmentid'])
        _write_config(s_config_file, assignment)
    print('finished: wrote {} submission files'.format(str(len(submissions))))
    return submissions


def _sync_file_meta(options):
    # TODO, this
    pass


def _sync_grades(options):
    print('syncing grades… ', end='', flush=True)
    config_dir = get_work_tree_root() + GRADE_FOLDER

    os.makedirs(config_dir, exist_ok=True)
    assignments = wsclient.get_grades(options, assignment_ids=options.assignmentids)
    for assignment in assignments:
        g_config_file = config_dir + str(assignment['assignmentid'])
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
    if get_work_tree_root() is None:
        return

    [options, unparsed] = config.parse_known_args()
    course_ids = _unpack(options.courseids)

    for course in course_ids:
        pass
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


def _merge_local_data(wd=get_work_tree_root(), courseids=[]):
    courses = _load_json_file(wd + LOCAL_CONFIG_COURSES)
    assignments = _merge_json_data_in_folder(wd + ASSIGNMENT_FOLDER)
    submissions = _merge_json_data_in_folder(wd + SUBMISSION_FOLDER)
    grades = _merge_json_data_in_folder(wd + GRADE_FOLDER)
    users = _load_json_file(wd + LOCAL_CONFIG_USERS)

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


def grade():
    [options, unparsed] = config.parse_known_args()

    course_data = _merge_local_data()
    courses = [Course(c) for c in course_data]
    grading_data = {}
    for file in options.files:
        # file_content = file.read()
        parsed = json.load(file)
        assignment_id = parsed['assignment_id']
        grading_data[assignment_id] = parsed['grades']

    upload_data = []
    for assignment_id, data in grading_data.items():
        for course in courses:
            if assignment_id in course.assignments:
                assignment = course.assignments[assignment_id]
                upload_data.append(assignment.prepare_grade_upload_data(data))

    print('this will upload the following grades:')
    grade_format = '  {:>20}:{:6d} {:5.1f} > {}'
    for graded_assignment in upload_data:
        print(' assignment {:5d}, teamsubmission: {}'.format(graded_assignment['assignment_id'], graded_assignment['team_submission']))
        for gdata in graded_assignment['grade_data']:
            print(grade_format.format(gdata['name'], gdata['user_id'], gdata['grade'], gdata['feedback'][:40]))
    if 'n' == input('does this look good? [Y/n]: '):
        print('do it right, then')
        return

    for graded_assignment in upload_data:
        as_id = graded_assignment['assignment_id']
        team = graded_assignment['team_submission']
        for gdata in graded_assignment['grade_data']:
            wsclient.set_grade(
                options=options,
                assignment_id=as_id,
                user_id=gdata['user_id'],
                grade=gdata['grade'],
                feedback=gdata['feedback'],
                team_submission=team
            )


def _safe_file_name(name):
    return re.sub(r'\W', '_', name)


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
auth_parser.add_argument('-s', '--service', help='the webservice, has to be set explicitly',
                         default='moodle_mobile_app')
auth_parser.add_argument('-a', '--ask', help='will ask for all credentials, again', action='store_true')

pull_parser = subparsers.add_parser('pull', help='retrieve files for grading')
pull_parser.add_argument('--url')
pull_parser.add_argument('--token')
pull_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
pull_parser.add_argument('-a', '--assignmentids', nargs='+', type=int, required=True)
pull_parser.add_argument('--all', help='pull all due submissions, even old ones', action='store_true')

grade_parser = subparsers.add_parser('grade', help='retrieve files for grading')
grade_parser.add_argument('--url')
grade_parser.add_argument('--token')
grade_parser.add_argument('files', nargs='+', help='files containing grades', type=configargparse.FileType('r'))
