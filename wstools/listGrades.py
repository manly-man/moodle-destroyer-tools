#!/usr/bin/env python3

import argparse
import configparser
import getpass
import json
import requests
import os.path

cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

#argParser.add_argument('aids', help='one or more assignment IDs',type=int, metavar='id', nargs='+')
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='r', encoding='utf8'), default=cfgPath)
argParser.add_argument('-a', '--assignment', help='assignment id', required=True)

args = argParser.parse_args()

cfgParser.read_file(args.config)

moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']

url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData = {
        'wstoken':token,
        'moodlewsrestformat': 'json',
        'wsfunction':'mod_assign_get_grades',
        'assignmentids[]': args.assignment,
        }
request = requests.post(url, postData)
print(request.text)
