class LookupDict(dict):
    def __getitem__(self, key):
        return self.__dict__.get(key, None)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

_text_format = {
    0: 'moodle',
    1: 'html',
    2: 'plain',
    # don't know why format 3 is not defined. Documentation says nothing about it.
    4: 'markdown'
}


# maybe use gettext for different versions?
class JsonFieldNames:
    add_attempt = 'addattempt'
    apply_to_all = 'applytoall'
    assign_feedback_text = 'plugindata[assignfeedbackcomments_editor][text]'
    assign_feedback_format = 'plugindata[assignfeedbackcomments_editor][format]'
    assign_feedback_file = 'plugindata[files_filemanager]'
    assignment_id = 'assignmentid'
    assignment_ids = 'assignmentids[]'
    assignments = 'assignments'
    attempt_number = 'attemptnumber'
    before = 'before'
    capabilities = 'capabilities[]'
    course = 'course'
    course_id = 'courseid'
    course_ids = 'courseids[]'
    courses = 'courses'
    context_id = 'contextid'
    context_level = 'contextlevel'
    component = 'component'
    debug_info = 'debuginfo'
    error_code = 'errorcode'
    exception = 'exception'
    file_area = 'filearea'
    file_name = 'filename'
    file_path = 'filepath'
    grade = 'grade'
    grades = 'grades'
    id = 'id'
    item_id = 'item_id'
    include_not_enrolled_courses = 'includenotenrolledcourses'
    instance_id = 'instanceid'
    invalid_parameter_exception = 'invalid_parameter_exception'
    invalid_response_exception = 'invalid_response_exception'
    invalid_response_exception_errorcode = 'invalidresponse'
    invalid_token = 'invalidtoken'
    message = 'message'
    modified = 'modified'
    moodle_exception = 'moodle_exception'
    moodle_ws_rest_format = 'moodlewsrestformat'
    name = 'name'
    no_permissions = 'nopermissions'
    options = 'options[{:d}][{}]'
    required_capability_exception = 'required_capability_exception'
    password = 'password'
    service = 'service'
    since = 'since'
    status = 'status'
    submissions = 'submissions'
    time_modified = 'timemodified'
    token = 'token'
    user_id = 'userid'
    user_name = 'username'
    users = 'users'
    value = 'value'
    workflow_state = 'workflowstate'
    ws_function = 'wsfunction'
    ws_token = 'wstoken'


class UrlPaths:
    web_service = '/webservice/rest/server.php'
    token = '/login/token.php'
    upload = '/webservice/upload.php'
    download = '/webservice/pluginfile.php'

text_format = LookupDict()

for number, fmt in _text_format.items():
    setattr(text_format, fmt, number)
