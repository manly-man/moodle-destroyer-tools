#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
'''
import argparse
import configparser
import getpass
import json
import requests
import os.path

cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

argParser.add_argument('-m','--moodle', help='moodle url', required=False)
argParser.add_argument('-u', '--user', help='username', required=False)
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='w', encoding='utf8'))

args = argParser.parse_args();

if None != args.config:
    cfgPath = args.config

if None == args.moodle:
    moodleUrl = input('The location of you moodle like "moodle.hostname.org"\nMoodle: ')
else:
    moodleUrl = args.moodle

if None == args.user:
    userName = input('Your Moodle username: ')
else:
    userName = args.user

userPassword = getpass.getpass(prompt=' Please insert user password.\n It will not be saved, it is required to get a token.\nPassword: ')

tokenUrl = 'https://'+moodleUrl+'/login/token.php'
tokenPostData = {'username':userName, 'password':userPassword, 'service':'moodle_mobile_app'}
tokenRequest = requests.post(tokenUrl, tokenPostData)

tokenJson = json.loads(tokenRequest.text)
token = tokenJson['token']

uidUrl = 'https://'+moodleUrl+'/webservice/rest/server.php'
uidPostData = {'wstoken':token, 'moodlewsrestformat': 'json', 'wsfunction':'core_webservice_get_site_info'}
uidRequest = requests.post(uidUrl, uidPostData)

uidJson = json.loads(uidRequest.text)
uid = uidJson['userid']

cfgParser['moodle'] = {
        'url':moodleUrl, 
        'user':userName,
        'uid':uid,
        'token':token
        }

with open(cfgPath, 'w') as cfgFile:
    cfgParser.write(cfgFile)
