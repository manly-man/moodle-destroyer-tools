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
