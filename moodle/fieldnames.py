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
    assignment_ids = 'assignmentids'
    attempt_number = 'attemptnumber'
    before = 'before'
    capabilities = 'capabilities'
    course_id = 'courseid'
    course_ids = 'courseids'
    context_id = 'contextid'
    context_level = 'contextlevel'
    component = 'component'
    file_area = 'filearea'
    file_name = 'filename'
    file_path = 'filepath'
    grade = 'grade'
    item_id = 'item_id'
    include_not_enrolled_courses = 'includenotenrolledcourses'
    instance_id = 'instanceid'
    modified = 'modified'
    moodle_ws_rest_format = 'moodlewsrestformat'
    name = 'name'
    options = 'options[{:d}][{}]'
    password = 'password'
    service = 'service'
    since = 'since'
    status = 'status'
    user_id = 'userid'
    user_name = 'username'
    value = 'value'
    workflow_state = 'workflowstate'
    ws_function = 'wsfunction'
    ws_token = 'wstoken'


text_format = LookupDict()

for number, fmt in _text_format.items():
    setattr(text_format, fmt, number)
