import glob
import json
import os
import re
import configparser
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.models import Course, Assignment, Submission
from util.resources import AssignmentMetaDataFolder, SubmissionMetaDataFolder, GradeMetaDataFolder


class WorkTree:
    def __init__(self, init=False, force=False, skip_init=False):
        if skip_init:
            return

        self.root = self.get_work_tree_root()
        if self.root is None and not init:
            raise NotInWorkTree()

        if init:
            self.root = self._initialize(force)

        self.meta_root = self.root + '.mdt/'
        self.config = self.meta_root + 'config'
        self.user_meta = self.meta_root + 'users'
        self.sync_meta = self.meta_root + 'sync'
        self.moodle_meta = self.meta_root + 'moodle'
        self.course_meta = self.meta_root + 'courses'
        self.assignment_meta = self.meta_root + 'assignments'
        self.submission_meta = self.meta_root + 'submissions'
        self.grade_meta = self.meta_root + 'grades'

        self._course_data = self._load_json_file(self.course_meta)
        self._user_data = self._load_json_file(self.user_meta)
        self._assignment_data = AssignmentMetaDataFolder(self.assignment_meta)
        self._submission_data = SubmissionMetaDataFolder(self.submission_meta)
        self._grade_data = GradeMetaDataFolder(self.grade_meta)

    @staticmethod
    def _initialize(force):
        try:
            os.makedirs('.mdt/assignments', exist_ok=force)
            os.makedirs('.mdt/submissions', exist_ok=force)
            os.makedirs('.mdt/grades', exist_ok=force)
            if force or not os.path.isfile('.mdt/users'):
                with open('.mdt/users', 'w') as users:
                    users.write('[]')
            if force or not os.path.isfile('.mdt/courses'):
                with open('.mdt/courses', 'w') as courses:
                    courses.write('[]')
            return os.getcwd() + '/'
        except FileExistsError:
            raise

    @staticmethod
    def global_config():
        if 'XDG_CONFIG_HOME' in os.environ:
            if os.path.isfile(os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'):
                return os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
        elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
            return os.path.expanduser('~/.config/mdtconfig')
        elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
            return os.path.expanduser('~/.mdtconfig')
        else:
            return WorkTree.create_global_config_file()

    @staticmethod
    def create_global_config_file():
        file = ''
        if 'XDG_CONFIG_HOME' in os.environ:
            if os.path.isdir(os.environ['XDG_CONFIG_HOME']):
                file = os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
        elif os.path.isdir(os.path.expanduser('~/.config')):
            file = os.path.expanduser('~/.config/mdtconfig')
        else:
            file = os.path.expanduser('~/.mdtconfig')
        text = 'could not find global config, creating {}'
        print(text.format(file))
        open(file, 'w').close()
        return file

    @staticmethod
    def get_config_file_list():
        global_config = WorkTree.global_config()
        cfg_files = [global_config]
        work_tree = WorkTree.get_work_tree_root()
        if work_tree is not None:
            # default_config_files order is crucial: work_tree cfg overrides global
            cfg_files.append(work_tree + '/.mdt/config')
        return cfg_files

    @staticmethod
    def get_work_tree_root():
        """ determines the work tree root by looking at the .mdt folder in cwd or parent folders
        :returns the work tree root as String or None
        """
        cwd = os.getcwd()
        repo = None
        while not os.path.isdir('.mdt'):
            if '/' == os.getcwd():
                os.chdir(cwd)
                return None
            os.chdir(os.pardir)
        if os.path.isdir('.mdt'):
            repo = os.getcwd()
        os.chdir(cwd)
        return repo + '/'

    @property
    def in_root(self):
        return os.path.isdir('.mdt')

    @property
    def in_tree(self):
        return self.root is not None

    @property
    def data(self):
        cs = []
        for c in self.courses.values():
            course = Course(c)

            course.users = self.users[str(course.id)]
            course.assignments = [a for a in self.assignments.values() if a[Jn.course] == course.id]
            for assignment in course.assignments.values():
                assignment.submissions = self.submissions.get(assignment.id, None)
                assignment.grades = self.grades.get(assignment.id, None)
            cs.append(course)
        return cs

    @property
    def assignments(self):
        return self._assignment_data

    @property
    def submissions(self):
        return self._submission_data

    @property
    def courses(self):
        courses = {}
        for course in self._course_data:
            courses[course['id']] = course
        return courses

    @courses.setter
    def courses(self, value):
        self._write_data(self.course_meta, value)
        self._course_data = value

    @property
    def grades(self):
        return self._grade_data

    @property
    def users(self):
        return self._user_data

    @users.setter
    def users(self, value):
        self._write_data(self.user_meta, value)
        self._user_data = value

    @staticmethod
    def _load_json_file(filename):
        try:
            with open(filename) as file:
                return json.load(file)
        except json.decoder.JSONDecodeError as e:
            print(e)
            pass

    @staticmethod
    def _write_config(path, data):
        with open(path, 'w') as file:
            file.write(data)

    @staticmethod
    def _write_data(path, data):
        with open(path, 'w') as file:
            json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)

    def _merge_json_data_in_folder(self, path):
        files = glob.glob(path + '*')
        data_list = [self._load_json_file(file) for file in files]
        return data_list

    @staticmethod
    def write_global_config(config_dict):
        with open(WorkTree.global_config(), 'w') as file:
            cfg_parser = configparser.ConfigParser()
            cfg_parser['global moodle settings'] = config_dict
            cfg_parser.write(file)

    def write_local_config(self, config_data):
        self._write_config(self.config, config_data)

    @staticmethod
    def safe_file_name(name):
        return re.sub(r'\W', '_', name)

    @staticmethod
    def assignment_folder(assignment):
        return WorkTree.safe_file_name('{}--{:d}'.format(assignment.name, assignment.id)) + '/'

    def write_grading_and_html_file(self, assignment):
        a_folder = self.assignment_folder(assignment)
        filename = 'gradingfile.json'
        if os.path.isfile(a_folder + filename):
            new_name = 'gradingfile_{:02d}.json'
            i = 0
            filename = new_name.format(i)
            while os.path.isfile(a_folder + filename):
                i += 1
                filename = new_name.format(i)
            print('grading file exists, writing to: {}'.format(filename))
        os.makedirs(a_folder, exist_ok=True)

        with open(a_folder + filename, 'w') as grading_file:
            grading_file.write(assignment.grading_file_content)

        html = assignment.merged_html
        if html is not None:
            with open(a_folder + '00_merged_submissions.html', 'w') as merged_html:
                merged_html.write(html)

    def create_folders(self, files):
        folders = set([os.path.dirname(f.path) for f in files])
        for folder in folders:
            os.makedirs(folder, exist_ok=True)

    def write_submission_file(self, file, content):
        with open(file.path, 'wb') as fd:
            fd.write(content)

    def prepare_download(self, assignments):
        files = []
        for a in assignments:
            for s in a.submissions.values():
                a_folder = self.assignment_folder(a)
                s_files = s.files
                if len(s_files) > 1:
                    s_folder = a_folder + '/' + self.safe_file_name(s.prefix)
                    for file in s_files:
                        file.path = s_folder + file.path
                        files.append(file)
                        # print(folder + file.path)
                elif len(s_files) == 1:
                    file = s_files[0]
                    path = a_folder + '/' + self.safe_file_name(s.prefix) + '--'
                    path += file.path[1:].replace('/', '_')
                    file.path = path
                    files.append(file)
        self.create_folders(files)
        return files


class NotInWorkTree(Exception):
    def __init__(self):
        self.message = 'You are not in an initialized work tree. Go get one.'

    def __str__(self):
        return self.message
