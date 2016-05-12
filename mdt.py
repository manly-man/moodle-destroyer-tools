#!/usr/bin/env python3
import glob
import os
import subprocess
import configargparse
import re
import sys

INSTALL_PATH = '/home/bone/projects/moodle-destroyer-tools-pycharm'

def find_external_subcmds():
    """this gets all files that are in $PATH and match mdt-*

    :returns dict with subcmd:full_path
    """
    # TODO has problems with sub-sub-commands, mtd-init-full will override mdt-init
    exec_paths = os.get_exec_path()
    exec_paths.append('.')   # TODO remove temp fix until mdt is in $PATH
    mdt_executable_paths = []
    for path in exec_paths:
        mdt_executable_paths += glob.glob(path + '/mdt-*')
    mdt_pattern = re.compile('mdt-\w+')
    matches = mdt_pattern.findall("".join(mdt_executable_paths))  # find all like mdt-*
    cmd_names = [re.compile('^mdt-').sub('', m) for m in matches]  # strip ^mdt-
    return dict(zip(cmd_names, mdt_executable_paths))


def find_global_config_file():
    if 'XDG_CONFIG_HOME' in os.environ:  # mebbe TODO check ~/.config/user-dirs.dirs
        if os.path.isfile(os.environ['XDG_CONFIG_HOME']+'/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
        return os.path.expanduser('~/.config/mdtconfig')
    elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
        return os.path.expanduser('~/.mdtconfig')
    else:
        return None


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
    pass


global_config = find_global_config_file()
if global_config is None:
    print('you should have rolled. try: \n  mdt init')  # TODO help sheeples.
    exit(1)

configs = [global_config]
work_tree = find_work_tree()
if work_tree is not None:
    # default_config_files order is crucial: work_tree cfg overrides global
    configs.append(work_tree+'/.mdt/config')

p = configargparse.getArgumentParser(name='mdt', default_config_files=configs)

ext_sub_commands = find_external_subcmds()
sub_command = check_for_sub_command()


if sub_command is None:
    print('you should give a subcommand, i know these:')
    [print('  ' + cmd) for cmd in ext_sub_commands.keys()]
    exit(1)
elif sub_command in ext_sub_commands:
    execute_external(ext_sub_commands[sub_command])
else:
    print('i don\'t know of this subcommand. I know those:\n')
    [print('  ' + cmd) for cmd in ext_sub_commands.keys()]
    exit(1)

#print(find_global_config_file())
#argv = sys.argv
#print(ext_sub_commands)
#print(find_work_tree())
#print(os.getcwd())
#print(p)

#p.add_argument('subcommand', help='subcommand to use', action='store', nargs='?', type=str)
#p.add_argument('--uid')
#p.add_argument('--url')
#p.add_argument('--token')
#p.add_argument('--user')


#opt = p.parse_args()


