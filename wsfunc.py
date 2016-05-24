#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import configargparse
import requests
import json
import re
import math
import os
from datetime import datetime

# from MoodleDestroyer import MoodleDestroyer
# todo parse {mlang} tags
# todo implement error handling in rest(direct)

__all__ = ['auth', 'init', 'pull', 'sync']
LOCAL_CONFIG_FOLDER = '.mdt/'
LOCAL_CONFIG = LOCAL_CONFIG_FOLDER + 'config'
ASSIGNMENT_FOLDER = LOCAL_CONFIG_FOLDER + 'assignments/'


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


def _get_assignment_list(options):
    """returns assignments for for all options.courseids"""

    function = 'mod_assign_get_assignments'
    args = {'courseids[]': options.courseids}

    reply = rest(options, function, wsargs=args)

    for course in reply['courses']:
        alist = []
        for assignment in course['assignments']:
            alist.append([assignment['id'], assignment['name']])
        alist.sort()

    assignments = []
    for course in reply['courses']:
        assignments += course['assignments']

    if options.all:
        now = datetime.now()
        due_assignments = []
        for assignment in assignments:
            due_date = datetime.fromtimestamp(assignment['duedate'])
            diff = now - due_date
            if now > due_date and diff.days < 25 * 7:
                due_assignments.append(assignment)

    return assignments


def _get_course_list(options):
    function = 'core_enrol_get_users_courses'
    args = {'userid': options.uid}
    reply = rest(options, function, wsargs=args)

    course_list = []
    for course in reply:
        course_list.append([course['fullname'], course['shortname'], course['id']])

    course_list.sort()
    return course_list


def _get_submissions(options):
    function = 'mod_assign_get_submissions'
    args = {'assignmentids[]': [options.aids]}

    reply = rest(options, function, wsargs=args)
    submissions = []
    for a in reply['assignments']:
        submissions.append(Assignment(a))

    return submissions


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

    course_list = _get_course_list(options)

    if options.courseids is None or options.force:
        choices = _get_choices_from_list(course_list, input_text)
        for c in choices:
            print('using: ' + course_list[c][0])
        options.courseids = [course_list[c][2] for c in choices]

    os.makedirs(LOCAL_CONFIG_FOLDER, exist_ok=True)
    with open(LOCAL_CONFIG, 'w') as config_file:
        config_file.write('courseids = ' + str(options.courseids))


def sync():
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--url')
    config.add_argument('-c', '--courseids', nargs='+', help='moodle course id', type=int, action='append')
    [options, unparsed] = config.parse_known_args()

    new_assignments = 0
    updated_assignments = 0

    def write_config(filename, data):
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

    os.makedirs(ASSIGNMENT_FOLDER, exist_ok=True)
    options.all = True
    alist = _get_assignment_list(options)
    for assignment in alist:
        as_config_file = ASSIGNMENT_FOLDER+str(assignment['id'])
        if os.path.isfile(as_config_file):
            with open(as_config_file, 'r') as local_file:
                local_as_config = json.load(as_config_file)
            if local_as_config['timemodified'] < assignment['timemodified']:
                write_config(as_config_file,assignment)
                updated_assignments += 1
        else:
            write_config(as_config_file, assignment)
            new_assignments += 1
    print('finished. new assignments: {}, updated_assignments: {}'.format(new_assignments, updated_assignments))

def pull():
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--url')
    config.add_argument('--courseids', nargs='+', type=int, action='append')
    config.add_argument('-a', '--all', help='pull all due submissions, even old ones', action='store_true')
    [options, unparsed] = config.parse_known_args()

    if len(config._default_config_files) <= 1:
        print('no work tree, try mdt init')
        return

    assignment_list = _get_assignment_list(options)

    for assignment in assignment_list:
        pass




def rest_direct(url, path, wsargs={}):
    try:
        reply = requests.post('https://' + url + path, wsargs)
    except ConnectionError:
        print('connection error')
    return json.loads(_parse_mlang(reply.text))


def rest(options, function, wsargs={}):
    wspath = '/webservice/rest/server.php'
    postData = {
        'wstoken': options.token,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    }
    postData.update(wsargs)
    return rest_direct(options.url, wspath, postData)


class Assignment:
    def __init__(self, data):
        self.aid = data['assignmentid']
        self.subs = [Submission(s) for s in data.pop('submissions')]
        self.data = data

    def __str__(self):
        string = str(self.aid) + '\n'
        for s in self.subs:
            string += str(s)
        return string


class Submission:
    def __init__(self, data):
        self.sid = data['id']
        self.uid = data['userid']
        if 'groupid' in data:
            self.gid = data['groupid']
        else:
            self.gid = 0
        self.plugs = [Plugin(p) for p in data.pop('plugins')]
        self.data = data

    def __str__(self):
        string = ''
        for p in self.plugs:
            string += str(p)

        if '' != string:
            string = ' ' + str(self.uid) + ':' + str(self.gid) + '\n' + string
        return string


class Plugin:
    def __init__(self, data):
        self.kind = data['type']
        self.name = data['name']
        if 'editorfields' in data:
            self.efields = [Editorfield(e) for e in data.pop('editorfields')]
        if 'fileareas' in data:
            self.fareas = [Filearea(f) for f in data.pop('fileareas')]
        self.data = data

    def __str__(self):
        if 'file' != self.kind:
            return ''
        string = ''
        for fa in self.fareas:
            string += str(fa)
        return string


class Filearea:
    def __init__(self, data):
        self.area = data['area']
        self.urls = []
        if 'files' in data:
            self.urls = [f['fileurl'] for f in data.pop('files')]
        self.data = data

    def __str__(self):
        string = ''
        if 0 == len(self.urls):
            return ''
        for u in self.urls:
            string += '  ' + u + '\n'
        return string


class Editorfield:
    def __init__(self, data):
        self.data = data
        self.name = data['name']
        self.descr = data['description']
        self.text = data['text']
        self.fmt = data['format']

