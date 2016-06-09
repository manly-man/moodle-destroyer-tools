#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import json
import re

import configargparse

import wsclient
from moodle.communication import MoodleSession
from moodle.models import Course

from util import worktree
from util import interaction

# TODO remove all merging stuff, merge on sync, write only one file, update accordingly
# TODO after metadata is in one file: on sync: request submissions via last_changed.

__all__ = ['auth', 'grade', 'init', 'pull', 'status', 'sync']


def auth():
    [options, unparsed] = config.parse_known_args()
    settings = {}

    if options.ask:
        settings['url'] = interaction.input_moodle_url(options.url)
        settings['user'] = interaction.input_user_name(options.user)
        del options.ask
    else:
        if options.url is None or options.url == '':
            settings['url'] = interaction.input_moodle_url()
        else:
            settings['url'] = options.url

        if options.user is None or options.user == '':
            settings['user'] = interaction.input_user_name()
        else:
            settings['user'] = options.user

    settings['service'] = options.service

    password = interaction.input_password()

    ms = MoodleSession(moodle_url=settings['url'])
    reply = ms.get_token(user_name=settings['user'], password=password, service=settings['service'])
    del password

    try:
        j = reply.json()
        settings['token'] = j['token']
        ms.token = settings['token']
    except KeyError:
        print(reply.text)
        raise SystemExit(1)

    reply = ms.get_site_info().json()
    settings['uid'] = reply['userid']
    # functions_json = reply['functions']
    # functions = [func_dict['name'] for func_dict in functions_json]
    # print(functions)

    worktree.write_global_config(settings)


def init():
    """initializes working tree: creates local .mdt/config, with chosen courses"""
    [options, unparsed] = config.parse_known_args()

    ms = MoodleSession(moodle_url=options.url, token=options.token)

    input_text = '\n  choose courses, seperate with space: '

    if worktree.in_root() and not options.force:
        print('repo already initilized, use --force to overwrite config')
        raise SystemExit(1)

    reply = ms.get_users_course_list(options.uid)
    courses = [Course(c) for c in reply.json()]
    courses.sort(key=lambda course: course.name)
    worktree.create_folders()

    if options.courseids is None or options.force:
        choices = interaction.input_choices_from_list(courses, input_text)
        if len(choices) == 0:
            print('nothing chosen.')
            raise SystemExit(1)
        chosen_courses = [courses[c] for c in choices]
        for c in chosen_courses:
            print('using: ' + c)
        options.courseids = [c.id for c in chosen_courses]
        saved_data = [c for c in reply.json() if c['id'] in options.courseids]

        worktree.write_local_course_meta(json.dumps(saved_data))

    worktree.write_local_config('courseids = ' + str(options.courseids))


def _write_config(filename, data):
    with open(filename, 'w') as file:
        file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def _sync_assignments(options):
    print('syncing assignments… ', end='', flush=True)

    new_assignments = 0
    updated_assignments = 0
    assignment_list = wsclient.get_assignments(options, course_ids=options.courseids)
    for assignment in assignment_list:
        if worktree.update_local_assignment_meta(assignment):
            updated_assignments += 1
        else:
            new_assignments += 1
    print('finished. new: {:d}, updated: {:d}, total: {:d}'.format(
        new_assignments, updated_assignments, len(assignment_list)))
    return assignment_list


def _sync_submissions(options):
    print('syncing submissions… ', end='', flush=True)

    assignmants = wsclient.get_submissions(options, assignment_ids=options.assignmentids)
    for assignment in assignmants:
        worktree.write_local_submission_meta(assignment)
    print('finished: wrote {:d} submission files'.format(len(assignmants)))
    return assignmants


def _sync_file_meta(options):
    # TODO, this
    pass


def _sync_grades(options):
    print('syncing grades… ', end='', flush=True)

    assignments = wsclient.get_grades(options, assignment_ids=options.assignmentids)
    for assignment in assignments:
        worktree.write_local_grade_meta(assignment)
    print('finished. total: {:d}'.format(len(assignments)))
    return assignments


def _sync_users(options):
    print('syncing users…', end=' ', flush=True)

    users = []
    for cid in options.courseids:
        users.append(wsclient.get_users(options, course_id=cid))
        print('{:5d}'.format(cid), end=' ', flush=True)

    worktree.write_local_user_meta(users)
    print('finished.')
    return users


def sync():
    worktree.needs_work_tree()

    [options, unparsed] = config.parse_known_args()
    course_ids = _unpack(options.courseids)

    for course in course_ids:
        pass
    assignments = _sync_assignments(options)
    options.assignmentids = [a['id'] for a in assignments]
    submissions = _sync_submissions(options)
    grades = _sync_grades(options)
    users = _sync_users(options)


def _unpack(elements):
    if elements is None:
        return None
    return [elem[0] for elem in elements if type(elem) is list]


def status():
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    course_data = worktree.merge_local_json_data(options.courseids)
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

    course_data = worktree.merge_local_json_data(options.courseids)
    courses = [Course(c) for c in course_data]
    assignments = []
    for c in courses:
        assignments += c.get_assignments(options.assignmentids)
    for a in assignments:
        a.download_files_and_write_html(token=options.token)


def grade():
    [options, unparsed] = config.parse_known_args()

    course_data = worktree.merge_local_json_data()
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


config = configargparse.getArgumentParser(name='mdt', default_config_files=worktree.get_config_file_list())
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
