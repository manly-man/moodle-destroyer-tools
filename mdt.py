#!/usr/bin/env python3
import glob
import os
import subprocess
import configargparse
import re
import sys
import wstools


def find_external_subcmds():
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


def find_work_tree():
    """ determines the work tree root by looking at the .mdt folder in cwd or parent folders
    :returns the work tree root as String or None
    """
    cwd = os.getcwd()
    repo = None
    while not os.path.isdir('.mdt'):
        if '/' == os.getcwd():
            break
        os.chdir(os.pardir)
    if os.path.isdir('.mdt'):
        repo = os.getcwd()
        wstools.WORKING_DIRECTORY = repo + '/'
    os.chdir(cwd)
    return repo


def check_for_sub_command():
    if 1 >= len(sys.argv):
        return None
    else:
        return sys.argv[1]


def execute_external(sub_command):
    argv = sys.argv[1:]
    argv[0] = sub_command
    print('executing '+repr(argv))
    subprocess.run(argv)


def find_internal_cmd():
    return wstools.__all__


def make_config(configs):
    config = configargparse.getArgumentParser(name='mdt', default_config_files=configs)
    config.add_argument('subcommand', help='subcommand to use', action='store', nargs='?', type=str)
    config.add_argument('--uid', is_config_file_arg=True)
    config.add_argument('--url', is_config_file_arg=True)
    config.add_argument('--token', is_config_file_arg=True)
    return config


def exec_path_to_dict(paths):
    mdt_pattern = re.compile('mdt-\S+')  # TODO add mdt-prefix on packaging
    matches = mdt_pattern.findall(" ".join(paths))  # find all like mdt-*
    cmd_names = [re.compile('^mdt-').sub('', m) for m in matches]  # strip ^mdt-
    return dict(zip(cmd_names, paths))


def get_config_file_list():
    global_config = find_global_config_file()
    config_files = [global_config]
    work_tree = find_work_tree()
    if work_tree is not None:
        # default_config_files order is crucial: work_tree cfg overrides global
        config_files.append(work_tree+'/.mdt/config')
    return config_files


def main():
    config_files = get_config_file_list()
    config = make_config(config_files)

    ext_sub_commands = find_external_subcmds()
    int_sub_commands = find_internal_cmd()
    sub_command = check_for_sub_command()

    # commands = {**ext_sub_commands, **int_sub_commands}  # merge dicts, PEP-448 Additional Unpacking Generalizations

    if sub_command is None:
        print('you should give a subcommand, i know these:')
        [print('  ' + cmd) for cmd in sorted(int_sub_commands)]
        [print('  ' + cmd) for cmd in sorted(ext_sub_commands.keys())]
        exit(1)
    elif sub_command == 'help':
        config.print_help()
    elif sub_command in int_sub_commands:
        call = getattr(wstools, sub_command)
        call()
    elif sub_command in ext_sub_commands:
        execute_external(ext_sub_commands[sub_command])
    else:
        print('i don\'t know of this subcommand. I know those:\n')
        [print('  ' + cmd) for cmd in ext_sub_commands.keys()]
        exit(1)


if __name__ == '__main__':
    main()
