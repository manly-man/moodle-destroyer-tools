from moodle.fieldnames import JsonFieldNames as Jn


class MoodleError(Exception):
    def __init__(self, exception, errorcode, message, debuginfo=''):
        self.exception_name = exception
        self.message = message
        self.error_code = errorcode
        self.debug_message = debuginfo

    def __str__(self):
        msg = 'Please Report this Exception!\n' \
              '{} {} {} {}'.format(self.exception_name, self.error_code, self.message, self.debug_message)
        return msg


class InvalidToken(MoodleError):
    def __init__(self, message):
        self.exception_name = Jn.moodle_exception
        self.error_code = Jn.invalid_token
        self.message = message

    def __str__(self):
        return 'your token is invalid, please use auth: {}'.format(self.message)


class AccessDenied(MoodleError):
    def __init__(self, message):
        self.exception_name = Jn.required_capability_exception
        self.error_code = Jn.no_permissions
        self.message = message

    def __str__(self):
        return self.message


class InvalidResponse(MoodleError):
    def __init__(self, message, debug_message):
        self.exception_name = Jn.invalid_response_exception
        self.error_code = Jn.invalid_response_exception_errorcode
        self.message = message
        self.debug_message = debug_message

    def __str__(self):
        return self.message + self.debug_message

# webservice_access_exception accessexception Access Control Exception Invalid token - token expired - check validuntil time for the token

# when asking for a unknown module ID, translates to nothing found, I guess.
# {
#   "message": "Datensatz kann nicht in der Datenbank gefunden werden",
#   "exception": "dml_missing_record_exception",
#   "errorcode": "invalidrecordunknown"
#   "debuginfo": "SELECT md.name\n                                                 FROM {modules} md\n                                                 JOIN {course_modules} cm ON cm.module = md.id\n                                                WHERE cm.id = :cmid\n[array (\n  'cmid' => 117242,\n)]",
# }
