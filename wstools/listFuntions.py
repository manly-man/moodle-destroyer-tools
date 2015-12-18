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

url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData = {'wstoken':token, 'moodlewsrestformat': 'json', 'wsfunction':'core_webservice_get_site_info'}
request = requests.post(url, postData)

wsFunc = json.loads(request.text)

functions = [func['name'] for func in wsFunc['functions']]
for function in sorted(functions):
    print(function)

