import json
import os
import moodle.models as models
from collections import Mapping
from abc import abstractmethod
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


class CachedFile(Mapping):  # TODO: WIP
    def __init__(self, file_path):
        self._cache = None
        self.path = file_path

    def __iter__(self):
        pass

    def __getitem__(self, key):
        if self._cache is None:
            self._cache = self._read_file(self.path)
        return self._cache[key]

    def __len__(self):
        pass

    @abstractmethod
    def _read_file(self, file_path):
        pass


class JsonDataFolder(CachedMapping):
    def __init__(self, folder):
        super().__init__()
        self._folder = folder + '/'

    def _read_data(self, key):  # CachedMapping
        filename = self._folder + str(key)
        try:
            return _read_json(filename)
        except FileNotFoundError:
            raise KeyError(key)

    def _write_data(self, key, value):  # CachedMutableMapping
        filename = self._folder + str(key)
        _dump_json(filename, value)

    def _setitem(self, key, value):
        self._cache[key] = value
        self._write_data(key, value)

    def __iter__(self):
        for filename in os.listdir(self._folder):
            yield int(filename)

    def __len__(self):
        return len(os.listdir(self._folder))


class JsonMetaDataFolder(JsonDataFolder):
    _meta_file_suffix = '_meta'

    def __init__(self, folder):
        super().__init__(folder)
        self._meta_file_path = folder + self._meta_file_suffix
        self._read_meta()

    def _read_meta(self):
        filename = self._meta_file_path
        try:
            meta = _read_json(filename)
        except FileNotFoundError:
            return
        for k, v in meta.items():
            setattr(self, k, v)

    def _write_meta(self):
        meta = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        _dump_json(self._meta_file_path, meta)

    def __iter__(self):
        names = set(os.listdir(self._folder))
        try:
            names.remove(self._meta_file_suffix)
        except KeyError:
            pass
        for name in names:
            yield int(name)

    def __len__(self):
        names = set(os.listdir(self._folder))
        try:
            names.remove(self._meta_file_suffix)
        except KeyError:
            pass
        return len(names)


class AssignmentFolder(JsonDataFolder):
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
