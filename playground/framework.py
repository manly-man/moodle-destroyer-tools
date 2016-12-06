from abc import ABCMeta, abstractmethod
from collections import Mapping, Sequence, Sized
from moodle.parsers import strip_mlang

class JsonWrapper(Sized):
    def __len__(self):
        return len(self._data)

    def __init__(self, json):
        self._data = json

    @property
    def raw(self): return self._data


class JsonListWrapper(JsonWrapper, Sequence):
    def __getitem__(self, index):
        return self._data[index]

    def __init__(self, json_list):
        if type(json_list) is not list:
            raise TypeError('received type {}, expected list'.format(type(json_list)))
        super().__init__(json_list)

    def __iter__(self):
        raise NotImplementedError('__iter__')

    def get(self, index):
        try:
            return self._data[index]
        except Exception as e:
            print(index)
            raise e


class JsonDictWrapper(JsonWrapper, Mapping):
    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __init__(self, json_dict):
        super().__init__(json_dict)
        if type(self._data) is not dict:
            raise TypeError('received type {}, expected dict'.format(type(json_dict)))

    __marker = object()

    def get(self, key, default=__marker):
        try:
            return self._data[key]
        except KeyError:
            if default is self.__marker:
                raise
            else:
                return default



class ResponseWrapper(metaclass=ABCMeta):
    @abstractmethod
    def _check_for_errors(self): raise NotImplementedError('_check_for_errors')

    @classmethod
    def __subclasshook__(cls, C):
        if cls is JsonResponseWrapper:
            if any('_check_for_errors' in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented

class JsonResponseWrapper(JsonWrapper, ResponseWrapper):
    def __init__(self, response):
        super().__init__(response.json())
        self._response = response
        self._check_for_errors()

    @property
    def response(self): return self._response

    @property
    def mlang_stripped_text(self): return strip_mlang(self.response.text)

    @property
    def mlang_stripped_json(self): return json.loads(self.mlang_stripped_text)

    @abstractmethod
    def _check_for_errors(self): raise NotImplementedError('check_for_errors')


class JsonDictResponseWrapper(JsonResponseWrapper, JsonDictWrapper):
    @abstractmethod
    def _check_for_errors(self):
        pass

    def __init__(self, response):
        super().__init__(response)
        if type(self._data) is not dict:
            raise TypeError('received type {}, expected dict'.format(type(response)))


class JsonListResponseWrapper(JsonResponseWrapper, JsonListWrapper):
    @abstractmethod
    def __iter__(self):
        pass

    def __init__(self, response):
        super().__init__(response)
        if type(self._data) is not list:
            raise TypeError('received type {}, expected list'.format(type(response)))

    def get(self, index):
        try:
            return self._data[index]
        except Exception as e:
            print(index)
            raise e


def check_disjoint(names):
    storage = set()
    for name in names:
        if name in storage:
            raise NameError('Field %r occurs twice!' % name)
        else:
            storage.add(name)


def get_slots(bases):
    return sum((getattr(b, 'all_slots', ()) for b in bases), ())


class odict(Mapping):
    """A simple implementation of ordered dicts without __delitem__ functionality"""

    def __init__(self, alist=None):
        self._inner = {}  # inner dictionary
        self._keys = []  # the dictionary keys in order
        if alist:
            for k, v in alist:
                self[k] = v

    def __getitem__(self, key):
        return self._inner[key]

    def __setitem__(self, key, value):
        self._inner[key] = value
        self._keys.append(key)

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        return '{%s}' % list(self.items())


class MetaRecord(type):
    _repository = {}  # repository of classes already instantiated

    @classmethod
    def __prepare__(mcs, name, bases):
        return odict()

    def __new__(mcs, name, bases, odic):
        entered_slots = tuple((n, v) for n, v in odic.items()
                              if n.endswith('_type'))
        all_slots = get_slots(bases) + entered_slots
        check_disjoint(n for (n, f) in all_slots)
        # check the field names are disjoint
        odic['all_slots'] = all_slots
        odic['all_names'] = tuple(n[:-5] for n, f in all_slots)
        odic['all_fields'] = fields = tuple(f for n, f in all_slots)
        cls = super().__new__(mcs, name, bases, dict(odic))
        mcs._repository[fields] = cls
        for i, (n, v) in enumerate(all_slots):
            setattr(cls, n[:-5], property(lambda self, i=i: self[i]))
        return cls

    def __eq__(cls, other):
        return cls.all_fields == other.all_fields

    def __ne__(cls, other):
        # must be defined explicitly; overriding __eq__ only is not enough
        return cls.all_fields != other.all_fields

    # def __call__(cls, *values):
    #     expected = len(cls.all_slots)
    #     passed = len(values)
    #     if passed != expected:
    #         raise TypeError('You passed %d parameters, expected %d' %
    #                         (passed, expected))
    #     vals = [f(v) for (n, f), v in zip(cls.all_slots, values)]
    #     return super().__call__(vals)

    def __add__(cls, other):
        name = '%s+%s' % (cls.__name__, other.__name__)
        fields = tuple(f for n, f in get_slots((cls, other)))
        try:  # retrieve from the repository an already generated class
            return cls._repository[fields]
        except KeyError:
            return type(cls)(name, (cls, other), {})

    def __repr__(cls):
        slots = ['%s:%s' % (n[:-5], f.__name__)
                 for (n, f) in cls.all_slots]
        return '<%s %s %s>' % ('class', cls.__name__,
                               ', '.join(slots))


class Record(tuple, metaclass=MetaRecord):
    """Base record class, also working as identity element"""

    def __add__(self, other):
        cls = type(self) + type(other)
        return cls(*super().__add__(other))

    def __repr__(self):
        slots = ['%s=%s' % (n, v) for n, v in zip(self.all_names, self)]
        return '<%s %s>' % (self.__class__.__name__, ', '.join(slots))


def varchar(n):
    """varchar(n) converts an object into a string with less than n
    characters or raises a TypeError"""
    def check(x):
        s = str(x)
        if len(s) > n:
              raise TypeError('Entered a string longer than %d chars' % n)
        return s
    check.__name__ = 'varchar(%d)' % n
    return check


def score(x):
   "Takes a string and converts it into an integer in the range 1-5"
   if set(x) != {'*'} or len(x) > 5:
       raise TypeError('%r is not a valid score!' % x)
   return len(x)



class Book(Record):
    title_type = varchar(128)
    author_type = varchar(64)


class Score(Record):
    score_type = score


book = Book()


class TypedField:
    def __init__(self, name, field_type):
        self.name = name
        self.field_type = field_type

    def is_valid(self, value): return isinstance(value, self.field_type)


class Field:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Field: {}>'.format(self.name)

class OptField:
    def __init__(self, name):
        self.name = name


class FieldRegistryMeta(type):
    def __init__(cls, name, bases=None, ns=None):
        super().__init__(name, bases, ns)
        cls._fields = {}
        cls._opt_fields = {}

        for key, value in ns.items():
            if isinstance(value, Field):
                print('registered {}: {}'.format(key, value.name))
                cls._fields[key] = value


class JsonFieldRegistry(metaclass=FieldRegistryMeta):
    def __init__(self, data):
        self._data = data

    def __getattribute__(self, name):
        try:
            field = object.__getattribute__(self, '_fields')[name]
            return self[field.name]
        except KeyError:
            return object.__getattribute__(self, name)


class MoodleCourseFields(JsonFieldRegistry):
    id = Field('id')
    short_name = Field('shortname')
    full_name = Field('fullname')
    enrolled_user_count = Field('enrolledusercount')
    id_number = Field('idnumber')
    visible = Field('visible')

    def __getitem__(self, index):
        return self._data[index]
