import glob
import json
import math
import os
import re
import configparser
import collections
from datetime import datetime
from moodle.fieldnames import JsonFieldNames as Jn
from moodle.models import Course, Assignment, Submission


class WorkTree:
    def __enter__(self):
        print('enter')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exit')

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


class MetaDataFolder(dict):
    def __init__(self, folder, **kwargs):
        super().__init__(**kwargs)
        self._folder = folder + '/'
        self._meta_name = 'meta'
        self._meta_filename = self._folder + self._meta_name
        self._cache = {}
        self._read_meta()

    def _read_meta(self):
        filename = self._meta_filename
        try:
            with open(filename, 'r') as file:
                meta = json.load(file)
                for k, v in meta.items():
                    setattr(self, k, v)
        except IOError:
            pass

    def _write_meta(self):
        filename = self._meta_filename
        meta = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        with open(filename, 'w') as file:
            json.dump(meta, file)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError as ke:
            return default

    def copy(self):
        return {key: self[key] for key in self.keys()}

    def keys(self):
        return [int(filename) for filename in os.listdir(self._folder) if filename != self._meta_name]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def pop(self, key, default=None):
        data = self[key]
        del self[key]
        return data

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    # noinspection PyMethodOverriding
    def values(self):
        return [self[key] for key in self.keys()]

    def update(self, other=None, **kwargs):
        raise NotImplementedError('update')

    def clear(self):
        for key in self.keys():
            os.remove(self._folder + str(key))

    def popitem(self):
        key = self.keys()[0]
        return self.pop(key)

    def __len__(self):
        return len(self.keys())

    def __delitem__(self, key):
        try:
            os.remove(self._folder + key)
        except FileNotFoundError:
            raise KeyError(key)

    def __repr__(self, *args, **kwargs):
        return self.__str__(*args, **kwargs)

    def __getitem__(self, key):
        try:
            return self._cache[key]
        except KeyError:
            filename = self._folder + str(key)
            try:
                with open(filename, 'r') as file:
                    self._cache[key] = json.load(file)
                    return self._cache[key]
            except IOError:
                raise KeyError('{} no data: {!s}'.format(self.__name__, key))

    def __setitem__(self, key, value):
        self._cache[key] = value
        with open(self._folder + str(key), 'w') as file:
            json.dump(value, file, indent=2, ensure_ascii=False, sort_keys=True)

    def __contains__(self, *args, **kwargs):
        return os.path.isfile(self._folder + args[0])

    def __str__(self, *args, **kwargs):
        return '<MetaDataFolder: {}>'.format(self._folder)

#    def __setattr__(self, key, value):
#        super().__setattr__(key, value)
#        print('setattr')
#        if not key.startswith('_'):
#            self._write_meta()


class AssignmentMetaDataFolder(MetaDataFolder):
    def update(self, other=None, **kwargs):
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for course in other[Jn.courses]:
            for assignment in course[Jn.assignments]:
                key = int(assignment['id'])
                value = assignment
                try:
                    local_data = self[key]
                    if local_data[Jn.time_modified] < assignment[Jn.time_modified]:
                        self[key] = value
                        result['updated'] += 1
                    else:
                        result['unchanged'] += 1
                except KeyError:
                    self[key] = value
                    result['new'] += 1
        return result

    def __getitem__(self, key):
        return Assignment(super().__getitem__(key))


class SubmissionMetaDataFolder(MetaDataFolder):

    def __init__(self, folder, **kwargs):
        self.last_sync = 0
        super().__init__(folder, **kwargs)

    def update(self, other=None, **kwargs):
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for assignment in other[Jn.assignments]:
            key = int(assignment[Jn.assignment_id])
            value = assignment[Jn.submissions]
            if key in self.keys():
                result['updated'] += 1
            else:
                result['new'] += 1
            if len(value) > 0:
                self[key] = value
            else:
                result['unchanged'] += 1
        self.last_sync = math.floor(datetime.now().timestamp())
        self._write_meta()
        return result

    def __getitem__(self, key):
        return SubmissionShelf(self._folder + str(key))


class GradeMetaDataFolder(MetaDataFolder):
    def __init__(self, folder, **kwargs):
        self.last_sync = 0
        super().__init__(folder, **kwargs)

    def update(self, other=None, **kwargs):
        # g_config_file = self.grade_meta + str(assignment[Jn.assignment_id])
        # self._write_meta(g_config_file, assignment)
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for assignment in other[Jn.assignments]:
            key = int(assignment[Jn.assignment_id])
            value = assignment[Jn.grades]
            if key in self.keys():
                result['updated'] += 1
            else:
                result['new'] += 1
            if len(value) > 0:
                self.__setitem__(key, value)
            else:
                result['unchanged'] += 1
        self.last_sync = math.floor(datetime.now().timestamp())
        self._write_meta()
        return result


class MetaDataFile(dict):
    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self._file = file
        self._meta_filename = file + '_meta'
        self._data = {}
        self._read_meta()

    @property
    def _cache(self):
        if len(self._data) < 1:
            with open(self._file) as file:
                self._data = json.load(file)
        return self._data

    def _read_meta(self):
        filename = self._meta_filename
        try:
            with open(filename, 'r') as file:
                meta = json.load(file)
                for k, v in meta.items():
                    setattr(self, k, v)
        except IOError:
            pass

    def _write_meta(self):
        filename = self._meta_filename
        meta = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        with open(filename, 'w') as file:
            json.dump(meta, file)

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def copy(self):
        return self._cache.copy()

    def keys(self):
        return self._cache.keys()

    def items(self):
        return self._cache.items()

    def pop(self, key, default=None):
        return self._cache.pop(key, default)

    def setdefault(self, key, default=None):
        return self._cache.setdefault(key, default)

    # noinspection PyMethodOverriding
    def values(self):
        return self._cache.values()

    def update(self, other=None, **kwargs):
        raise NotImplementedError('update')

    def clear(self):
        self._cache.clear()

    def popitem(self):
        return self._cache.popitem()

    def __len__(self):
        return len(self._cache)

    def __delitem__(self, key):
        del self._cache[key]

    def __repr__(self, *args, **kwargs):
        return str(self)

    def __getitem__(self, key):
        return self._cache[key]

    def __setitem__(self, key, value):
        self._cache[key] = value

    def __contains__(self, *args, **kwargs):
        return self._cache.__contains__(*args, **kwargs)

    def __str__(self, *args, **kwargs):
        return '<MetaData: {}>'.format(self._file)


class JsonShelf(collections.MutableMapping):
    """Base class for shelf implementations.

    This is initialized with a dictionary-like object.
    """

    def __init__(self, filename, read_only=True):
        self._filename = filename
        self._meta_filename = filename + '_meta'
        self._data = None
        self._read_only = read_only
        self._changed = False

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __delitem__(self, key):
        del self._data[key]
        self._changed = True

    def __setitem__(self, key, value):
        self._changed = True
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __enter__(self):
        print('enter {}'.format(self._filename))
        try:
            with open(self._filename, 'r') as file:
                self._data = json.load(file)
        except IOError:
            print('could not read {}')
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exit {}'.format(self._filename))
        self.close()

    def close(self):
        if self._data is None:
            return
        if not self._read_only and self._changed:
            try:
                with open(self._filename, 'w') as file:
                    json.dump(self._data, file)
            except IOError:
                print('could not write {}'.format(self._filename))
                pass


class JsonShelfSet(collections.MutableSet):
    def __init__(self, filename, read_only=True):
        self._filename = filename
        self._meta_filename = filename + '_meta'
        print(filename)
        self._data = json.load(open(filename, 'r'))
        self._read_only = read_only
        self._changed = False

    def __contains__(self, x):
        pass

    def discard(self, value):
        pass

    def add(self, value):
        pass

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __enter__(self):
        print('enter {}'.format(self._filename))
        try:
            with open(self._filename, 'r') as file:
                self._data = json.load(file)
        except IOError:
            print('could not read {}')
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exit {}'.format(self._filename))
        self.close()

    def close(self):
        if self._data is None:
            return
        if not self._read_only and self._changed:
            try:
                with open(self._filename, 'w') as file:
                    json.dump(self._data, file)
            except IOError:
                print('could not write {}'.format(self._filename))
                pass


class SubmissionShelf(JsonShelfSet):
    def __iter__(self):
        for subdata in self._data:
            yield Submission(subdata)

    def __getitem__(self, key):
        return Submission(self._data[key])


class JsonSet(collections.Set):
    def __init__(self, filename):
        self._filename = filename
        self._meta_filename = filename + '_meta'
        self._data = None

    @property
    def _cache(self):
        raise NotImplementedError('JsonSet')

    def __contains__(self, x):
        raise NotImplementedError('JsonSet')

    def __len__(self):
        return len(self._cache)

    def __iter__(self):
        raise NotImplementedError('JsonSet')


class SynchronizedJsonSet(JsonSet, collections.MutableSet):
    def discard(self, value):
        raise NotImplementedError('SynchronizedJsonSet')

    def add(self, value):
        raise NotImplementedError('SynchronizedJsonSet')

    def __iter__(self):
        raise NotImplementedError('SynchronizedJsonSet')

    @property
    def _cache(self):
        raise NotImplementedError('SynchronizedJsonSet')

    def __contains__(self, x):
        raise NotImplementedError('SynchronizedJsonSet')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exit')
        if self._data is None:
            print('data was none')
            return
        try:
            with open(self._filename, 'w') as file:
                print('writing {:d} items'.format(len(self._data)))
                json.dump(list(self._data.values()), file)
        except IOError:
            print('could not write changes to {}'.format(self._filename))


class SubmissionSet(JsonSet):
    @property
    def _cache(self):
        if self._data is None:
            self._data = {}
            with open(self._filename, 'r') as file:
                data_list = json.load(file)
            for sub in data_list:
                self._data[sub[Jn.id]] = sub
        return self._data

    def __iter__(self):
        for data in self._cache.values():
            yield Submission(data)

    def __contains__(self, x):
        if not isinstance(x, Submission):
            return False
        return x.id in self._cache


class MutableSubmissionSet(SubmissionSet, SynchronizedJsonSet):
    def __enter__(self):
        print('enter')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exit')
        if self._data is None:
            print('data was none')
            return
        try:
            with open(self._filename, 'w') as file:
                print('writing {:d} items'.format(len(self._data)))
                json.dump(list(self._data.values()), file)
        except IOError:
            print('could not write changes to {}'.format(self._filename))

    def discard(self, submission):
        if not isinstance(submission, Submission):
            raise Exception('cannot discard type {} from SubmissionSet'.format(type(submission)))
        del self._cache[submission.id]

    def add(self, submission):
        if not isinstance(submission, Submission):
            raise Exception('cannot add type {} to SubmissionSet'.format(type(submission)))
        self._cache[submission.id] = submission.raw


class ShelfSet(collections.MutableSet):
    def __init__(self, filename, read_only=True):
        self._filename = filename
        self._meta_filename = filename + '_meta'
        self._data = None
        self._submissions = []
        self._read_only = read_only
        self._changed = False

    @property
    def _cache(self):
        if self._data is None:
            with open(self._filename, 'r') as file:
                self._data = json.load(file)
            for sub in self._data:
                self._submissions.append(Submission(sub))
        return self._submissions

    def __contains__(self, x):
        for submission in iter(self):
            if submission.id == x.id:
                return True
        return False

    def __len__(self):
        return len(self._cache)

    def __iter__(self):
        for s in self._cache:
            yield s

    def discard(self, value):
        pass

    def add(self, value):
        if value in self:
            print('discarding other')

        pass