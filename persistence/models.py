import json
import os

from pathlib import Path
from collections import Mapping
from abc import abstractmethod

import moodle.models as models
# TODO, mebbe add locks for async usage.


def _read_json(filename):
    with open(filename) as file:
        return json.load(file)


def _dump_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)


class CachedMapping(Mapping):

    def __init__(self):
        self._cache = {}

    def __getitem__(self, key):
        # return value if in cache
        try:
            return self._cache[key]
        except KeyError:
            pass

        # try reading from resource.
        self._cache[key] = self._read_data(key)
        return self._cache[key]

    @abstractmethod
    def _read_data(self, key):
        pass


class CachedFileMapping(Mapping):  # TODO: WIP
    def __init__(self, file_path):
        self._cache = None
        self.path = file_path

    def __iter__(self):
        if self._cache is None:
            self._cache = self._read_file(self.path)
        return iter(self._cache)

    def __getitem__(self, key):
        if self._cache is None:
            self._cache = self._read_file(self.path)
        return self._cache[key]

    def __len__(self):
        if self._cache is None:
            self._cache = self._read_file(self.path)
        return len(self._cache)

    @abstractmethod
    def _read_file(self, file_path):
        return {}


class CachedJsonFile(CachedFileMapping):
    def _read_file(self, file_path):
        return _read_json(file_path)


class JsonDataFolder(CachedMapping):
    def __init__(self, root_folder: Path, init=False):
        super().__init__()
        self._folder = root_folder / self.folder_name
        if init:
            self._folder.mkdir(exist_ok=True)

    def _read_data(self, key):  # CachedMapping
        filename = self._folder / str(key)
        try:
            return _read_json(filename)
        except FileNotFoundError:
            raise KeyError(key)

    def _write_data(self, key, value):  # CachedMutableMapping
        filename = self._folder / str(key)
        _dump_json(filename, value)

    def _setitem(self, key, value):
        self._cache[key] = value
        self._write_data(key, value)

    def __iter__(self):
        for file in self._folder.iterdir():
            yield int(file.name)

    def __len__(self):
        return len(list(self.__iter__()))

    @property
    @abstractmethod
    def folder_name(self):
        return 'folder_name'


class JsonMetaDataFolder(JsonDataFolder):
    _meta_file_suffix = '_meta'

    def __init__(self, root_folder: Path, init=False):
        super().__init__(root_folder, init)
        self._meta_file_path = root_folder / (self.folder_name + self._meta_file_suffix)
        self._read_meta()

    def _read_meta(self):
        filename = self._meta_file_path
        try:
            meta = _read_json(filename)
            for k, v in meta.items():
                setattr(self, k, v)
        except FileNotFoundError:
            pass

    def _write_meta(self):
        meta = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        _dump_json(self._meta_file_path, meta)

    def __iter__(self):
        for file in self._folder.iterdir():
            yield int(file.name)

    def __len__(self):
        return len(set(self._folder.iterdir()))

    @property
    @abstractmethod
    def folder_name(self):
        return 'folder_name'


class AssignmentFolder(JsonDataFolder):
    @property
    def folder_name(self):
        return 'assignments'

    def update(self, json_data):
        response = models.CourseAssignmentResponse(json_data)
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for course in response.courses:
            for assignment in course.assignments:
                key = assignment.id
                value = assignment
                try:
                    local_data = models.MoodleAssignment(self[key])
                    if local_data.time_modified < assignment.time_modified:
                        self._setitem(assignment.id, assignment.raw)
                        result['updated'] += 1
                    else:
                        result['unchanged'] += 1
                except KeyError:
                    self._setitem(assignment.id, assignment.raw)
                    result['new'] += 1
        return result


class SubmissionFolder(JsonMetaDataFolder):
    @property
    def folder_name(self):
        return 'submissions'

    last_sync = 0

    def _update_submissions(self, assignment_id, submissions):
        local_list = models.MoodleSubmissionList(self[assignment_id])
        local_submissions = {sub.id: sub for sub in local_list}
        for submission in submissions:
            local_submissions[submission.id] = submission
        raw = [sub.raw for sub in local_submissions.values()]
        self._setitem(assignment_id, raw)

    def update(self, json_data, time_of_sync):
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        response = models.AssignmentSubmissionResponse(json_data)
        for assignment in response.assignments:
            if assignment.id in self and len(assignment.submissions) > 0:
                self._update_submissions(assignment.id, assignment.submissions)
                result['updated'] += 1
            elif len(assignment.submissions) > 0:
                result['new'] += 1
                self._setitem(assignment.id, assignment.submissions.raw)
            else:
                result['unchanged'] += 1
        self.last_sync = time_of_sync
        self._write_meta()
        return result


class GradeFolder(JsonMetaDataFolder):
    @property
    def folder_name(self):
        return 'grades'

    last_sync = 0

    def _update_grades(self, assignment_id, grades):
        local_list = models.MoodleGradeList(self[assignment_id])
        local_grades = {grd.id: grd for grd in local_list}
        # local_grades = {grade[Jn.id]: grade for grade in self[assignment_id]}
        for grade in grades:
            local_grades[grade.id] = grade
        raw = [grd.raw for grd in local_grades.values()]
        self._setitem(assignment_id, raw)

    def update(self, json_data, time_of_sync):
        # g_config_file = self.grade_meta + str(assignment[Jn.assignment_id])
        # self._write_meta(g_config_file, assignment)
        response = models.AssignmentGradeResponse(json_data)
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for assignment in response.assignments:
            if assignment.id in self and len(assignment.grades) > 0:
                self._update_grades(assignment.id, assignment.grades)
                result['updated'] += 1
            elif len(assignment.grades) > 0:
                self._setitem(assignment.id, assignment.grades.raw)
                result['new'] += 1
            else:
                result['unchanged'] += 1
        self.last_sync = time_of_sync
        self._write_meta()
        return result


class Config(models.JsonDictWrapper):
    error_msg = """
    '{}' couldn't be found in your config file.
    Maybe it's corrupted.
    Either check your config file
    or delete the entire file and create a new one.
    """

    @property
    def service(self): return self['service']

    @property
    def token(self):
        try:
            return self['token']
        except KeyError:
            raise SystemExit(self.error_msg.format('token'))

    @property
    def user_id(self):
        try:
            return self['user_id']
        except KeyError:
            raise SystemExit(self.error_msg.format('user_id'))

    @property
    def url(self):
        try:
            return self['url']
        except KeyError:
            raise SystemExit(self.error_msg.format('url'))

    @property
    def user_name(self): return self['user_name']

    def add_overrides(self, overrides):
        self._data.update(overrides)

    def __str__(self):
        return str(self._data)


class MdtConfig:
    _file_name = 'config'

    @classmethod
    def global_config_locations(cls):
        locations = []
        try:
            locations.append(os.environ['XDG_CONFIG_HOME'] + '/mdtconfig')
        except KeyError:
            pass
        locations.append(os.path.expanduser('~/.config/mdtconfig'))
        locations.append(os.path.expanduser('~/.mdtconfig'))
        return locations

    def __init__(self, meta_root=None, prefer_local=False, init=False):
        self.prefer_local = prefer_local
        self.global_cfg = self.read_global(init)
        if meta_root:
            self.local_cfg = {}

    def read_global(self, init):
        locations = self.global_config_locations()
        for file_name in locations:
            try:
                with open(file_name) as file:
                    return Config(json.load(file))
            except FileNotFoundError:
                pass
        if not self.prefer_local or init:
            text = 'could not find global config, creating {}'
            print(text.format(locations[0]))
            with open(locations[0], 'w') as cfg_file:
                cfg_file.write('{}')
            return {}
        return None

