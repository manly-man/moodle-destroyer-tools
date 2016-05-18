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
# from MoodleDestroyer import MoodleDestroyer
# todo parse {mlang} tags
# todo implement error handling in rest(direct)

__all__ = ['init', 'auth']

def auth():
    import getpass
    import configparser
    import sys

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
    '''can return assignments for more than one course, is rarely used. if ever.'''
    cids = options.courseid
    wsfunction = 'mod_assign_get_assignments'
    wsargs = {'courseids[]': [cids]}

    reply = rest(options, wsfunction, wsargs=wsargs)
    # due_date = datetime.datetime.fromtimestamp(1463392800) # from json['duedate']
    # now = datetime.datetime.now()

    for course in reply['courses']:
        print(str(course['id']) + ' ' + course['fullname'])
        alist = []
        for assignment in course['assignments']:
            alist.append([assignment['id'], assignment['name']])
            if assignment['id'] == 3934:
                print(json.dumps(assignment, indent=2))
        alist.sort()
        for a in alist:
            print(' ' + str(a))


def _get_course_list(options):
    wsfunction = 'core_enrol_get_users_courses'
    wsargs = {'userid': options.uid}
    reply = rest(options, wsfunction, wsargs=wsargs)

    course_list = []
    # print(json.dumps(courses_json, indent=2))
    for course in reply:
        if 1 == course['visible']:
            course_list.append([course['fullname'], course['shortname'], course['id']])

    course_list.sort()
    return course_list


def init():
    import os
    # it is theoretically possible to have more than one course in one folder.
    # could be used for multiple IDs
    config = configargparse.getArgumentParser(name='mdt')
    config.add_argument('--uid')
    config.add_argument('--url')
    config.add_argument('--force', help='overwrite the config', action='store_true')
    config.add_argument('-c', '--courseid', help='moodle course id', type=int)

    input_text = 'choose course: '
    [options, unparsed] = config.parse_known_args()

    if os.path.isfile('.mdt/config') and not options.force:
        print('repo already initilized, use --force to overwrite config')
        return

    course_list = _get_course_list(options)

    if options.courseid is None or options.force:
        for n, c in enumerate(course_list, 0):
            print('{:2d} {}'.format(n, c))
        choice = int(input(input_text))
        course = course_list[choice]
        print('using: ' + course[0])
        options.courseid = course[2]

    if not os.path.exists('.mdt'):
        os.makedirs('.mdt')

    with open('.mdt/config', 'w') as config_file:
        config_file.write('courseid = ' + str(options.courseid))

    assignments = _get_assignment_list(options)


def rest_direct(url, path, wsargs={}):
    reply = requests.post('https://' + url + path, wsargs)
    return json.loads(reply.text)


def rest(options, function, wsargs={}):
    wspath = '/webservice/rest/server.php'
    postData = {
        'wstoken': options.token,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    }
    postData.update(wsargs)
    return rest_direct(options.url, wspath, postData)
