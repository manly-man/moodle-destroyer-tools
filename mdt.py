#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys

import wstools
from persistence.worktree import NotInWorkTree


def exec_path_to_dict(paths):
    mdt_pattern = re.compile('mdt-\S+')
    matches = mdt_pattern.findall(" ".join(paths))  # find all like mdt-*
    cmd_names = [re.compile('^mdt-').sub('', m) for m in matches]  # strip ^mdt-
    return dict(zip(cmd_names, paths))


def external_subcmds():
    """this gets all files that are in $PATH and match mdt-*

    :returns dict with subcmd:full_path
    """

    exec_paths = os.get_exec_path()
    mdt_executable_paths = []
    for path in exec_paths:
        mdt_executable_paths += glob.glob(path + '/mdt-*')
    return exec_path_to_dict(mdt_executable_paths)


def execute_external(sub_command):
    extern = external_subcmds()
    argv = sys.argv[1:]
    argv[0] = extern[sub_command]
    subprocess.run(argv)


def internal_cmd():
    return wstools.__all__


def check_for_sub_command():
    if 1 >= len(sys.argv):
        return None
    else:
        return sys.argv[1]


def print_known_external_commands():
    print('additional external commands:')
    [print('    ' + cmd) for cmd in sorted(external_subcmds().keys())]


def main():
    sub_command = check_for_sub_command()

    if sub_command is None:
        wstools.make_config_parser().print_help()
        print_known_external_commands()
        raise SystemExit(1)
    elif sub_command in internal_cmd():
        parser = wstools.make_config_parser()
        args, unknown = parser.parse_known_args()
        if 'func' in args:
            kwargs = vars(args)
            func = kwargs.pop('func')
            func(**kwargs)
        else:
            call = getattr(wstools, sub_command)
            call()
    elif sub_command in external_subcmds():
        execute_external(sub_command)
    else:
        wstools.make_config_parser().print_help()
        print_known_external_commands()
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
        print('exiting…')
    except KeyboardInterrupt:
        print('exiting…')
        sys.exit(1)
    except SystemExit:
        raise
    except NotInWorkTree as e:
        print(e)
        raise SystemExit(1)
    except Exception as e:
        print('onoz…')
        print(e)
        raise
