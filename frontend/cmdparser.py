import argparse

"""
TODO: this only works for modules imported by mdt.py
could rework this to work across modules.
"""

class ArgparseArgument:
    def add_to_parser(self, parser):
        raise NotImplementedError


class Argument(ArgparseArgument):
    def add_to_parser(self, parser):
        parser.add_argument(*self.args, **self.kwargs)

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ArgumentGroup(ArgparseArgument):
    def add_to_parser(self, parser):
        group = parser.add_argument_group(self.name, self.help_text)
        for arg in self.arg_list:
            arg.add_to_parser(group)

    def __init__(self, name, help_text, arg_list):
        self.name = name
        self.help_text = help_text
        self.arg_list = arg_list


class ParserManager:
    known_commands = []
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="internal sub command help")

    @classmethod
    def register(cls, name, help_text):
        if name not in cls.known_commands:
            cls.known_commands.append(name)
        return cls.subparsers.add_parser(name, help=help_text)

    @classmethod
    def command(cls, help_text, *arguments):
        def register_function(function):
            sub = cls.register(function.__name__, help_text)
            for arg in arguments:
                arg.add_to_parser(sub)
            sub.set_defaults(func=function)

        return register_function

