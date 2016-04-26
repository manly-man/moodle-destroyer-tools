#!/usr/bin/env python3
import os

def find_subcmd(program):
    return program


path = os.environ['PATH'].split(os.pathsep)

print(path)
