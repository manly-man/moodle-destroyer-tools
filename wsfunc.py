import json
import re
import requests

# TODO maybe use command pattern for ws functions
# TODO handle ws exceptions in sensible manner, collate warnings


def get_assignments(options, course_ids):
    """returns assignments for for all options.courseids"""

    function = 'mod_assign_get_assignments'
    args = {'courseids[]': course_ids}

    reply = _rest(options, function, wsargs=args)

    assignments = []
    for course in reply['courses']:
        assignments += course['assignments']

    return assignments


def get_course_list(options, user_id):
    function = 'core_enrol_get_users_courses'
    args = {'userid': user_id}
    reply = _rest(options, function, wsargs=args)
    return reply


def get_grades(options, assignment_ids, since=0):
    function = 'mod_assign_get_grades'
    args = {'assignmentids[]': assignment_ids}
    optargs = {'since': since}  # only return records, where timemodified >= since
    wsargs = {**args, **optargs}
    reply = _rest(options, function, wsargs=wsargs)
    grades = [a for a in reply['assignments']]
    return grades


def get_site_info(options):
    return _rest(options, 'core_webservice_get_site_info')


def get_submissions(options, assignment_ids):
    function = 'mod_assign_get_submissions'
    args = {'assignmentids[]': assignment_ids}

    reply = _rest(options, function, wsargs=args)
    submissions = [a for a in reply['assignments']]

    return submissions


def get_users(options, course_id):
    """returns assignments for for all options.courseids"""
    function = 'core_enrol_get_enrolled_users'
    args = {'courseid': course_id}
    reply = _rest(options, function, wsargs=args)

    return {'courseid': course_id, 'users': reply}


def get_token(options, password):
    args = {
        'username': options.user,
        'password': password,
        'service': options.service
    }
    reply = _rest_direct(options.url, '/login/token.php', wsargs=args)
    try:
        return reply['token']
    except KeyError:
        print(json.dumps(reply, indent=2, ensure_ascii=False))


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


def _rest_direct(url, path, wsargs={}):
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


def _rest(options, function, wsargs={}):
    wspath = '/webservice/rest/server.php'
    post_data = {
        'wstoken': options.token,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    }
    post_data.update(wsargs)
    return _rest_direct(options.url, wspath, post_data)


