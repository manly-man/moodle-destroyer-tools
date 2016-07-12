#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import json
import configargparse

from moodle.exceptions import AccessDenied, InvalidResponse
from moodle.communication import MoodleSession
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.models import Course
from moodle.parsers import strip_mlang

from util.worktree import WorkTree
from util import interaction
import shutil
import logging

log = logging.getLogger('wstools')

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


def _make_config_parser_auth(subparsers, url_token_parser):
    auth_parser = subparsers.add_parser(
        'auth',
        help='retrieve access token from server',
        parents=[url_token_parser]
    )
    auth_parser.add_argument('-u', '--username', help='username', required=False)
    auth_parser.add_argument('-s', '--service', help='the webservice, has to be set explicitly',
                             default='moodle_mobile_app')
    auth_parser.add_argument('-a', '--ask', help='will ask for all credentials, again', action='store_true')
    auth_parser.set_defaults(func=auth)


def auth(args):
    wt = WorkTree(skip_init=True)
    _url = 'url'
    _user = 'username'
    _service = 'service'

    settings = {}

    if args.ask:
        settings[_url] = interaction.input_moodle_url(args.url)
        settings[_user] = interaction.input_user_name(args.username)
        del args.ask
    else:
        if args.url is None or args.url == '':
            settings[_url] = interaction.input_moodle_url()
        else:
            settings[_url] = args.url

        if args.username is None or args.username == '':
            settings[_user] = interaction.input_user_name()
        else:
            settings[_user] = args.username

    settings[_service] = args.service

    password = interaction.input_password()

    ms = MoodleSession(moodle_url=settings[_url])
    reply = ms.get_token(user_name=settings[_user], password=password, service=settings[_service])
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
    init_parser.set_defaults(func=init)


def init(args):
    """initializes working tree: creates local .mdt/config, with chosen courses"""

    try:
        wt = WorkTree(init=True, force=args.force)
    except FileExistsError:
        print('already initialized')
        raise SystemExit(1)

    ms = MoodleSession(moodle_url=args.url, token=args.token)

    reply = ms.get_users_course_list(args.uid)
    courses = [Course(c) for c in reply.json()]
    courses.sort(key=lambda course: course.name)

    if args.courseids is None or args.force:
        choices = interaction.input_choices_from_list(courses, '\n  choose courses, seperate with space: ')
        if len(choices) == 0:
            print('nothing chosen.')
            raise SystemExit(1)
        chosen_courses = [courses[c] for c in choices]
        for c in chosen_courses:
            print('using: ' + str(c))
        args.courseids = [c.id for c in chosen_courses]
        saved_data = [c for c in reply.json() if c['id'] in args.courseids]

        wt.write_local_course_meta(saved_data)

    wt.write_local_config('courseids = ' + str(args.courseids))
    args.courseids = [[i] for i in args.courseids]  # pack hotfix, do not liek.
    sync(args)


def _make_config_parser_sync(subparsers, url_token_parser):
    sync_parser = subparsers.add_parser(
        'sync',
        help='download metadata from server',
        parents=[url_token_parser]
    )
    sync_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')
    sync_parser.add_argument('-a', '--assignments', help='sync assignments', action='store_true')
    sync_parser.add_argument('-s', '--submissions', help='sync submissions', action='store_true')
    sync_parser.add_argument('-g', '--grades', help='sync grades', action='store_true')
    sync_parser.add_argument('-u', '--users', help='sync users', action='store_true', default=False)

    sync_parser.set_defaults(func=sync)


def sync(args):
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

    def _write_users(moodle, course_ids, worktree):
        print('syncing users…', end=' ', flush=True)

        users = {}
        for cid in course_ids:
            try:
                reply = moodle.get_enrolled_users(course_id=cid)
                data = json.loads(strip_mlang(reply.text))
                users[int(cid)] = data
                print('{:5d}:got {:4d}'.format(cid, len(data)), end=' ', flush=True)
            except AccessDenied as denied:
                message = '{:d} denied access to users: {}'.format(cid, denied)
                print(message, end=' ', flush=True)
            except InvalidResponse as e:
                message = 'Moodle encountered an error: msg:{} \n debug:{}'.format(e.message,e.debug_message)
                print(message)

        worktree.write_local_user_meta(users)
        print('finished.')

    wt = WorkTree()

    course_ids = _unpack(args.courseids)
    sync_meta_data = wt.read_sync_meta()
    last_sync = sync_meta_data['last_sync']
    moodle = MoodleSession(moodle_url=args.url, token=args.token)

    sync_all = True
    if args.users or args.submissions or args.assignments or args.grades:
        sync_all = False

    if args.assignments or sync_all:
        print('syncing assignments… ', end='', flush=True)
        assignment_ids = _write_assignments(moodle.get_assignments(course_ids), wt)

    if args.submissions or sync_all:
        print('syncing submissions… ', end='', flush=True)
        # _write_submissions(moodle.get_submissions_for_assignments(assignment_ids, since=last_sync), wt)
        _write_submissions(moodle.get_submissions_for_assignments(assignment_ids), wt)

    if args.grades or sync_all:
        print('syncing grades… ', end='', flush=True)
        # _write_grades(moodle.get_grades(assignment_ids, since=last_sync))
        _write_grades(moodle.get_grades(assignment_ids), wt)

    if args.users or sync_all:
        _write_users(moodle, course_ids, wt)

    if sync_all:
        wt.update_sync_meta()


def _make_config_parser_status(subparsers, url_token_parser):
    status_parser = subparsers.add_parser('status', help='display various information about work tree')
    status_parser.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
    status_parser.add_argument('-a', '--assignmentids', nargs='+', help='show detailed status for assignment id',
                               type=int)
    status_parser.add_argument('-s', '--submissionids', nargs='+', help='show detailed status for submission id',
                               type=int)
    status_parser.add_argument('--full', help='display all assignments', action='store_true')
    status_parser.set_defaults(func=status)


def status(args):
    wt = WorkTree()
    args.courseids = _unpack(args.courseids)
    term_columns = shutil.get_terminal_size().columns

    course_data = wt.data
    courses = [Course(c) for c in course_data]
    if args.assignmentids is not None and args.submissionids is None:
        for c in sorted(courses, key=lambda c: c.name):
            print(c)
            assignments = c.get_assignments(args.assignmentids)
            a_status = [a.detailed_status_string(indent=1) for a in assignments]
            for s in sorted(a_status):
                print(s)
    elif args.submissionids is not None:
        # TODO this.
        for c in sorted(courses, key=lambda c: c.name):
            print(c)
            assignments = c.get_assignments(args.assignmentids)
            a_status = [a.detailed_status_string() for a in assignments]
            for s in sorted(a_status):
                print(s)
    elif args.full:
        for i in sorted(courses, key=lambda c: c.name):
            i.print_status()
    else:
        for course in sorted(courses, key=lambda c: c.name):
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
    pull_parser.set_defaults(func=pull)


def pull(args):
    ms = MoodleSession(moodle_url=args.url, token=args.token)

    wt = WorkTree()
    course_ids = _unpack(args.courseids)
    assignment_ids = args.assignmentids

    course_data = wt.data
    courses = [Course(c) for c in course_data]
    assignments = []
    for c in courses:
        assignments += c.get_assignments(assignment_ids)

    for a in assignments:
        wt.start_pull(a)
        counter = 0
        complete = len(a.file_urls)
        interaction.print_progress(counter, complete)
        for file in a.file_urls:
            log.debug(file[Jn.file_url])
            response = ms.download_file(file[Jn.file_url])
            wt.write_pulled_file(response.content, file)
            counter += 1
            interaction.print_progress(counter, complete, suffix=file[Jn.file_path])
        html = a.merged_html
        if html is not None:
            wt.write_pulled_html(html)
        wt.write_grading_file(a)
        wt.finish_pull()


def _make_config_parser_grade(subparsers, url_token_parser):
    grade_parser = subparsers.add_parser(
        'grade',
        help='upload grades from files',
        parents=[url_token_parser]
    )
    grade_parser.add_argument('files', nargs='+', help='files containing grades', type=configargparse.FileType('r'))
    grade_parser.set_defaults(func=grade)


def grade(args):
    wt = WorkTree()

    course_data = wt.data
    courses = [Course(c) for c in course_data]
    grading_data = {}
    for file in args.files:
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

    ms = MoodleSession(moodle_url=args.url, token=args.token)
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
    upload_parser.set_defaults(func=upload)


def upload(args):
    # wt = WorkTree()
    files = args.files
    ms = MoodleSession(args.url, args.token)
    reply = ms.upload_files(files)
    j = json.loads(reply.text)
    print(json.dumps(j, indent=2, ensure_ascii=False))


def _make_config_parser_config(subparsers, url_token_parser):
    config_parser = subparsers.add_parser(
        'config',
        help='shows config values, nothing else'
    )
    config_parser.set_defaults(func=config)


def config(args):
    wt = WorkTree()
    parser = make_config_parser(wt)
    parser.parse_known_args()
    parser.print_values()


def _unpack(elements):
    if elements is None:
        return None
    return [elem[0] for elem in elements if type(elem) is list]


class MoodleDestroyerCommand:
    def __init__(self, name, help_text):
        self.name = name
        self.help = help_text

    def __str__(self):
        return self.name + ' ' + self.help

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()
