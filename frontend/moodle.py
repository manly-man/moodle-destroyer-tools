import concurrent.futures as cf
import json
from datetime import datetime
import math

import moodle.models as models
from frontend.models import Submission, GradingFile, Assignment, Course
from moodle.exceptions import AccessDenied, InvalidResponse
from persistence.worktree import WorkTree
from util import interaction

MAX_WORKERS = 10


class MoodleFrontend:
    def __init__(self, worktree=None):
        # todo, read course from worktree config.
        from moodle.communication import MoodleSession
        self.worktree = worktree or WorkTree()
        self.config = WorkTree.get_global_config_values()
        self.session = MoodleSession(moodle_url=self.config.url, token=self.config.token)

    @property
    def course_ids(self):
        return self.worktree.courses.keys()

    @property
    def assignment_ids(self):
        return self.worktree.assignments.keys()

    def sync_assignments(self):
        response = self.session.mod_assign_get_assignments(self.course_ids)
        wrapped = models.CourseAssignmentResponse(response)
        result = self.worktree.assignments.update(wrapped.raw)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def sync_users(self):
        # limit collected information to only relevant bits. is faster and can possibly work around some moodle bugs.
        sync_fields = ['fullname', 'groups', 'id']
        options = {'userfields': ','.join(sync_fields)}

        users = {}
        output = ""
        for cid in self.course_ids:
            try:
                response = self.session.core_enrol_get_enrolled_users(course_id=cid, options=options)
                users[int(cid)] = response
                output += '{:5d}:got {:4d}\n'.format(cid, len(response))
            except AccessDenied as denied:
                message = '{:d} denied access to users: {}\n'.format(cid, denied)
                output += message
            except InvalidResponse as e:
                message = 'Moodle encountered an error: msg:{} \n debug:{}\n'.format(e.message, e.debug_message)
                output += message

        self.worktree.users = users

        return output

    def sync_submissions(self):
        now = math.floor(datetime.now().timestamp())
        response = self.session.mod_assign_get_submissions(self.assignment_ids,
                                                           since=self.worktree.submissions.last_sync)
        result = self.worktree.submissions.update(response, now)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def sync_grades(self):
        now = math.floor(datetime.now().timestamp())
        response = self.session.mod_assign_get_grades(self.assignment_ids, since=self.worktree.grades.last_sync)
        result = self.worktree.grades.update(response, now)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def get_course_list(self):
        wrapped = models.CourseListResponse(self.session.core_enrol_get_users_courses(self.config.user_id))
        return wrapped

    def sync_file_meta_data(self):
        files = []
        for as_id, submissions in self.worktree.submissions.items():
            for submission in submissions:
                files += Submission(submission).files

        for file in files:
            wrapped = models.FileMetaDataResponse(self.session.core_files_get_files(**file.meta_data_params))
            print(str(wrapped.raw))
            # reply = moodle.get_submissions_for_assignments(wt.assignments.keys())
            # data = json.loads(strip_mlang(reply.text))
            # result = wt.submissions.update(data)
            # output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
            # print('finished. ' + ' '.join(output))

    def download_files(self, assignment_ids=None):

        courses = self.worktree.data
        assignments = []
        if assignment_ids is None:
            for c in courses:
                assignments += c.assignments.values()
        else:
            for c in courses:
                assignments += c.get_assignments(assignment_ids)

        files = self.worktree.prepare_download(assignments)

        file_count = len(files)
        counter = 0
        # todo, error handling
        if file_count > 0:
            interaction.print_progress(counter, file_count)
            with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as tpe:
                future_to_file = {tpe.submit(self.session.download_file, file.url): file for file in files}
                for future in cf.as_completed(future_to_file):
                    file = future_to_file[future]
                    response = future.result()
                    counter += 1
                    interaction.print_progress(counter, file_count, suffix=file.path)
                    self.worktree.write_submission_file(file, response.content)
        for a in assignments:
            self.worktree.write_grading_and_html_file(a)

    def upload_grades(self, upload_data):
        def argument_list(upload_data):
            for grades in upload_data:
                as_id = grades.assignment_id
                team = grades.team_submission
                args = []
                for values in grades.grades:
                    args.append({
                        'assignment_id': as_id,
                        'user_id': values.id,
                        'grade': values.grade,
                        'feedback_text': values.feedback,
                        'team_submission': team
                    })
                return args

        args_list = argument_list(upload_data)
        grade_count = len(args_list)
        counter = 0

        if grade_count > 0:
            interaction.print_progress(counter, grade_count)
            with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as tpe:
                future_to_grade = {tpe.submit(self.session.mod_assign_save_grade, **args): args for args in args_list}
                for future in cf.as_completed(future_to_grade):
                    args = future_to_grade[future]
                    response = future.result()
                    counter += 1
                    interaction.print_progress(counter, grade_count)

    def upload_files(self, files):
        # TODO, Wrap and return it, don't print. do print in wstools.upload. also modify submit
        response = self.session.upload_files(files)
        text = response
        print(json.dumps(text, indent=2, ensure_ascii=False))
        return text

    def search_courses_by_keywords(self, keyword_list):
        # TODO: wrap and return to wstools.enrol
        response = self.session.core_course_search_courses(' '.join(keyword_list))
        return response

    def get_course_enrolment_methods(self, course_id):
        # TODO: wrap and return to wstools.enrol
        response = self.session.core_enrol_get_course_enrolment_methods(course_id)
        return response

    def enrol_in_course(self, course_id, instance_id, password=''):
        # TODO: wrap and return to wstools.enrol
        response = self.session.enrol_self_enrol_user(course_id, instance_id=instance_id, password=password)
        return response

    def save_submission(self, assignment_id, text='', text_format=0, text_file_id=0, files_id=0):
        # TODO: wrap and return to wstools.submit
        response = self.session.mod_assign_save_submission(assignment_id, text, text_format, text_file_id, files_id)
        return response

    @classmethod
    def get_token(cls, url, user, password, service):
        # TODO: wrap and return to wstools.auth
        from moodle.communication import MoodleSession

        session = MoodleSession(moodle_url=url)
        token = session.get_token(user_name=user, password=password, service=service)

        return token

    def get_user_id(self):
        # TODO: wrap and return to wstools.auth
        from moodle.fieldnames import JsonFieldNames as Jn
        data = self.session.core_webservice_get_site_info()
        return data[Jn.user_id]

    def parse_grade_files(self, fd_list):
        """
        this mostly rewrites the values read from the grading file.
        since most of this can be done, when creating the grading file
        it should be done there.
        Namely, adding a team_submission field and instead of
        setting the submission.id in the file, use the user.id instead

        :param fd_list:
        :return:
        """

        upload_data = []

        print('this will upload the following grades:')
        grade_format = '  {:>20}:{:6d} {:5.1f} > {}'

        invalid_values = []

        for file in fd_list:
            wrapped = GradingFile(json.load(file))

            assignment = Assignment(self.worktree.assignments[wrapped.assignment_id])
            assignment.course = Course(self.worktree.courses[assignment.course_id])

            assignment.course.users = self.worktree.users[str(assignment.course_id)]
            assignment.submissions = self.worktree.submissions[assignment.id]

            wrapped.team_submission = assignment.is_team_submission

            print(' assignment {:5d}, team_submission: {}'.format(assignment.id,
                                                                  assignment.is_team_submission))

            for grade in wrapped.grades:
                submission = assignment.submissions[grade.id]

                if assignment.is_team_submission:
                    group = assignment.course.groups[submission.group_id]
                    user = group.members[0]
                    grade.id = user.id
                else:
                    grade.id = submission.user_id

                if assignment.max_points < grade.grade:
                    invalid_values.append(grade)

                print(grade_format.format(grade.name, grade.id, grade.grade, grade.feedback[:40]))

            upload_data.append(wrapped)

        if len(invalid_values) > 0:
            for grade in invalid_values:
                print(
                    "WARNING: the grade value is larger than the max achievable grade")
                print(grade_format.format(grade.name, grade.id, grade.grade, grade.feedback[:40]))
            raise SystemExit(1)

        answer = input('does this look good? [Y/n]: ')

        if 'n' == answer:
            print('do it right, then')
            return
        elif not ('y' == answer or '' == answer):
            print('wat')
            return

        return upload_data
