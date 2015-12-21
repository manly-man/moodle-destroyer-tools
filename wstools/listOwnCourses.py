#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import configparser
import getpass
import json
import requests
import os.path
import operator

cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

#argParser.add_argument('-m','--moodle', help='moodle url', required=False)
#argParser.add_argument('-u', '--user', help='username', required=False)
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='r', encoding='utf8'), default=cfgPath)

args = argParser.parse_args()

cfgParser.read_file(args.config)

#TODO change getToken to save moodleUrl instead of url
moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']
uid = cfgParser['moodle']['uid']

url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData2 = {'wstoken':token, 'moodlewsrestformat': 'json', 'wsfunction':'core_enrol_get_users_courses', 'userid': uid}
request2 = requests.post(url, postData2)

courses = json.loads(request2.text)

clist = []
for course in courses:
    if 1 == course['visible']:
        clist.append([course['id'],course['fullname']])
#        print(str(course['id']) + ' ' +course['fullname'])
clist.sort()
for c in clist:
    print(c)
#functions = [func['name'] for func in wsFunc['functions']]
#for function in sorted(functions):
#    print(function)

