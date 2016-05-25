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

# TODO determine working directory root somewhere sensible, pass to wsfunc.

__all__ = ['auth', 'init', 'pull', 'status', 'sync']
WORKING_DIRECTORY = None
LOCAL_CONFIG_FOLDER = '.mdt/'
LOCAL_CONFIG = LOCAL_CONFIG_FOLDER + 'config'
LOCAL_CONFIG_USERS = LOCAL_CONFIG_FOLDER + 'users'
LOCAL_CONFIG_COURSES = LOCAL_CONFIG_FOLDER + 'courses'
ASSIGNMENT_FOLDER = LOCAL_CONFIG_FOLDER + 'assignments/'
SUBMISSION_FOLDER = LOCAL_CONFIG_FOLDER + 'submissions/'
GRADE_FOLDER = LOCAL_CONFIG_FOLDER + 'grades/'


def _get_working_directory():
    if WORKING_DIRECTORY is None:
        print('not in working directory, this command needs to be')
        return None
    return WORKING_DIRECTORY


def auth():
    import getpass
    import configparser

    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('-u', '--user', help='username', required=False)
    config.add_argument('-s', '--service', help='the webservice, has to be set explicitly', default='moodle_mobile_app')
    config.add_argument('-a', '--ask', help='will ask for all credentials, again', action='store_true')

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

    reply = rest_direct(options.url, '/login/token.php', {
            'username': options.user,
            'password': password,
            'service': options.service
        })

    del password

    try:
        options.token = reply['token']

        reply = rest(options, 'core_webservice_get_site_info')
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

    except KeyError:
        print(json.dumps(reply, indent=2, ensure_ascii=False))

    return options


def _get_assignments_from_server(options):
    """returns assignments for for all options.courseids"""

    function = 'mod_assign_get_assignments'
    args = {'courseids[]': options.courseids}

    reply = rest(options, function, wsargs=args)

    assignments = []
    for course in reply['courses']:
        assignments += course['assignments']

    # if not options.all:
    #     now = datetime.now()
    #     due_assignments = []
    #     for assignment in assignments:
    #         due_date = datetime.fromtimestamp(assignment['duedate'])
    #         diff = now - due_date
    #         if now > due_date and diff.days < 25 * 7:
    #             due_assignments.append(assignment)
    #     return due_assignments

    return assignments


def _get_course_list_from_server(options):
    function = 'core_enrol_get_users_courses'
    args = {'userid': options.uid}
    reply = rest(options, function, wsargs=args)
    return reply


def _get_submissions_from_server(options):
    function = 'mod_assign_get_submissions'
    args = {'assignmentids[]': options.assignmentids}

    reply = rest(options, function, wsargs=args)
    submissions = [a for a in reply['assignments']]
    # submissions = [
    # for a in reply['assignments']:
    #     submissions.append(Assignment(a))

    return submissions


def _get_grades_from_server(options):
    function = 'mod_assign_get_grades'
    args = {'assignmentids[]': options.assignmentids}
    optargs = {'since': 0}  # only return records, where timemodified >= since

    reply = rest(options, function, wsargs=args)
    grades = [a for a in reply['assignments']]
    return grades


def _get_users_from_server(options):
    """returns assignments for for all options.courseids"""

    function = 'core_enrol_get_enrolled_users'
    users = []
    for course_id in options.courseids:
        args = {'courseid': course_id}
        reply = rest(options, function, wsargs=args)
        users.append({'courseid': course_id, 'users': reply})

    return users


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


def _parse_mlang(string, preferred_lang='en'):
    # todo make preferred language configurable
    # creates mlang tuples like ('en', 'eng text')
    # tuple_regex = re.compile(r'(?:\{mlang (\w{2})\}(.+?)\{mlang\})+?', flags=re.S)
    # tuples = tuple_regex.findall(string)

    # creates set with possible languages like {'en', 'de'}
    lang_regex = re.compile(r'\{mlang\s*(\w{2})\}')
    lang_set = set(lang_regex.findall(string))

    if len(lang_set) > 1:
        lang_set.discard(preferred_lang)  # removes preferred lang from set, langs in set will be purged
        discard_mlang = '|'.join(lang_set)
        pattern = re.compile(r'((?=\{mlang ('+discard_mlang+r')\})(.*?)\{mlang\})+?', flags=re.S)
        string = pattern.sub('', string)

    strip_mlang = re.compile(r'(\s*\{mlang.*?\}\s*)+?')
    return strip_mlang.sub('', string)


def init():
    """initializes working tree: creates local .mdt/config, with chosen courses"""
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--uid')
    config.add_argument('--url')
    config.add_argument('--force', help='overwrite the config', action='store_true')
    config.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')
    [options, unparsed] = config.parse_known_args()

    input_text = '\n  choose courses, seperate with space: '

    if len(config._default_config_files) > 1 and not options.force:
        print('repo already initilized, use --force to overwrite config')
        return

    course_data = _get_course_list_from_server(options)
    course_data_temp = _get_course_list_from_server(options)
    courses = [Course(c) for c in course_data_temp]
    courses.sort(key=lambda course: course.name)

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
    os.makedirs(LOCAL_CONFIG_FOLDER, exist_ok=True)
    with open(LOCAL_CONFIG, 'w') as config_file:
        config_file.write('courseids = ' + str(options.courseids))


def _sync_assignments(options):
    print('syncing assignments… ', end='', flush=True)
    new_assignments = 0
    updated_assignments = 0
    config_dir = _get_working_directory() + ASSIGNMENT_FOLDER

    def write_config(filename, data):
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

    os.makedirs(config_dir, exist_ok=True)
    assignment_list = _get_assignments_from_server(options)
    for assignment in assignment_list:
        as_config_file = config_dir+str(assignment['id'])
        if os.path.isfile(as_config_file):
            with open(as_config_file, 'r') as local_file:
                local_as_config = json.load(local_file)
            if local_as_config['timemodified'] < assignment['timemodified']:
                write_config(as_config_file, assignment)
                updated_assignments += 1
        else:
            write_config(as_config_file, assignment)
            new_assignments += 1
    print('finished. new: {}, updated: {}, total: {}'.format(
        new_assignments, updated_assignments, str(len(assignment_list))))
    return assignment_list


def _sync_submissions(options):
    print('syncing submissions… ', end='', flush=True)
    config_dir = _get_working_directory() + SUBMISSION_FOLDER

    def write_config(filename, data):
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

    os.makedirs(config_dir, exist_ok=True)
    submissions = _get_submissions_from_server(options)
    for assignment in submissions:
        s_config_file = config_dir+str(assignment['assignmentid'])
        write_config(s_config_file, assignment)
    print('finished: wrote {} submission files'.format(str(len(submissions))))
    return submissions


def _sync_grades(options):
    print('syncing grades… ', end='', flush=True)
    config_dir = _get_working_directory() + GRADE_FOLDER

    def write_config(filename, data):
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

    os.makedirs(config_dir, exist_ok=True)
    assignments = _get_grades_from_server(options)
    for assignment in assignments:
        g_config_file = config_dir+str(assignment['assignmentid'])
        write_config(g_config_file, assignment)
    print('finished. total: {}'.format(str(len(assignments))))
    return assignments


def _sync_users(options):
    print('syncing users… ', end='', flush=True)
    u_config_file = _get_working_directory() + LOCAL_CONFIG_USERS

    def write_config(filename, data):
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

    users = _get_users_from_server(options)
    write_config(u_config_file, users)
    print('finished.')
    return users


def sync():
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--url')
    config.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    if _get_working_directory() is None:
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
    return [elem[0] for elem in elements if type(elem) is list]


def _pretty_print_work_dir_status(courses):
    for course in courses:
        course_out = ''
        course_out += 'courseid:{:5d}'.format(course['id'])
        course_out += ' assignments:{:3d}'.format(len(course['assignments']))
        course_out += ' users:{:4d}'.format(len(course['users']))
        print(course_out)
        outlist = []
        for assignment in course['assignments']:
            out = ''
            out += ' assignmentid:{:5d}'.format(assignment['id'])
            out += ' {:40}'.format(str(assignment['name'])[0:39])
            if 'submissions' in assignment:
                out += ' submissions:{:4d}'.format(len(assignment['submissions']))

            if 'grades' in assignment:
                out += ' grades:{:4d}'.format(len(assignment['grades']))
            else:
                out += ' grades:{:4d}'.format(0)

            outlist.append(out)

        for out in sorted(outlist):
            print(out)


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


def _pretty_print_assignment_status(courses, assignmentids):
    def pretty_submission(submission):
        plugin_out = ''
        for plugin in submission['plugins']:
            plugin_out += pretty_plugin(plugin)  #plugin is list of dicts
        if plugin_out != '':
            return '  submission id:{:5d}'.format(submission['id']) + plugin_out
        else:
            return ''

    def pretty_plugin(plugin):
        out = ''
        if 'editorfields' in plugin:
            out += pretty_editorfield(plugin['editorfields'])

        if 'fileareas' in plugin:
            out += pretty_file(plugin['fileareas'])

        return out

    def pretty_editorfield(editorfields):
        out = ''
        for ef in editorfields:
            if ef['text'].strip() != '':
                out += ef['name']
            else:
                out += ''  # 'no editorfield'
        return out

    def pretty_file(fileareas):
        out = ''
        for fa in fileareas:
            if 'files' in fa:
                out += '{}: filecount: {:2d}'.format(fa['area'],len(fa['files']))
            else:
                out += ''  # '{}: no files'.format(fa['area'])
        return out

    for course in courses:
        assignments = [a for a in course['assignments'] if a['id'] in assignmentids]
        if len(assignments) > 0:
            print('course {:5d}'.format(course['id']))
            for a in assignments:
                subs = [Submission(s) for s in a['submissions']]
                content = [s for s in subs if s.has_content()]
                if a['teamsubmission'] == 1:
                    print(' assignment {}, has {:3d} group submissions'.format(a['name'], len(content)))
                    submitter_count = 0
                    for s in content:
                        users = course['users']
                        submitters = [u['id'] for u in users if len(u['groups']) > 0 and u['groups'][0]['id'] == s.gid]
                        submitter_count += len(submitters)
                        print(s, end='')
                        print(' submitters:{}'.format(str(submitters)))
                    if 'grades' in a:
                        print('  have subcount:{:3d}, gradecount:{:3d}'.format(submitter_count, len(a['grades'])))
                        if submitter_count == len(a['grades']):
                            print('  all graded, yay')
                else:
                    print(' assignment {}, has {:3d} single submissions'.format(a['name'], len(content)))

                # for s in a['submissions']:
                #     text = pretty_submission(s)
                #     if text != '':
                #         print(text)


def status():
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('-c', '--courseids', nargs='+', help='moodle course ids', type=int, action='append')
    config.add_argument('-a', '--assignmentids', nargs='+', help='show detailed status for assignment id', type=int)
    [options, unparsed] = config.parse_known_args()
    options.courseids = _unpack(options.courseids)

    now = datetime.now()
    wd = _get_working_directory()
    if wd is None:
        return

    courses = _merge_local_data(wd, options.courseids)
    if options.assignmentids is not None:
        _pretty_print_assignment_status(courses, options.assignmentids)
    else:
        pass  # _pretty_print_work_dir_status(courses)
    print(type(courses))
    print(type(courses[0]))
    cc = [Course(c) for c in courses]
    print(type(cc))
    print(type(cc[0]))
    for i in cc:
        print(i.print_status())


def pull():
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--url')
    config.add_argument('--assignmentids', nargs='+', type=int, action='append')
    config.add_argument('-a', '--all', help='pull all due submissions, even old ones', action='store_true')
    [options, unparsed] = config.parse_known_args()

    if len(config._default_config_files) <= 1:
        print('no work tree, try mdt init')
        return

    assignment_list = _get_assignments_from_server(options)

    for assignment in assignment_list:
        pass


def rest_direct(url, path, wsargs={}):
    try:
        reply = requests.post('https://' + url + path, wsargs)
        data = json.loads(reply.text)
        if 'exception' in data:
            print(str(json.dumps(data, indent=1)))
        elif 'warnings' in data:
            for warning in data['warnings']:
                print('{} (id:{}) returned warning code [{}]:{}'.format(
                    warning['item'], str(warning['itemid']), warning['warningcode'], warning['message']
                ))
        return json.loads(_parse_mlang(reply.text))
    except ConnectionError:
        print('connection error')


def rest(options, function, wsargs={}):
    wspath = '/webservice/rest/server.php'
    postData = {
        'wstoken': options.token,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    }
    postData.update(wsargs)
    return rest_direct(options.url, wspath, postData)


class Course:
    def __init__(self, data):
        self.id = data.pop('id')
        self.name = data.pop('fullname')
        self.shortname = data.pop('shortname')
        self.users = []
        if 'users' in data:
            self.users = data.pop('users')
        self.assignments = []
        if 'assignments' in data:
            self.assignments = [Assignment(a) for a in data.pop('assignments')]

        self.unparsed = data
        #todo: map(user:groups), class User

    def __str__(self):
        return '{:40} id:{:5d} short: {}'.format(self.name[0:39], self.id, self.shortname)

    def print_status(self):
        print(self)
        for a in self.assignments:
            a.print_short_status(indent=1)


class Assignment:
    def __init__(self, data):
        self.id = data.pop('id')
        self.submissions = [Submission(s) for s in data.pop('submissions')]
        self.teamsubmission = 1 == data.pop('teamsubmission')
        self.duedate_timestamp = data.pop('duedate')
        self.name = data.pop('name')
        self.grades = []
        if 'grades' in data:
            self.grades = data.pop('grades')
        self.unparsed = data

    def __str__(self):
        return 'assignment[{:d}]: {}'.format(self.id, self.name[0:29])

    def submission_count(self):
        # TODO is wrong for team submission, needs user:group mappings to work.
        return [s.has_content() for s in self.submissions].count(True)

    def is_due(self):
        return self.duedate_timestamp < datetime.now().timestamp()

    def grade_count(self):
        return len(self.grades)

    def needs_grading(self):
        return self.is_due() and self.grade_count() < self.submission_count()

    def print_short_status(self, indent=0):
        fmt_string = ' ' * indent + '{:40} submissions:{:3d} due:{:1} graded:{}'
        print(fmt_string.format(self.id, self.name[0:39], self.submission_count(), self.is_due(), not self.needs_grading()))


class Submission:
    def __init__(self, data):
        self.id = data.pop('id')
        self.uid = data.pop('userid')
        self.gid = data.pop('groupid')
        self.plugs = [Plugin(p) for p in data.pop('plugins')]
        self.unparsed = data

    def __str__(self):
        out = ''
        if self.has_content():
            for p in self.plugs:
                out += str(p)
            out = '  id:{:7d} {:5d}:{:5d}'.format(self.id, self.uid, self.gid) + ' ' + out
            return out
        else:
            return ''

    def has_content(self):
        return True in [p.has_content() for p in self.plugs]


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


class Filearea:
    def __init__(self, data):
        self.area = data.pop('area')
        self.files = []
        if 'files' in data:
            self.files = data.pop('files')
        self.data = data

    def __str__(self):
        if self.has_content():
            return str(len(self.files))
        else:
            return ''

    def has_content(self):
        return len(self.files) > 0


class Editorfield:
    def __init__(self, data):
        self.data = data
        self.name = data.pop('name')
        self.descr = data.pop('description')
        self.text = data.pop('text')
        self.fmt = data.pop('format')
        self.unparsed = data

    def __str__(self):
        if self.has_content():
            return self.name
        else:
            return ''

    def has_content(self):
        return self.text.strip() != ''

