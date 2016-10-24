import moodle.models as models
from moodle.frontend.models import Submission
from moodle.exceptions import AccessDenied, InvalidResponse
from util.worktree import WorkTree
from util import interaction
import concurrent.futures as cf
import json

MAX_WORKERS = 10

class MoodleFrontend:
    def __init__(self, worktree=None):
        # todo, read course from worktree config.
        from moodle.communication import MoodleSession
        self.worktree = worktree or WorkTree()
        self.config = WorkTree.get_global_config_values()
        self.session = MoodleSession(moodle_url=self.config.url, token=self.config.token)

    @property
    def course_ids(self): return self.worktree.courses.keys()

    @property
    def assignment_ids(self): return self.worktree.assignments.keys()

    def sync_assignments(self):
        response = self.session.get_assignments(self.course_ids)
        wrapped = models.CourseAssignmentResponse(response)
        result = self.worktree.assignments.update(wrapped.mlang_stripped_json)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def sync_users(self):
        users = {}
        output = ""
        for cid in self.course_ids:
            try:
                wrapped = models.EnrolledUsersListResponse(self.session.get_enrolled_users(course_id=cid))
                users[int(cid)] = wrapped.mlang_stripped_json
                output += '{:5d}:got {:4d}\n'.format(cid, len(wrapped))
            except AccessDenied as denied:
                message = '{:d} denied access to users: {}\n'.format(cid, denied)
                output += message
            except InvalidResponse as e:
                message = 'Moodle encountered an error: msg:{} \n debug:{}\n'.format(e.message, e.debug_message)
                output += message

        self.worktree.users = users

        return output

    def sync_submissions(self):
        response = self.session.get_submissions_for_assignments(self.assignment_ids, since=self.worktree.submissions.last_sync)
        wrapped = models.AssignmentSubmissionResponse(response)
        result = self.worktree.submissions.update(wrapped.mlang_stripped_json)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def sync_grades(self):
        response = self.session.get_grades(self.assignment_ids, since=self.worktree.grades.last_sync)
        wrapped = models.AssignmentGradeResponse(response)
        result = self.worktree.grades.update(wrapped.mlang_stripped_json)
        output = ['{}: {:d}'.format(k, v) for k, v in result.items()]
        return output

    def get_course_list(self):
        wrapped = models.CourseListResponse(self.session.get_users_course_list(self.config.user_id))
        return wrapped

    def sync_file_meta_data(self):
        files = []
        for as_id, submissions in self.worktree.submissions.items():
            for submission in submissions:
                files += Submission(submission).files

        for file in files:
            wrapped = models.FileMetaDataResponse(self.session.get_file_meta(**file.meta_data_params))
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
            for grades_assignment in upload_data:
                as_id = grades_assignment['assignment_id']
                team = grades_assignment['team_submission']
                args = []
                for gdata in grades_assignment['grade_data']:
                    args.append({
                        'assignment_id': as_id,
                        'user_id': gdata['user_id'],
                        'grade': gdata['grade'],
                        'feedback_text': gdata['feedback'],
                        'team_submission': team
                    })
                return args

        args_list = argument_list(upload_data)
        grade_count = len(args_list)
        counter = 0

        if grade_count > 0:
            interaction.print_progress(counter, grade_count)
            with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as tpe:
                future_to_grade = {tpe.submit(self.session.save_grade, **args): args for args in args_list}
                for future in cf.as_completed(future_to_grade):
                    args = future_to_grade[future]
                    response = future.result()
                    counter += 1
                    interaction.print_progress(counter, grade_count)

    def upload_files(self, files):
        # TODO, Wrap and return it, don't print. do print in wstools.upload. also modify submit
        response = self.session.upload_files(files)
        text = response.json()
        print(json.dumps(text, indent=2, ensure_ascii=False))
        return text

    def search_courses_by_keywords(self, keyword_list):
        # TODO: wrap and return to wstools.enrol
        response = self.session.search_for_courses(' '.join(keyword_list))
        return response.json()

    def get_course_enrolment_methods(self, course_id):
        # TODO: wrap and return to wstools.enrol
        response = self.session.get_course_enrolment_methods(course_id)
        return response.json()

    def enrol_in_course(self, course_id, instance_id, password=''):
        # TODO: wrap and return to wstools.enrol
        response = self.session.enrol_in_course(course_id, instance_id=instance_id, password=password)
        return response.json()

    def save_submission(self, assignment_id, text='', text_format=0, text_file_id=0, files_id=0):
        # TODO: wrap and return to wstools.submit
        response = self.session.save_submission(assignment_id, text, text_format, text_file_id , files_id)
        return response.json()

    def get_token(self, url, user, password, service):
        # TODO: wrap and return to wstools.auth
        from moodle.communication import MoodleSession
        from moodle.fieldnames import JsonFieldNames as Jn
        self.session = MoodleSession(moodle_url=url)
        response = self.session.get_token(user_name=user, password=password, service=service)
        try:
            j = response.json()
            token = j[Jn.token]
            self.session.token = token
        except KeyError:
            print(response.text)
            raise SystemExit(1)

        return token

    def get_user_id(self):
        # TODO: wrap and return to wstools.auth
        from moodle.fieldnames import JsonFieldNames as Jn
        data = self.session.get_site_info().json()
        return data[Jn.user_id]
