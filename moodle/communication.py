import mimetypes
import os
import json

import requests

from moodle.exceptions import MoodleException

from moodle.fieldnames import text_format as moodle_text_format
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.parsers import strip_mlang

import logging

log = logging.getLogger('moodle.communication')


class MoodleSessionCore(requests.Session):
    ws_path = '/webservice/rest/server.php'

    def __init__(self, moodle_url, token=None, rest_format='json'):
        super().__init__()
        self.token = token

        if moodle_url.startswith('http://'):
            moodle_url = 'https://' + moodle_url[4:]
        if not moodle_url.startswith('https://'):
            moodle_url = 'https://' + moodle_url
        self.rest_format = rest_format
        self.url = moodle_url

    def post_web_service(self, ws_function, args=None):
        needed_args = {
            Jn.moodle_ws_rest_format: self.rest_format,
            Jn.ws_token: self.token,
            Jn.ws_function: ws_function
        }
        if args is None:
            args = needed_args
        else:
            args.update(needed_args)

        response = self.post(self.url + self.ws_path, args)

        if 'json' != self.rest_format:
            return response.text

        try:
            payload = json.loads(strip_mlang(response.text))
            if isinstance(payload, dict) and 'exception' in payload:
                raise MoodleException.generate_exception(**payload)
            return payload
        except json.JSONDecodeError:
            log.error(f'moodle sent an unexpected response:\n {response.text}')
            raise SystemExit(1)

    def get_token(self, user_name, password, service='moodle_mobile_app'):
        """
        Request a token for a specific web service
        A service is defined by your admin.
        It is defines a set of functions activated for the service.
        use get_site_info() to retrieve the exported function set.
        Most Moodle platforms have the Moodle Mobile Service active, I think it is enabled by default.
        'documented' at https://docs.moodle.org/dev/Creating_a_web_service_client#How_to_get_a_user_token
        and https://github.com/moodle/moodle/blob/master/login/token.php

        :param user_name: the user name
        :param password: password
        :param service: defaults to 'moodle_mobile_app'
        :return: a token or one of many exceptions -.-
        """
        endpoint = '/login/token.php'
        data = {
            Jn.user_name: user_name,
            Jn.password: password,
            Jn.service: service
        }
        response = self.post(self.url + endpoint, data)

        try:
            payload = response.json()
        except json.JSONDecodeError:
            log.error(f'Moodle returned unexpected values, expected valid json:\n {response.text}')
            raise SystemExit(1)

        try:
            return payload[Jn.token]
        except KeyError:
            if payload.get('errorcode', None) == 'invalidlogin':
                log.warning(f'wrong authentication information?\n {str(payload)}')
            else:
                log.error(f'Something went wrong:\n {str(payload)}')

    def upload_files(self, fd_list, file_path='/', file_area='draft', item_id=0):
        endpoint = '/webservice/upload.php'
        mimetypes.init()

        upload_info = []
        for num, fd in enumerate(fd_list):
            file_number = f'file_{num:d}'
            file_name = os.path.basename(fd.name)
            (file_type, encoding) = mimetypes.guess_type(fd.name)
            upload_info.append((file_number, (file_name, fd, file_type)))

        log.debug(str(upload_info))

        data = {
            Jn.file_path: file_path,
            Jn.file_area: file_area,
            Jn.item_id: item_id,
            Jn.token: self.token
        }

        response = self.post(self.url + endpoint, data, files=upload_info)
        if 'json' != self.rest_format:
            return response.text

        try:
            payload = json.loads(response.text)
            if isinstance(payload, dict) and 'exception' in payload:
                raise MoodleException.generate_exception(**payload)
            return payload
        except json.JSONDecodeError:
            log.error(f'moodle sent an unexpected response, expected valid json:\n {response.text}')
            raise SystemExit(1)

    def download_file(self, file_url):
        args = {Jn.token: self.token}
        return self.post(file_url, args)


class MoodleSession(MoodleSessionCore):
    def mod_assign_save_submission(self, assignment_id, text='', text_format=0, text_file_id=0, files_id=0):
        data = {
            Jn.assignment_id: assignment_id,
            Jn.plugin_data_online_text: text,
            Jn.plugin_data_online_text_format: text_format,
            Jn.plugin_data_online_text_item_id: text_file_id,
            Jn.plugin_data_submission_files_item_id: files_id
        }
        return self.post_web_service('mod_assign_save_submission', args=data)

    def mod_assign_save_grade(self, assignment_id, user_id, grade,
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
            Jn.assignment_id: assignment_id,
            Jn.user_id: user_id,
            Jn.grade: grade,
            Jn.attempt_number: attempt_number,
            Jn.add_attempt: 0,
            Jn.workflow_state: workflow_state,
            Jn.apply_to_all: 0,
            Jn.assign_feedback_text: feedback_text,
            Jn.assign_feedback_format: moodle_text_format[feedback_format],
            Jn.assign_feedback_file: feedback_draft_area_id
        }

        if team_submission:
            data[Jn.apply_to_all] = 1
        if add_attempt:
            data[add_attempt] = 1

        return self.post_web_service('mod_assign_save_grade', args=data)

    def mod_assign_get_assignments(self, course_ids=None, capabilities=None, include_not_enrolled_courses=False):
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
            Jn.course_ids: course_ids,
            Jn.capabilities: capabilities,
            # fn.include_not_enrolled_courses: include_not_enrolled_courses, #  moodle 3.2
        }

        return self.post_web_service('mod_assign_get_assignments', data)

    def mod_assign_get_grades(self, assignment_ids, since=0):
        """
        Get grades from the Assignment

        :param assignment_ids: list of assignment ids to get grades for.
        :param since: timestamp, only return records where timemodified >= since, default=0
        :return: list of grades, contained in assignments.
        """
        data = {
            Jn.assignment_ids: assignment_ids,
            Jn.since: since,
        }
        return self.post_web_service('mod_assign_get_grades', data)

    def mod_assign_get_submissions(self, assignment_ids, status='', since=0, before=0):
        """
        Requests submission metadata for assignments.

        :param assignment_ids: list of assignment ids to get the data for.
        :param status: filter by status, dunno what that could be.
        :param since: get only submissions since timestamp
        :param before: get only submissions before timestamp
        :return: submission meta data contained in assignment list.
        """
        data = {
            Jn.assignment_ids: assignment_ids,
            Jn.status: status,
            Jn.since: since,
            Jn.before: before,
        }

        return self.post_web_service('mod_assign_get_submissions', data)

    def core_enrol_get_users_courses(self, user_id):
        """
        Get the list of courses where a user is enrolled in

        :param user_id: the user id to get courses from
        :return: list of courses where the user is enrolled in.
        """
        data = {
            Jn.user_id: user_id,
        }

        return self.post_web_service('core_enrol_get_users_courses', data)

    def core_enrol_get_enrolled_users(self, course_id, options=None):
        """
        request a list of all users, can filter by options:
        :param course_id: the course id where you want to get the users for.
        :param options: a dict with one of the following values:
        * withcapability (string) return only users with this capability.
                            This option requires 'moodle/role:review' on the course context.
        * groupid (integer) return only users in this group id. If the course has groups enabled and this param
                            isn't defined, returns all the viewable users.
                            This option requires 'moodle/site:accessallgroups' on the course context if the
                            user doesn't belong to the group.
        * onlyactive (integer) return only users with active enrolments and matching time restrictions.
                            This option requires 'moodle/course:enrolreview' on the course context.
        * userfields ('string, string, ...') return only the values of these user fields.
        * limitfrom (integer) sql limit from.
        * limitnumber (integer) maximum number of returned users.
        * sortby (string) sort by id, firstname or lastname. For ordering like the site does, use siteorder.
        * sortdirection (string) ASC or DESC
        :return: a list of users
        """
        data = {
            Jn.course_id: course_id
        }
        # moodle takes these options like options[0][name]=key, options[0][value]=value
        if options is not None:
            for num, (key, value) in enumerate(options.items()):
                data.update({
                    Jn.options.format(num, Jn.name): key,
                    Jn.options.format(num, Jn.value): value,
                })

        return self.post_web_service('core_enrol_get_enrolled_users', data)

    def core_enrol_get_course_enrolment_methods(self, course_id):
        # a possible response
        # [
        #     {
        #         "courseid": 1234,
        #         "wsfunction": "enrol_self_get_instance_info",
        #         "type": "self",
        #         "name": "Selbsteinschreibung (Student)",
        #         "id": 45673,
        #         "status": true
        #     }
        # ]

        data = {
            Jn.course_id: course_id,
        }
        return self.post_web_service('core_enrol_get_course_enrolment_methods', args=data)

    def enrol_self_enrol_user(self, course_id, password='', instance_id=0):
        """
        enrol self in course
        :param course_id: course id to enrol in
        :param password: password for enrollment
        :param instance_id: instance id of self enrolment plugin
        :return:
        """
        data = {
            Jn.course_id: course_id,
            Jn.password: password,
            Jn.instance_id: instance_id,
        }
        return self.post_web_service('enrol_self_enrol_user', args=data)

    def gradereport_user_get_grades_table(self, course_id, user_id=0):
        """
        Retrieves the grade report table.

        :param course_id: the course you want the table from
        :param user_id: if not set, all users tables will be retreived (SLOW)
        :return: the grade table
        """
        data = {
            Jn.course_id: course_id,
            Jn.user_id: user_id
        }
        return self.post_web_service('gradereport_user_get_grades_table', args=data)

    def core_course_search_courses(self, criteria_value, criteria_name='search', page=0, per_page=0,
                                   required_capabilities=None, limit_to_enrolled=0):
        """
        Search Moodle for courses.

        :param criteria_value: the words you want to search for
        :param criteria_name: where you want to search in? not sure. default is 'search'
        (search, modulelist (only admins), blocklist (only admins), tagid)
        :param page: if you set per_page to anything else, you select which one you want to get
        :param per_page: how many items per page, starting from 0
        :param required_capabilities: I dunno, moodle doc says it whould be required and documentation is '2'
        :param limit_to_enrolled: display only enrolled courses, could be boolean?
        :return:
        """

        data = {
            Jn.criteria_name: criteria_name,
            Jn.criteria_value: criteria_value
        }

        return self.post_web_service('core_course_search_courses', args=data)

    def core_webservice_get_site_info(self):
        """Requests meta data about the site and user.
        Contains user preferences and some "capabilities".
        Also contains a list of functions allowed by the web service.

        :return: said info
        """
        return self.post_web_service('core_webservice_get_site_info')

    def core_files_get_files(self, context_id, item_id,
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
        :param context_level: (block, course, coursecat, system, user, module)
        :param instance_id:
        :return: what you asked for … welp?
        """
        data = {
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

        return self.post_web_service('core_files_get_files', args=data)

    def core_course_get_contents(self, course_id, options=None):
        """
        get course content

        :param course_id: the course id you want to get contents of
        :param options:
        * excludemodules (bool) Do not return modules, return only the sections structure
        * excludecontents (bool) Do not return module contents (i.e: files inside a resource)
        * sectionid (int) Return only this section
        * sectionnumber (int) Return only this section with number (order)
        * cmid (int) Return only this module information (among the whole sections structure)
        * modname (string) Return only modules with this name "label, forum, etc..."
        * modid (int) Return only the module with this id (to be used with modname)

        :return: the course content
        """

        data = {
            Jn.course_id: course_id
        }

        if options is not None:
            for num, (key, value) in enumerate(options.items()):
                data.update({
                    Jn.options.format(num, Jn.name): key,
                    Jn.options.format(num, Jn.value): value,
                })

        return self.post_web_service('core_course_get_contents', args=data)
