#!/usr/bin/env python3
import glob
import os
import subprocess
import configargparse
import re
import sys
import wstools

# TODO


def external_subcmds():
    """this gets all files that are in $PATH and match mdt-*

    :returns dict with subcmd:full_path
    """

    exec_paths = os.get_exec_path()
    mdt_executable_paths = []
    for path in exec_paths:
        mdt_executable_paths += glob.glob(path + '/mdt-*')
    return exec_path_to_dict(mdt_executable_paths)


def create_global_config_file():
    file = ''
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isdir(os.environ['XDG_CONFIG_HOME']):
            file = os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isdir(os.path.expanduser('~/.config')):
        file = os.path.expanduser('~/.config/mdtconfig')
    else:
        file = os.path.expanduser('~/.mdtconfig')
    text = 'could not find global config, creating {}'
    print(text.format(file))
    open(file, 'w').close()
    return file


def find_global_config_file():
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isfile(os.environ['XDG_CONFIG_HOME']+'/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
        return os.path.expanduser('~/.config/mdtconfig')
    elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
        return os.path.expanduser('~/.mdtconfig')
    else:
        return create_global_config_file()


def check_for_sub_command():
    if 1 >= len(sys.argv):
        return None
    else:
        return sys.argv[1]


def execute_external(sub_command):
    extern = external_subcmds()
    argv = sys.argv[1:]
    argv[0] = extern[sub_command]
    subprocess.run(argv)


def internal_cmd():
    return wstools.__all__


def make_config(configs):
    config = configargparse.getArgumentParser(name='mdt', default_config_files=configs)
    config.add_argument('subcommand', help='subcommand to use', action='store', nargs='?', type=str)
    config.add_argument('--uid', is_config_file_arg=True)
    config.add_argument('--url', is_config_file_arg=True)
    config.add_argument('--token', is_config_file_arg=True)
    return config


def exec_path_to_dict(paths):
    mdt_pattern = re.compile('mdt-\S+')
    matches = mdt_pattern.findall(" ".join(paths))  # find all like mdt-*
    cmd_names = [re.compile('^mdt-').sub('', m) for m in matches]  # strip ^mdt-
    return dict(zip(cmd_names, paths))


def get_config_file_list():
    global_config = find_global_config_file()
    config_files = [global_config]
    work_tree = wstools.get_work_tree_root()
    if work_tree is not None:
        # default_config_files order is crucial: work_tree cfg overrides global
        config_files.append(work_tree+'/.mdt/config')
    return config_files


def print_known_commands():
    print('you should give a subcommand, i know these:')
    print('\n internal:')
    [print('  ' + cmd) for cmd in sorted(internal_cmd())]
    print('\n external:')
    [print('  ' + cmd) for cmd in sorted(external_subcmds().keys())]


def main():
    sub_command = check_for_sub_command()

    if sub_command is None:
        print_known_commands()
        raise SystemExit(1)
    elif sub_command == 'help':
        print_known_commands()
    elif sub_command in internal_cmd():
        make_config(get_config_file_list())
        call = getattr(wstools, sub_command)
        call()
    elif sub_command in external_subcmds():
        execute_external(sub_command)
    else:
        print_known_commands()
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
    except:
        print('onoz…')
        raise
