import mimetypes
import os

import requests
from requests.adapters import HTTPAdapter

from urllib.parse import parse_qs

import moodle.exceptions
from moodle.fieldnames import text_format
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.fieldnames import UrlPaths as Paths
from moodle.parsers import strip_mlang


# TODO handle ws exceptions in sensible manner, collate warnings: MoodleAdapter?
# TODO check if server supports wsfunction


class MoodleSession(requests.Session):
    def __init__(self, moodle_url, token=None):
        super(MoodleSession, self).__init__()
        self.ws_path = Paths.web_service
        self.token = token
        if moodle_url.startswith('http://'):
            moodle_url = 'https://' + moodle_url[4:]
        if not moodle_url.startswith('https://'):
            moodle_url = 'https://' + moodle_url
        self.url = moodle_url
        self.mount('https://', MoodleAdapter())

    def post_web_service(self, data=None):
        needed_args = {
                Jn.moodle_ws_rest_format: 'json',
                Jn.ws_token: self.token,
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
            Jn.ws_function: 'core_enrol_get_users_courses',
            Jn.user_id: user_id,
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
            Jn.ws_function: 'mod_assign_get_assignments',
            Jn.course_ids: course_ids,
            Jn.capabilities: capabilities,
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
            Jn.ws_function: 'mod_assign_get_grades',
            Jn.assignment_ids: assignment_ids,
            Jn.since: since,
        }
        return self.post_web_service(data)

    def get_site_info(self):
        """Requests meta data about the site and user.
        Contains user preferences and some "capabilities".
        Also contains a list of functions allowed by the web service.

        :return: said info
        """
        data = {Jn.ws_function: 'core_webservice_get_site_info'}
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
            Jn.ws_function: 'mod_assign_get_submissions',
            Jn.assignment_ids: assignment_ids,
            Jn.status: status,
            Jn.since: since,
            Jn.before: before,
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
            Jn.ws_function: 'core_enrol_get_enrolled_users',
            Jn.course_id: course_id
        }
        # moodle takes these options like options[0][name]=key, options[0][value]=value
        if options is not None:
            for num, (key, value) in enumerate(options.items(), 0):
                data.update({
                    Jn.options.format(num, Jn.name): key,
                    Jn.options.format(num, Jn.value): value,
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
            Jn.ws_function: 'core_files_get_files',
            Jn.context_id: context_id,
            Jn.component: component,
            Jn.file_area: file_area,
            Jn.item_id: item_id,
            Jn.file_path: file_path,
            Jn.file_name: file_name,
            Jn.modified: since,
            Jn.context_level: context_level,
            Jn.instance_id: instance_id,
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
            Jn.user_name: user_name,
            Jn.password: password,
            Jn.service: service
        }
        return self.post(self.url+Paths.token, data)

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
            Jn.ws_function: 'mod_assign_save_grade',
            Jn.assignment_id: assignment_id,
            Jn.user_id: user_id,
            Jn.grade: grade,
            Jn.attempt_number: attempt_number,
            Jn.add_attempt: 0,
            Jn.workflow_state: workflow_state,
            Jn.apply_to_all: 0,
            Jn.assign_feedback_text: feedback_text,
            Jn.assign_feedback_format: text_format[feedback_format],
            Jn.assign_feedback_file: feedback_draft_area_id
        }

        if team_submission:
            data[Jn.apply_to_all] = 1
        if add_attempt:
            data[add_attempt] = 1

        return self.post_web_service(data)

    def upload_files(self, fd_list, file_path='/', file_area='draft', item_id=0):
        mimetypes.init()

        upload_info = []
        for num, fd in enumerate(fd_list, 0):
            upload_info.append(('file_{:d}'.format(num),
                                (os.path.basename(fd.name), fd, mimetypes.guess_type(fd.name)[0])))
        print(str(upload_info))

        data = {
            Jn.file_path: file_path,
            Jn.file_area: file_area,
            Jn.item_id: item_id,
            Jn.token: self.token
        }
        return self.post(self.url+Paths.upload, data, files=upload_info)


class MoodleAdapter(HTTPAdapter):
    def __init__(self, **kwargs):
        super(MoodleAdapter, self).__init__(**kwargs)

    def build_response(self, req, resp):
        response = super().build_response(req, resp)

        called_function = ''
        # check if the request was a web service call, handle response accordingly.
        if Paths.web_service == response.request.path_url:
            params = parse_qs(req.body)
            if Jn.ws_function in params:
                called_function = params[Jn.ws_function]
                print('called function: {}'.format(called_function))

        if called_function != '':
            if 'mod_assign_save_grade' and response.json() is None:
                # success
                return response
            data = response.json()
            if Jn.exception in data:
                self.handle_exception(data)

        return response

    @staticmethod
    def handle_exception(data):
        error_code = data[Jn.error_code]
        if error_code == Jn.no_permissions:
            raise moodle.exceptions.AccessDenied(data[Jn.message])
        elif error_code == Jn.invalid_token:
            raise moodle.exceptions.InvalidToken(data[Jn.message])
        elif error_code == Jn.invalid_response_exception_errorcode:
            raise moodle.exceptions.InvalidResponse(data[Jn.message], data[Jn.debug_info])
        else:
            raise moodle.exceptions.MoodleError(**data)


class MoodleResponse(requests.Response):
    @property
    def text(self):
        return strip_mlang(super().text())