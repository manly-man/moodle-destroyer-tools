#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import json
import configargparse

from moodle.exceptions import AccessDenied
from moodle.communication import MoodleSession
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.models import Course
from moodle.parsers import strip_mlang

from util.worktree import WorkTree
from util import interaction

# TODO on sync: request submissions via last_changed.

__all__ = ['auth', 'config', 'grade', 'init', 'pull', 'status', 'sync', 'upload']


def make_config_parser(work_tree=WorkTree(skip_init=True)):
    parser = configargparse.ArgumentParser(default_config_files=work_tree.get_config_file_list())
    subparsers = parser.add_subparsers(help="internal sub command help")

    url_token_parser = configargparse.ArgumentParser(add_help=False,
                                                     default_config_files=work_tree.get_config_file_list())
    url_token_parser.add_argument('--url')
    url_token_parser.add_argument('--token')

    _make_config_parser_auth(subparsers, url_token_parser)
    _make_config_parser_init(subparsers, url_token_parser)
    _make_config_parser_status(subparsers, url_token_parser)
    _make_config_parser_sync(subparsers, url_token_parser)
    _make_config_parser_pull(subparsers, url_token_parser)
    _make_config_parser_grade(subparsers, url_token_parser)
    _make_config_parser_upload(subparsers, url_token_parser)
    _make_config_parser_config(subparsers, url_token_parser)

    return parser


def _get_options(work_tree=WorkTree(skip_init=True)):
    options, unknown_args = make_config_parser(work_tree).parse_known_args()
    return options


def _make_config_parser_auth(subparsers, url_token_parser):
    auth_parser = subparsers.add_parser(
        'auth',
        help='retrieve access token from server',
        parents=[url_token_parser]
    )
    auth_parser.add_argument('-u', '--user', help='username', required=False)
    auth_parser.add_argument('-s', '--service', help='the webservice, has to be set explicitly',
                             default='moodle_mobile_app')
    auth_parser.add_argument('-a', '--ask', help='will ask for all credentials, again', action='store_true')


def auth():
    wt = WorkTree(skip_init=True)
    _url = 'url'
    _user = 'user'

    options = _get_options(wt)
    settings = {}

    if options.ask:
        settings[_url] = interaction.input_moodle_url(options.url)
        settings[_user] = interaction.input_user_name(options.user)
        del options.ask
    else:
        if options.url is None or options.url == '':
            settings[_url] = interaction.input_moodle_url()
        else:
            settings[_url] = options.url

        if options.user is None or options.user == '':
            settings[_user] = interaction.input_user_name()
        else:
            settings[_user] = options.user

    settings['service'] = options.service

    password = interaction.input_password()

    ms = MoodleSession(moodle_url=settings[_url])
    reply = ms.get_token(user_name=settings[_user], password=password, service=settings['service'])
    del password

    try:
        j = reply.json()
        settings[Jn.token] = j[Jn.token]
        ms.token = settings[Jn.token]
    except KeyError:
        print(reply.text)
        raise SystemExit(1)

    reply = ms.get_site_info().json()
    settings['uid'] = reply[Jn.user_id]
    # functions_json = reply['functions']
    # functions = [func_dict['name'] for func_dict in functions_json]
    # print(functions)

    wt.write_global_config(settings)


def _make_config_parser_init(subparsers, url_token_parser):
    init_parser = subparsers.add_parser(
        'init',
        help='initialize work tree',
        parents=[url_token_parser]
    )
    init_parser.add_argument('--uid')
    init_parser.add_argument('--force', help='overwrite the config', action='store_true')
    init_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')


def init():
    """initializes working tree: creates local .mdt/config, with chosen courses"""
    options = _get_options()

    try:
        wt = WorkTree(init=True, force=options.force)
    except FileExistsError:
        print('already initialized')
        raise SystemExit(1)

    ms = MoodleSession(moodle_url=options.url, token=options.token)

    reply = ms.get_users_course_list(options.uid)
    courses = [Course(c) for c in reply.json()]
    courses.sort(key=lambda course: course.name)

    if options.courseids is None or options.force:
        choices = interaction.input_choices_from_list(courses, '\n  choose courses, seperate with space: ')
        if len(choices) == 0:
            print('nothing chosen.')
            raise SystemExit(1)
        chosen_courses = [courses[c] for c in choices]
        for c in chosen_courses:
            print('using: ' + str(c))
        options.courseids = [c.id for c in chosen_courses]
        saved_data = [c for c in reply.json() if c['id'] in options.courseids]

        wt.write_local_course_meta(saved_data)

    wt.write_local_config('courseids = ' + str(options.courseids))
    sync()


def _write_assignments(reply, worktree):
    changes = {
        'new': 0,
        'updated': 0,
        'unchanged': 0
    }
    assignment_ids = []
    data = json.loads(strip_mlang(reply.text))
    for course in data[Jn.courses]:
        for assignment in course[Jn.assignments]:
            assignment_ids.append(assignment[Jn.id])
            as_status = worktree.update_local_assignment_meta(assignment)
            changes[as_status] += 1
    print('finished. new: {:d}, updated: {:d}, unchanged: {:d}'.format(
        changes['new'], changes['updated'], changes['unchanged']))
    return assignment_ids


def _write_submissions(reply, worktree):
    new = 0
    updated = 0
    data = json.loads(strip_mlang(reply.text))
    for assignment in data[Jn.assignments]:
        if len(assignment[Jn.submissions]) > 0:
            if worktree.write_local_submission_meta(assignment):
                updated += 1
            else:
                new += 1
    print('finished: wrote {:d} new, {:d} updates submission files'.format(new, updated))


def _sync_file_meta(reply):
    # TODO, this
    pass


def _write_grades(reply, worktree):
    data = json.loads(strip_mlang(reply.text))
    for assignment in data[Jn.assignments]:
        worktree.write_local_grade_meta(assignment)
    print('finished. total: {:d}'.format(len(data[Jn.assignments])))


def _write_users(session, course_ids, worktree):
    print('syncing users…', end=' ', flush=True)

    users = []
    for cid in course_ids:
        try:
            reply = session.get_enrolled_users(course_id=cid)
            data = json.loads(strip_mlang(reply.text))
            users += data
            print('{:5d}:got {:4d}'.format(cid, len(data)), end=' ', flush=True)
        except AccessDenied as denied:
            message = '{:d} denied access to users: {}'.format(cid, denied)
            print(message, end=' ', flush=True)

    worktree.write_local_user_meta(users)
    print('finished.')


def _make_config_parser_sync(subparsers, url_token_parser):
    sync_parser = subparsers.add_parser(
        'sync',
        help='download metadata from server',
        parents=[url_token_parser]
    )
    sync_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')


def sync():
    wt = WorkTree()

    options = _get_options(wt)
    course_ids = _unpack(options.courseids)
    sync_meta_data = wt.read_sync_meta()
    last_sync = sync_meta_data['last_sync']
    moodle = MoodleSession(moodle_url=options.url, token=options.token)

    print('syncing assignments… ', end='', flush=True)
    assignment_ids = _write_assignments(moodle.get_assignments(course_ids), wt)

    print('syncing submissions… ', end='', flush=True)
    _write_submissions(moodle.get_submissions_for_assignments(assignment_ids, since=last_sync), wt)
    # _write_submissions(moodle.get_submissions_for_assignments(assignment_ids))

    print('syncing grades… ', end='', flush=True)
    # _write_grades(moodle.get_grades(assignment_ids, since=last_sync))
    _write_grades(moodle.get_grades(assignment_ids), wt)

    _write_users(moodle, course_ids, wt)

    wt.update_sync_meta()


def _unpack(elements):
    if elements is None:
        return None
    return [elem[0] for elem in elements if type(elem) is list]


def _make_config_parser_status(subparsers, url_token_parser):
    status_parser = subparsers.add_parser('status', help='display various information about work tree')
    status_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
    status_parser.add_argument('-a', '--assignmentids', nargs='+', help='show detailed status for assignment id',
                               type=int)
    status_parser.add_argument('-s', '--submissionids', nargs='+', help='show detailed status for submission id',
                               type=int)
    status_parser.add_argument('--full', help='display all assignments', action='store_true')


def status():
    wt = WorkTree()
    options = _get_options(wt)
    options.courseids = _unpack(options.courseids)

    course_data = wt.data
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


def _make_config_parser_pull(subparsers, url_token_parser):
    pull_parser = subparsers.add_parser(
        'pull',
        help='retrieve files for grading',
        parents=[url_token_parser]
    )
    pull_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
    pull_parser.add_argument('-a', '--assignmentids', nargs='+', type=int, required=True)
    pull_parser.add_argument('--all', help='pull all due submissions, even old ones', action='store_true')


def pull():
    wt = WorkTree()
    options = _get_options(wt)
    course_ids = _unpack(options.courseids)
    assignment_ids = options.assignmentids

    course_data = wt.data
    courses = [Course(c) for c in course_data]
    assignments = []
    for c in courses:
        assignments += c.get_assignments(assignment_ids)
    for a in assignments:
        a.download_files_and_write_html(token=options.token)


def _make_config_parser_grade(subparsers, url_token_parser):
    grade_parser = subparsers.add_parser(
        'grade',
        help='upload grades from files',
        parents=[url_token_parser]
    )
    grade_parser.add_argument('files', nargs='+', help='files containing grades', type=configargparse.FileType('r'))


def grade():
    wt = WorkTree()
    options = _get_options(wt)

    course_data = wt.data
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

    ms = MoodleSession(moodle_url=options.url, token=options.token)
    for graded_assignment in upload_data:
        as_id = graded_assignment['assignment_id']
        team = graded_assignment['team_submission']
        for gdata in graded_assignment['grade_data']:
            ms.save_grade(assignment_id=as_id,
                          user_id=gdata['user_id'],
                          grade=gdata['grade'],
                          feedback_text=gdata['feedback'],
                          team_submission=team)


def _make_config_parser_upload(subparsers, url_token_parser):
    upload_parser = subparsers.add_parser(
        'upload',
        help='upload files to draft area',
        parents=[url_token_parser]
    )
    upload_parser.add_argument('files', nargs='+', help='files to upload', type=configargparse.FileType('rb'))


def upload():
    wt = WorkTree()
    options = _get_options(wt)
    files = options.files
    ms = MoodleSession(options.url, options.token)
    reply = ms.upload_files(files)
    j = json.loads(reply.text)
    print(json.dumps(j, indent=2, ensure_ascii=False))


def _make_config_parser_config(subparsers, url_token_parser):
    subparsers.add_parser(
        'config',
        help='shows config values, nothing else'
    )


def config():
    wt = WorkTree()
    parser = make_config_parser(wt)
    parser.parse_known_args()
    parser.print_values()
