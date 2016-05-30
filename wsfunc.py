
class MoodleWebServiceFunction:
    def __init__(self, function, required_args={}, optional_args={}):
        self.implements = function
        self.required_args = required_args
        self.optional_args = optional_args

    def data(self, **args):
        self.check_args(**args)
        data = {}
        for key, value in args.items():
            if type(value) is list:
                data[key+'[]'] = value
            else:
                data[key] = value
        return data

    def check_args(self, **args):
        for arg_name, arg_type in self.required_args.items():
            if arg_name not in args:
                raise TypeError('required argument {} not in arguments', arg_name)
            elif type(args[arg_name]) is not arg_type:
                raise TypeError('arg: {} is type {}, expected: {}'.format(arg_name, type(args[arg_name]), arg_type))


get_course_list = MoodleWebServiceFunction(
    function='core_enrol_get_users_courses',
    required_args={'userid': int}
)


get_grades = MoodleWebServiceFunction(
    function='mod_assign_get_grades',
    required_args={'assignmentids': list},
    optional_args={'since': int}  # timestamp,  only return records, where timemodified >= since
)
