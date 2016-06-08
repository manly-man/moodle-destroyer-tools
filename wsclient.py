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


def get_file_meta(options, context_id, item_id, component='assignsubmission_file', file_area='submission_files', filepath='', filename=''):
    function = 'core_files_get_files'
    args = {
        'contextid': context_id,
        'component': component,
        'filearea': file_area,
        'itemid': item_id,
        'filepath': filepath,
        'filename': filename
    }

    return _rest(options, function=function, wsargs=args)


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


def set_grade(options, assignment_id, user_id, grade, feedback='', team_submission=False, feedback_format='plain'):
    function = 'mod_assign_save_grade'

    remark_format = {
        'moodle': 0,
        'html': 1,
        'plain': 2,
        # don't know why remark format 3 is not defined. Documentation says nothing about it.
        'markdown': 4
    }
    data = {
        'assignmentid': assignment_id,  # The assignment id to operate on
        'userid': user_id,  # The student id to operate on
        'grade': grade,  # The new grade for this user. Ignored if advanced grading used
        'attemptnumber': -1,  # The attempt number (-1 means latest attempt)
        'addattempt': 0,  # Allow another attempt if the attempt reopen method is manual
        'workflowstate': '',  # The next marking workflow state
        'applytoall': 0,  # If true, this grade will be applied to all members of the group (for group assignments).
        'plugindata[assignfeedbackcomments_editor][text]': feedback,
        'plugindata[assignfeedbackcomments_editor][format]': remark_format[feedback_format],
        'plugindata[files_filemanager]': 0  # The id of a draft area containing files for this feedback. 0 for none
    }

    if team_submission:
        data['applytoall'] = 1

    print('submitting: aid:{:5d} uid:{:5d} grade:{:5.1f} group:{}'.format(assignment_id, user_id, grade, str(team_submission)))
    result = _rest(options, function=function, wsargs=data)


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
        if data is not None and 'exception' in data:
            print(str(json.dumps(data, indent=1)))
        elif data is not None and 'warnings' in data:
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


class MoodleWebServiceClient:
    def __init__(self, moodle_hostname, token, rest_format='json', web_service_path='/webservice/rest/server.php'):
        self.moodle_hostname = moodle_hostname
        self.token = token
        self.rest_format = rest_format
        self.web_service_path = web_service_path

    def _rest(self, function, wsargs={}):
        pass

    def _rest_direct(self, ):
        pass
