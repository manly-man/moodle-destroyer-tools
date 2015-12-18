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

argParser.add_argument('cids', help='one or more course IDs',type=int, metavar='id', nargs='+')
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='r', encoding='utf8'), default=cfgPath)

args = argParser.parse_args()

cfgParser.read_file(args.config)

moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']
uid = cfgParser['moodle']['uid']
cids = args.cids

url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData2 = {'wstoken':token, 'moodlewsrestformat': 'json', 'wsfunction':'mod_assign_get_assignments', 'courseids[]': [cids]}
request2 = requests.post(url, postData2)

assignments = json.loads(request2.text)

for course in assignments['courses']:
    print(str(course['id']) + ' ' + course['fullname'])
    for assignment in course['assignments']:
        print(' '+str(assignment['id']) + ' ' +assignment['name'])
