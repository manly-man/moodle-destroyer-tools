import moodle.models as models
from moodle.exceptions import AccessDenied, InvalidResponse
from util.worktree import WorkTree


class MoodleFrontend:
    def __init__(self, url, token, worktree=None):
        # todo, read course from worktree config.
        from moodle.communication import MoodleSession
        self.url = url
        self.token = token
        self.worktree = worktree or WorkTree()
        self.session = MoodleSession(moodle_url=self.url, token=self.token)

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

