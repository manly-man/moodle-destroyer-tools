#!/usr/bin/env python3
import glob
import os
import subprocess
import configargparse
import re


def find_external_subcmds():
    """this gets all files that are in $PATH and match mdt-*

    :returns dict with subcmd:full_path
    """
    exec_paths = os.get_exec_path()
    exec_paths += '.'  # TODO remove temp fix until mdt is in $PATH
    mdt_executable_paths = []
    for path in exec_paths:
        mdt_executable_paths += glob.glob(path + '/mdt-*')
    mdt_pattern = re.compile('mdt-\w+')
    matches = mdt_pattern.findall("".join(mdt_executable_paths))  # find all like mdt-*
    cmd_names = [re.compile('^mdt-').sub('', m) for m in matches]  # strip ^mdt-
    subcmds = dict(zip(cmd_names, mdt_executable_paths))
    return subcmds


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

global_config = find_global_config_file()
if global_config is None:
    print('you should have rolled. try: \n  mdt init')  # TODO help sheeples.
    exit(-1)

work_tree = find_work_tree()
p=[]
if work_tree is not None:
    print()
    p = configargparse.getArgumentParser(name='mdt', default_config_files=[global_config, work_tree+'/.mdt/config'])
else:
    p = configargparse.getArgumentParser(name='mdt', default_config_files=[global_config])

p.add_argument('--uid')
p.add_argument('--url')
p.add_argument('--token')
p.add_argument('--user')


opt = p.parse_args()
print(find_global_config_file())
print(find_external_subcmds())
print(find_work_tree())
print(os.getcwd())
print(p)
print(opt)
