import argparse
import abc
import collections
import numbers
import test.test_coroutines

def attrs(**kwargs):
    def decorate(obj):
        for k in kwargs:
            setattr(obj, k, kwargs[k])
    return decorate


class Name(collections.Callable):
    def __call__(self, test):
        pass

    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        return self.name

    def __get__(self, instance, owner):
        return self.name


class SubClassRegistry(abc.ABCMeta):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'registry'):
            cls.registry = set()
        cls.registry.add(cls)
        cls.registry -= set(bases)  # Remove base classes
        print(cls.__mro__)
        print(cls.__base__)
        print(cls.__bases__)


    # Metamethods, called on class objects:
    def __iter__(cls):
        return iter(cls.registry)

    # def __str__(cls):
    #     if cls in cls.registry:
    #         return cls.__name__
    #     return cls.__name__ + ": " + ", ".join([sc.__name__ for sc in cls])


class CommandRegistry(SubClassRegistry):
    needed_attributes = ['arguments', 'name', 'help']

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'parser'):
            cls.parser = argparse.ArgumentParser()
            cls.subparser = cls.parser.add_subparsers(help="internal sub command help")
        else:
            if 'name' not in attrs:
                raise BaseException("you must provice arguments in your class")


class Command(metaclass=CommandRegistry):

    @property
    def name(self):
        return None

    @property
    def help(self):
        return None

    @property
    def arguments(self):
        return None


class CommandDecorator:
    def __init__(self, *args):
        pass



class ArgumentContainer:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Init(Command):
    arguments = [
        ArgumentContainer('--force', help='overwrite the config', action='store_true'),
        ArgumentContainer('-c', '--courseids', dest='course_ids', nargs='+', help='moodle course id', action='append')
    ]
    name = 'init'
    @classmethod
    def run(cls):
        print('running auth')

# print(Init().arguments)