import requests
from moodle.fieldnames import text_format
from moodle.fieldnames import json as fn
from requests.adapters import HTTPAdapter

# TODO handle ws exceptions in sensible manner, collate warnings: MoodleAdapter?


class MoodleSession(requests.Session):
    def __init__(self, moodle_url, token=None):
        super(MoodleSession, self).__init__()
        self.ws_path = '/webservice/rest/server.php'
        self.url = moodle_url
        self.token = token
        # self.mount('https://', MoodleAdapter(moodle_url=moodle_url, token=token))

    def post_web_service(self, data=None):
        needed_args = {
                fn.moodle_ws_rest_format: 'json',
                fn.ws_token: self.token,
        }
        if data is None:
            data = needed_args
        else:
            data.update(needed_args)

        return self.post(self.url + self.ws_path, data)

    def get_users_course_list(self, user_id):
        """
        Get the list of courses where a user is enrolled in

        :param user_id: the user id to get courses from
        :return: list of courses where the user is enrolled in.
        """
        data = {
            fn.ws_function: 'core_enrol_get_users_courses',
            fn.user_id: user_id,
        }

        return self.post_web_service(data)

    def get_assignments(self, course_ids=None, capabilities=None, include_not_enrolled_courses=False):
        """
        Get the list of assignments, the current user has capabilities for.

        :param course_ids: empty for retrieving all the courses where the user is enroled in
        :param capabilities: filter courses by capabilities
        :param include_not_enrolled_courses: whether to return courses that the user can see
            even if is not enroled in. This requires the parameter courseids to not be empty.
        :return: courses and assignments for the users capability
        """
        if capabilities is None:
            capabilities = []
        if course_ids is None:
            course_ids = []
        if include_not_enrolled_courses:
            include_not_enrolled_courses = 1
        else:
            include_not_enrolled_courses = ''
        data = {
            fn.ws_function: 'mod_assign_get_assignments',
            fn.course_ids: course_ids,
            fn.capabilities: capabilities,
            # fn.include_not_enrolled_courses: include_not_enrolled_courses, #  moodle 3.2
        }

        return self.post_web_service(data)

    def get_grades(self, assignment_ids, since=0):
        """
        Get grades from the Assignment

        :param assignment_ids: list of assignment ids to get grades for.
        :param since: timestamp, only return records where timemodified >= since, default=0
        :return: list of grades, contained in assignments.
        """
        data = {
            fn.ws_function: 'mod_assign_get_grades',
            fn.assignment_ids: assignment_ids,
            fn.since: since,
        }
        return self.post_web_service(data)

    def get_site_info(self):
        """
        Requests meta data about the site and user.
        Contains user preferences and some "capabilities".
        Also contains a list of functions allowed by the web service.

        :return: said info
        """
        data = {fn.ws_function: 'core_webservice_get_site_info'}
        return self.post_web_service(data)

    def get_submissions_for_assignments(self, assignment_ids, status='', since=0, before=0):
        """
        Requests submission metadata for assignments.

        :param assignment_ids: list of assignment ids to get the data for.
        :param status: filter by status, dunno what that could be.
        :param since: get only submissions since timestamp
        :param before: get only submissions before timestamp
        :return: submission meta data contained in assignment list.
        """
        data = {
            fn.ws_function: 'mod_assign_get_submissions',
            fn.assignment_ids: assignment_ids,
            fn.status: status,
            fn.since: since,
            fn.before: before,
        }

        return self.post_web_service(data)

    def get_enrolled_users(self, course_id, options=None):
        """
        request a list of all users, can filter by options:
        :param course_id: the course id where you want to get the users for.
        :param options: a dict with one of the following values:
        * withcapability (string) return only users with this capability. This option requires 'moodle/role:review' on the course context.
        * groupid (integer) return only users in this group id. If the course has groups enabled and this param
                            isn't defined, returns all the viewable users.
                            This option requires 'moodle/site:accessallgroups' on the course context if the
                            user doesn't belong to the group.
        * onlyactive (integer) return only users with active enrolments and matching time restrictions. This option requires 'moodle/course:enrolreview' on the course context.
        * userfields ('string, string, ...') return only the values of these user fields.
        * limitfrom (integer) sql limit from.
        * limitnumber (integer) maximum number of returned users.
        * sortby (string) sort by id, firstname or lastname. For ordering like the site does, use siteorder.
        * sortdirection (string) ASC or DESC
        :return: a list of users
        """
        data = {
            fn.ws_function: 'core_enrol_get_enrolled_users',
            fn.course_id: course_id
        }
        # moodle takes these options like options[0][name]=key, options[0][value]=value
        if options is not None:
            for num, (key, value) in enumerate(options.items(), 0):
                data.update({
                    fn.options.format(num, fn.name): key,
                    fn.options.format(num, fn.value): value,
                })

        return self.post_web_service(data)

    def get_file_meta(self, context_id, item_id,
                      component='', file_area='',
                      file_path='', file_name='', since=0,
                      context_level=None, instance_id=None):
        """
        Allows to browse Moodle file areas, it is pretty weird!
        Especially if you try to find all those values o_0, at least I was unsuccessful.
        If you want to access the file meta data, you MUST NOT set file_name!
        I will tell you how to get them from a file's url, the rest is up to you.
        https://XXX/pluginfile.php/105864/assignsubmission_file/submission_files/126296/Submission2_GroupN.zip
        context id: 105864
        component: assignsubmission_file
        file_area: submission_files
        item id: 126296
        file_name: Submission2_GroupN.zip

        :param context_id: Set to -1 to use context_level and instance_id.
        :param item_id:
        :param component:
        :param file_area:
        :param file_path:
        :param file_name:
        :param since:
        :param context_level:
        :param instance_id:
        :return: what you asked for … welp?
        """
        data = {
            fn.ws_function: 'core_files_get_files',
            fn.context_id: context_id,
            fn.component: component,
            fn.file_area: file_area,
            fn.item_id: item_id,
            fn.file_path: file_path,
            fn.file_name: file_name,
            fn.modified: since,
            fn.context_level: context_level,
            fn.instance_id: instance_id,
        }

        return self.post_web_service(data)

    def get_token(self, user_name, password, service='moodle_mobile_app'):
        """
        Request a token for a specific web service
        A service is defined by your admin.
        It is defines a set of functions activated for the service.
        use get_site_info() to retrieve the exported function set.
        Most Moodle platforms have the Moodle Mobile Service active, I think it is enabled by default.

        :param user_name: the user name
        :param password: password
        :param service: defaults to 'moodle_mobile_app'
        :return: a token.
        """
        data = {
            fn.user_name: user_name,
            fn.password: password,
            fn.service: service
        }
        return self.post(self.url+'/login/token.php', data)

    def save_grade(self, assignment_id, user_id, grade,
                   feedback_text='', team_submission=False, feedback_format='plain',
                   attempt_number=-1, add_attempt=False, workflow_state='',
                   feedback_draft_area_id=0):
        """
        Uploads a grade for the user to moodle.

        :param assignment_id: the graded assignment id
        :param user_id: the user receiving the grade
        :param grade: the new grade: ignored if advanced grading is used
        :param team_submission: apply the grade to all members of the group (for group assignments)
        :param feedback_text: your feedback for the user
        :param feedback_format: defaults to plain, refer to moodle.fieldnames.text_format for more possibilities
        :param feedback_draft_area_id: id of a draft area containing files for this feedback
        :param attempt_number: the attempt number (-1 means latest attempt)
        :param add_attempt: allow another attempt if the attempt reopen method is manual
        :param workflow_state: the next marking workflow state
        :return:
        """
        data = {
            fn.ws_function: 'mod_assign_save_grade',
            fn.assignment_id: assignment_id,
            fn.user_id: user_id,
            fn.grade: grade,
            fn.attempt_number: attempt_number,
            fn.add_attempt: 0,
            fn.workflow_state: workflow_state,
            fn.apply_to_all: 0,
            fn.assign_feedback_text: feedback_text,
            fn.assign_feedback_format: text_format[feedback_format],
            fn.assign_feedback_file: feedback_draft_area_id
        }

        if team_submission:
            data[fn.apply_to_all] = 1
        if add_attempt:
            data[add_attempt] = 1

        return self.post_web_service(data)


class MoodleAdapter(HTTPAdapter):
    def __init__(self, moodle_url, token=None, **kwargs):
        self.url = moodle_url
        self.token = token
        super(MoodleAdapter, self).__init__(**kwargs)
