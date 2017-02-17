# interesting things:
# inspect.signature for plugins
# multithreading https://docs.python.org/3/tutorial/stdlib2.html#multi-threading
# also: multiprocessing http://python-3-patterns-idioms-test.readthedocs.io/en/latest/CoroutinesAndConcurrency.html
# unittests https://docs.python.org/3/library/unittest.html
import argparse
import getpass
import json
import logging
import shutil

from frontend import MoodleFrontend
from frontend.models import Course, Assignment
from moodle.fieldnames import JsonFieldNames as Jn, text_format
from persistence.worktree import WorkTree
from util import interaction
from frontend.cmdparser import ParserManager, Argument, ArgumentGroup

log = logging.getLogger('wstools')
pm = ParserManager('wstools', 'internal sub command help')


def make_config_parser():
    return pm.parser


@pm.command(
    'retrieve access token from server',
    Argument('-u', '--username', dest='username', help='username', required=False),
    Argument('--url', help='the moodle host name', required=False),
    Argument('-a', '--ask', help='will ask for all credentials, again', action='store_true'),
    Argument('-s', '--service', help='the webservice, has to be set explicitly, defaults to mobile api',
             default='moodle_mobile_app'),
    Argument('--local', help='write auth info to local config', action='store_true')
)
def auth(url=None, ask=False, username=None, service='moodle_mobile_app', local=False):
    """
    Retreives a Web Service Token for the given user and host and saves it to the global config.

    :param url: the moodle host
    :param ask: set this to true, to get asked for input of known values anyway.
    :param username: the login for which you'd like to retrieve a token for.
    :param service: the configured Web Service, you'd like the token for.
    :param local: write auth info to local file
    :return: nothing.
    """

    _url = 'url'
    _user = 'user_name'
    _service = 'service'

    cfg = WorkTree.get_global_config_values()

    settings = {
        _url: url or cfg.get(_url, None),
        _user: username or cfg.get(_user, None),
        _service: service
    }

    if ask:
        settings[_url] = interaction.input_moodle_url(settings[_url])
        settings[_user] = interaction.input_user_name(settings[_user])
        del ask
    else:
        if settings[_url] is None or settings[_url].strip() == '':
            settings[_url] = interaction.input_moodle_url()

        if settings[_user] is None or settings[_user].strip() == '':
            settings[_user] = interaction.input_user_name()

    password = interaction.input_password()

    token = MoodleFrontend.get_token(settings[_url], settings[_user], password, settings[_service])
    settings[Jn.token] = token
    del password

    # Writing values here once, to allow MoodleFrontend to read from it.
    if not local:
        WorkTree.write_global_config(settings)
    else:
        wt = WorkTree()
        wt.write_local_config(settings)

    frontend = MoodleFrontend(True)
    settings['user_id'] = frontend.get_user_id()

    WorkTree.write_global_config(settings)


@pm.command(
    'initialize work tree',
    Argument('--force', help='overwrite the config', action='store_true'),
    Argument('-c', '--courseids', dest='course_ids', nargs='+', help='moodle course id', action='append')
)
def init(force=False, course_ids=None):
    """initializes working tree: creates local .mdt/config, with chosen courses"""

    try:
        wt = WorkTree(init=True, force=force)
    except FileExistsError:
        print('already initialized, use --force to overwrite or delete .mdt folder')
        raise SystemExit(1)

    # ms = MoodleSession(moodle_url=url, token=token)
    frontend = MoodleFrontend(wt)

    # wrapped = wrappers.CourseListResponse(ms.get_users_course_list(user_id))
    wrapped = frontend.get_course_list()
    courses = list(wrapped)

    courses.sort(key=lambda course: course.full_name)

    saved_data = []
    if course_ids is None or force:
        choices = interaction.input_choices_from_list(courses, '\n  choose courses, seperate with space: ')
        if len(choices) == 0:
            print('nothing chosen.')
            raise SystemExit(0)
        chosen_courses = [courses[c] for c in choices]
        print('using:\n' + ' '.join([str(c) for c in chosen_courses]))
        course_ids = [c.id for c in chosen_courses]
        saved_data = [c for c in wrapped.raw if c['id'] in course_ids]

    wt.courses = saved_data

    wt.write_local_config({'courseids': str(course_ids)})


@pm.command(
    'download metadata from server',
    Argument('-a', '--assignments', help='sync assignments', action='store_true'),
    Argument('-s', '--submissions', help='sync submissions', action='store_true'),
    Argument('-g', '--grades', help='sync grades', action='store_true'),
    Argument('-u', '--users', help='sync users', action='store_true', default=False),
    Argument('-f', '--files', help='sync file metadata', action='store_true', default=False)
)
def sync(assignments=False, submissions=False, grades=False, users=False, files=False):
    frontend = MoodleFrontend()

    sync_all = True
    if users or submissions or assignments or grades or files:
        sync_all = False

    if assignments or sync_all:
        print('syncing assignments… ', end='', flush=True)
        output = frontend.sync_assignments()
        print('finished. ' + ' '.join(output))

    if submissions or sync_all:
        print('syncing submissions… ', end='', flush=True)
        output = frontend.sync_submissions()
        print('finished. ' + ' '.join(output))

    if grades or sync_all:
        print('syncing grades… ', end='', flush=True)
        output = frontend.sync_grades()
        print('finished. ' + ' '.join(output))

    if users or sync_all:
        print('syncing users…', end=' ', flush=True)
        output = frontend.sync_users()
        print(output + 'finished.')

    if files:  # TODO: when finished, add 'or sync_all'
        print('syncing files… ', end='', flush=True)
        frontend.sync_file_meta_data()
        print('finished')


@pm.command(
    'display various information about work tree',
    Argument('-a', '--assignmentids', dest='assignment_ids', nargs='+',
             help='show detailed status for assignment id', type=int),
    Argument('-s', '--submissionids', dest='submission_ids', nargs='+',
             help='show detailed status for submission id', type=int),
    Argument('--full', help='display all assignments', action='store_true')
)
def status(assignment_ids=None, submission_ids=None, full=False):
    wt = WorkTree()
    term_columns = shutil.get_terminal_size().columns

    if assignment_ids is not None and submission_ids is None:
        for assignment_id in assignment_ids:
            assignment = Assignment(wt.assignments[assignment_id])
            assignment.course = Course(wt.courses[assignment.course_id])
            assignment.course.users = wt.users[str(assignment.course_id)]
            assignment.submissions = wt.submissions[assignment_id]
            try:
                assignment.grades = wt.grades[assignment_id]
            except KeyError:
                assignment.grades = None

            print(assignment.course)
            print(assignment.detailed_status_string(indent=1))

    elif submission_ids is not None:
        courses = wt.data
        # TODO this.
        for course in sorted(courses, key=lambda c: c.name):
            print(course)
            assignments = course.sync_assignments(assignment_ids)
            a_status = [a.detailed_status_string() for a in assignments]
            for s in sorted(a_status):
                print(s)
    elif full:
        courses = wt.data
        for course in sorted(courses, key=lambda c: c.name):
            course.print_status()
    else:
        courses = wt.data
        for course in sorted(courses, key=lambda c: c.name):
            course.print_short_status()


@pm.command(
    'retrieve files for grading',
    Argument('assignment_ids', nargs='*', type=int),
    Argument('--all', help='pull all due submissions, even old ones', action='store_true')
)
def pull(assignment_ids=None, all=False):
    frontend = MoodleFrontend()

    frontend.download_files(assignment_ids)


@pm.command(
    'upload grades from files',
    Argument('grading_files', nargs='+', help='files containing grades', type=argparse.FileType())
)
def grade(grading_files):
    frontend = MoodleFrontend()
    upload_data = frontend.parse_grade_files(grading_files)

    frontend.upload_grades(upload_data)


@pm.command(
    'upload files to draft area',
    Argument('files', nargs='+', help='files to upload', type=argparse.FileType('rb'))
)
def upload(files):
    frontend = MoodleFrontend(True)  # TODO: HACK, for not initializing worktree
    frontend.upload_files(files)


@pm.command(
    'enrol in a course',
    Argument('keywords', nargs='+', help='some words to search for')
)
def enrol(keywords):
    frontend = MoodleFrontend(True)
    data = frontend.search_courses_by_keywords(keywords)
    courses = [c for c in data['courses']]
    courses.sort(key=lambda d: d['fullname'])

    print('received {} courses'.format(data['total']))
    course_strs = []
    for course in courses:
        course_strs.append(
            '{:40} {:5d} {:20} {}'.format(course[Jn.full_name][:39], course[Jn.id], course[Jn.short_name][:19],
                                          str(set(course['enrollmentmethods'])))
        )

    choices = interaction.input_choices_from_list(course_strs, '\n  choose one course: ')
    if len(choices) == 0:
        print('nothing chosen.')
        raise SystemExit(1)
    elif len(choices) > 1:
        print('please choose only one, to enrol in')
        raise SystemExit(1)

    chosen_course = courses[choices[0]]
    # print('using:\n' + ' '.join([str(c[Jn.short_name]) for c in chosen_course]))
    # reply = ms.get_course_enrolment_methods(chosen_course[Jn.id])

    enrolment_methods = frontend.get_course_enrolment_methods(chosen_course[Jn.id])
    chosen_method_instance_id = None
    if len(enrolment_methods) > 1:
        print(json.dumps(enrolment_methods, indent=2, sort_keys=True))
        # todo: let user choose enrolment method
        raise NotImplementedError('there are multiple enrolment methods, please send this output as bugreport')
    elif len(enrolment_methods) == 1:
        if enrolment_methods[0][Jn.status]:
            chosen_method_instance_id = enrolment_methods[0][Jn.id]

    if chosen_method_instance_id is None:
        # no active enrolment method
        print('No available enrolment method, sorry')
        raise SystemExit(0)
    # todo: if wsfunction in enrolment method, try that. on accessexception, try without password.
    # todo: if without password fails, possibly warning code 4, then ask for password

    answer = frontend.enrol_in_course(chosen_course[Jn.id], instance_id=chosen_method_instance_id)
    if not answer[Jn.status] and Jn.warnings in answer:
        warning = answer[Jn.warnings][0]
        if warning[Jn.warning_code] == '4':  # wrong password?
            unsuccessful = True
            while unsuccessful:
                print(warning[Jn.message])
                # todo, move to utils.interaction
                password = getpass.getpass(prompt='enrolment key: ')
                data = frontend.enrol_in_course(chosen_course[Jn.id], password=password,
                                                instance_id=chosen_method_instance_id)

                if data[Jn.status]:
                    unsuccessful = False
                    # todo: this is pretty hacky and error prone, fix possibly soon, or maybe not. this has no priority.


@pm.command(
    'submit text or files to assignment for grading',
    Argument('-a', '--assignment_id', help='the assignment id to submit to.'),
    ArgumentGroup('online', 'for online text submission', [
        Argument('-tf', '--textfiles', nargs='+', type=argparse.FileType('rb'),
                 help='files you want in the text. pictures in markdown?'),
        Argument('-t', '--text', type=argparse.FileType(),
                 help='the text file with content you want to submit (txt,md,html)')
    ]),
    ArgumentGroup('files', 'for file submission', [
        Argument('-f', '--files', nargs='+', type=argparse.FileType('rb'), help='the files you want to sumbit.')
    ])
)
def submit(text=None, textfiles=None, files=None, assignment_id=None):
    """ Bei nur Datei Abgabe, keine File ID angegeben. [
    {
    "item": "Es wurde nichts eingereicht.",
    "itemid": 4987,
    "warningcode": "couldnotsavesubmission",
    "message": "Could not save submission."
    }
    ]"""

    def determine_text_format_id(file_name):
        ending = file_name.split('.')[-1]
        if 'md' == ending:
            return text_format['markdown']
        if 'html' == ending:
            return text_format['html']
        if 'txt' == ending:
            return text_format['plain']
        return 0

    frontend = MoodleFrontend()
    file_item_id = 0
    if files is not None:
        file_response = frontend.upload_files(files)
        if file_response.has_errors:
            for error in file_response.errors:
                print(error)
            answer = input('errors occured, continue anyway? [Y/n]: ')
            if 'n' == answer:
                raise SystemExit(0)
            elif not ('y' == answer.lower() or '' == answer):
                print('wat')
                raise SystemExit(1)
        for file in file_response:
            file_item_id = file.item_id
            break

    text_file_item_id = 0
    if textfiles is not None:
        text_file_response = frontend.upload_files(textfiles)
        text_file_item_id = text_file_response[0]['itemid']

    submission_text = ''
    submission_text_format = 0
    if text is not None:
        submission_text = text.read()
        submission_text_format = determine_text_format_id(text.name)

    assignments = []
    if assignment_id is None:
        wt = WorkTree()
        for data in wt.assignments.values():
            assignments.append(Assignment(data))
        choice = interaction.input_choices_from_list(assignments, 'which assignment? ')
        assignment_id = assignments[choice[0]].id

    # print('{:s} {:d} {:d} {:d}'.format(text, submission_text_format, text_file_item_id, file_item_id))
    data = frontend.save_submission(assignment_id, submission_text, submission_text_format, text_file_item_id,
                                    file_item_id)
    print(data)


@pm.command(
    'dump course countents, work in progress'
)
def dump():
    frontend = MoodleFrontend()

    frontend.get_course_content()


@pm.command(
    'dump config'
)
def config():
    print(WorkTree.get_global_config_values())
    for cfg in WorkTree.get_config_file_list():
        print(cfg)
