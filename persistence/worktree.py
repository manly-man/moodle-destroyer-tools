import glob
import json
import os
import re

from pathlib import Path

from frontend.models import Course, GlobalConfig
from moodle.fieldnames import JsonFieldNames as Jn
from persistence.models import AssignmentFolder, SubmissionFolder, GradeFolder
from util import zipwrangler


class WorkTree:
    DATA_FOLDER = '.mdt'
    GLOBAL_CONFIG_LOCATIONS = [
        Path.home() / '.config' / 'mdtconfig',
        Path.home() / '.mdtconfig'
    ]
    try:
        xdg = Path(os.environ['XDG_CONFIG_HOME']) / 'mdtconfig'
        GLOBAL_CONFIG_LOCATIONS = [xdg] + GLOBAL_CONFIG_LOCATIONS
    except KeyError:
        pass
    LOCAL_CONFIG = 'config'
    USERS = 'users'
    COURSES = 'courses'
    SYNC = 'sync'
    MOODLE = 'moodle'

    def __init__(self, init=False, force=False, skip_init=False):
        if skip_init:
            return

        self.root = self.find_work_tree_root()
        if self.root is None and not init:
            raise NotInWorkTree()

        if init:
            self.root = self._initialize(force)

        self.data_root = self.root / self.DATA_FOLDER
        self.config = self.data_root / self.LOCAL_CONFIG
        self.user_data = self.data_root / self.USERS
        self.sync_data = self.data_root / self.SYNC
        self.moodle_data = self.data_root / self.MOODLE
        self.course_data = self.data_root / self.COURSES

        self._course_data = self._load_json_file(self.course_data)
        self._user_data = self._load_json_file(self.user_data)
        self._assignment_data = AssignmentFolder(self.data_root, init)
        self._submission_data = SubmissionFolder(self.data_root, init)
        self._grade_data = GradeFolder(self.data_root, init)

    @classmethod
    def _initialize(cls, force):
        try:
            root = Path.cwd() / cls.DATA_FOLDER
            root.mkdir(exist_ok=force)
            users = root / cls.USERS
            courses = root / cls.COURSES
            if force or not users.is_file():
                users.write_text('[]')
            if force or not courses.is_file():
                courses.write_text('[]')
            return Path.cwd()
        except FileExistsError:
            raise

    @classmethod
    def get_global_config_filename(cls):
        for path in cls.GLOBAL_CONFIG_LOCATIONS:
            if path.is_file():
                return path
        else:
            return cls.create_global_config_file()

    @staticmethod
    def get_global_config_values():
        try:
            global_cfg = GlobalConfig(WorkTree._load_json_file(WorkTree.get_global_config_filename()))
        except TypeError:
            config_error_msg = """
            config couldn't be initalized.
            If you created the config yourself, check for proper JSON format.
            """
            raise SystemExit(config_error_msg)
        try:
            local_config_file = WorkTree.get_local_config_file()
            if local_config_file:
                global_cfg.add_overrides(WorkTree._load_json_file(local_config_file))
        except json.JSONDecodeError:
            pass  # probably old ini-style config, ignore it

        return global_cfg

    @staticmethod
    def get_config_values():
        file_names = WorkTree.get_config_file_list()
        global_config = WorkTree.get_global_config_values()
        for name in file_names:
            with open(name) as file:
                try:
                    values = json.load(file)
                    global_config.add_overrides(values)
                except json.decoder.JSONDecodeError:
                    # probably old-style ini config
                    pass
        return global_config

    @classmethod
    def create_global_config_file(cls):
        for path in cls.GLOBAL_CONFIG_LOCATIONS:
            if path.parent.is_dir():
                print(f'could not find global config, creating {path}')
                path.write_text('{}')
                return path
        else:
            print(f'could not find a location for global config, tried: {cls.GLOBAL_CONFIG_LOCATIONS}')
            raise ValueError()

    @classmethod
    def get_config_file_list(cls):
        global_config = cls.get_global_config_filename()
        cfg_files = [global_config]
        work_tree = cls.find_work_tree_root()
        if work_tree is not None:
            # default_config_files order is crucial: work_tree cfg overrides global
            cfg_files.append(work_tree / cls.DATA_FOLDER / cls.LOCAL_CONFIG)
        return cfg_files

    @classmethod
    def get_local_config_file(cls):
        work_tree = cls.find_work_tree_root()

        if work_tree is None:
            return None

        config = work_tree / cls.DATA_FOLDER / cls.LOCAL_CONFIG
        if not config.is_file():
            return None

        return config

    @classmethod
    def find_work_tree_root(cls):
        """
        determines the work tree root by looking at the .mdt folder in cwd or parent folders

        :returns the work tree root as Path or None
        """
        cwd = Path.cwd()
        if (cwd / cls.DATA_FOLDER).is_dir():
            return cwd
        for parent in cwd.parents:
            if (parent / cls.DATA_FOLDER).is_dir():
                return parent
        else:
            return None

    @property
    def in_root(self):
        return (Path.cwd() / self.DATA_FOLDER).is_dir()

    @property
    def in_tree(self):
        return self.find_work_tree_root() is not None

    @property
    def data(self):
        cs = []

        for course_data in self.courses.values():
            course = Course(course_data)
            users = self.users
            if users is None or len(users) == 0:
                no_users_msg = """
                No users in courses found.
                If you did not sync already, metadata is probably missing.
                Use subcommand sync to retrieve metadata from selected moodle
                courses.
                """
                raise SystemExit(no_users_msg)
            else:
                    course.users = users[str(course.id)]

            assignment_list = []
            for assignment_data in self.assignments.values():
                if assignment_data[Jn.course] == course.id:
                    assignment_list.append(assignment_data)
            # course.assignments = [a for a in self.assignments.values() if a[Jn.course] == course.id]
            course.assignments = assignment_list

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
        self._write_data(self.course_data, value)
        self._course_data = value

    @property
    def grades(self):
        return self._grade_data

    @property
    def users(self):
        return self._user_data

    @users.setter
    def users(self, value):
        self._write_data(self.user_data, value)
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
        WorkTree._write_data(WorkTree.get_global_config_filename(), config_dict)

    def write_local_config(self, config_data):
        WorkTree._write_data(self.config, config_data)

    @classmethod
    def safe_file_name(cls, name):
        return re.sub(r'\W', '_', name)

    @classmethod
    def formatted_assignment_folder(cls, assignment):
        return Path(cls.safe_file_name(f'{assignment.name}--{assignment.id:d}'))

    def write_grading_and_html_file(self, assignment):
        # TODO: check if submission was after deadline and write to grading file
        a_folder = self.root / self.formatted_assignment_folder(assignment)
        grade_file = a_folder / 'gradingfile.json'
        if grade_file.is_file():
            counter = 0
            grade_file = a_folder / f'gradingfile_{counter:02d}.json'
            while grade_file.is_file():
                counter += 1
                grade_file = a_folder / f'gradingfile_{counter:02d}.json'
            print(f'grading file exists, writing to: {grade_file}')
        a_folder.mkdir(exist_ok=True)

        grade_file.write_text(assignment.grading_file_content)

        html_content = assignment.merged_html
        if html_content is not None:
            html_file = a_folder / '00_merged_submissions.html'
            html_file.write_text(html_content)

    def create_folders(self, files):
        folders = set([f.path.parent for f in files])
        for folder in folders:
            folder.mkdir(exist_ok=True, parents=True)

    def write_submission_file(self, file, content):
        with open(file.path, 'wb') as fd:
            fd.write(content)
        if file.path.suffix == '.zip':
            zipwrangler.clean_unzip_with_temp_dir(file.path, target=file.path.parent, remove_zip=True)

    def prepare_download(self, assignments):
        files = []
        for a in assignments:
            for s in a.submissions.values():
                a_folder = self.root / self.formatted_assignment_folder(a)
                print(a_folder)
                s_files = s.files
                if len(s_files) > 1:
                    s_folder = a_folder / self.safe_file_name(s.prefix)
                    for file in s_files:
                        file.path = s_folder / file.path[1:]
                        files.append(file)
                elif len(s_files) == 1:
                    file = s_files[0]
                    path = self.safe_file_name(s.prefix) + '--'
                    path += file.path[1:].replace('/', '_')
                    file.path = a_folder / path
                    files.append(file)
        self.create_folders(files)
        return files


class NotInWorkTree(Exception):
    def __init__(self):
        self.message = 'You are not in an initialized work tree. Go get one.'

    def __str__(self):
        return self.message
