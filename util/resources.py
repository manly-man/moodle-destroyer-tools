import math
import json
import os
from datetime import datetime
from moodle.fieldnames import JsonFieldNames as Jn


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
            json.dump(meta, file, indent=2, ensure_ascii=False, sort_keys=True)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError as ke:
            return default

    def copy(self):
        return {key: self.__getitem__(key) for key in self.keys()}

    def keys(self):
        return [int(filename) for filename in os.listdir(self._folder) if filename != self._meta_name]

    def items(self):
        return [(key, self.__getitem__(key)) for key in self.keys()]

    def pop(self, key, default=None):
        data = self.__getitem__(key)
        self.__delitem__(key)
        return data

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    # noinspection PyMethodOverriding
    def values(self):
        return [self.__getitem__(key) for key in self.keys()]

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
        if key in self._cache:
            return self._cache[key]

        filename = self._folder + str(key)
        try:
            with open(filename, 'r') as file:
                self._cache[key] = json.load(file)
                return self._cache[key]
        except IOError:
            raise KeyError(key)

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


class SubmissionMetaDataFolder(MetaDataFolder):

    def __init__(self, folder, **kwargs):
        self.last_sync = 0
        super().__init__(folder, **kwargs)

    def _update_submissions(self, assignment_id, submissions):
        local_submissions = {sub[Jn.id]: sub for sub in self[assignment_id]}
        for submission in submissions:
            local_submissions[submission[Jn.id]] = submission
        self[assignment_id] = list(local_submissions.values())

    def update(self, other=None, **kwargs):
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for assignment in other[Jn.assignments]:
            assignment_id = int(assignment[Jn.assignment_id])
            submissions = assignment[Jn.submissions]
            if assignment_id in self.keys() and len(submissions) > 0:
                self._update_submissions(assignment_id, submissions)
                result['updated'] += 1
            elif len(submissions) > 0:
                result['new'] += 1
                self[assignment_id] = submissions
            else:
                result['unchanged'] += 1
        self.last_sync = math.floor(datetime.now().timestamp())
        self._write_meta()
        return result


class GradeMetaDataFolder(MetaDataFolder):

    def __init__(self, folder, **kwargs):
        self.last_sync = 0
        super().__init__(folder, **kwargs)

    def _update_grades(self, assignment_id, grades):
        local_grades = {grade[Jn.id]: grade for grade in self[assignment_id]}
        for grade in grades:
            local_grades[grade[Jn.id]] = grade
        self[assignment_id] = list(local_grades.values())

    def update(self, other=None, **kwargs):
        # g_config_file = self.grade_meta + str(assignment[Jn.assignment_id])
        # self._write_meta(g_config_file, assignment)
        result = dict.fromkeys(['new', 'updated', 'unchanged'], 0)
        for assignment in other[Jn.assignments]:
            assignment_id = int(assignment[Jn.assignment_id])
            grades = assignment[Jn.grades]
            if assignment_id in self.keys() and len(grades) > 0:
                self._update_grades(assignment_id, grades)
                result['updated'] += 1
            elif len(grades) > 0:
                self[assignment_id] = grades
                result['new'] += 1
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
