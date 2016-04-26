#!/usr/bin/env python3
import glob
import os
import subprocess
import configargparse


def find_external_subcmds():
    exec_paths = os.get_exec_path()
    exec_paths += '.'  # TODO remove temp fix until mdt is in $PATH
    # print('looking for executables in:\n' + '\n'.join(exec_paths))
    mdt_executables = []
    for path in exec_paths:
        mdt_executables += glob.glob(path + '/mdt-*')
    return mdt_executables


def find_global_config_file():
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isfile(os.environ['XDG_CONFIG_HOME']+'/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME']+'/mdtconfig'
    elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
        return os.path.expanduser('~/.mdtconfig')
    else:
        return None


def find_work_tree():
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


print(find_external_subcmds())
print(find_work_tree())
print(os.getcwd())


