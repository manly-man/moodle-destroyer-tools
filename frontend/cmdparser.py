import argparse


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
    # TODO: rework ParserManager to scan submodules for commands, move to commands module.
    def __init__(self, name, help_text):
        self.name = name
        self.help = help_text
        self.known_commands = []
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(help=help_text)

    def register(self, name, help_text):
        if name not in self.known_commands:
            self.known_commands.append(name)
        return self.subparsers.add_parser(name, help=help_text)

    def command(self, help_text, *arguments):
        def register_function(decorated_fn):
            sub = self.register(decorated_fn.__name__, help_text)
            for arg in arguments:
                arg.add_to_parser(sub)
            sub.set_defaults(func=decorated_fn)

        return register_function
