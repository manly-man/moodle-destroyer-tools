#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import argparse
import configparser
import getpass
import json
import requests
import os.path

cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

passwordText = """
 Please insert user password.
 It will not be saved, it is required to get a token.
Password: """

moodleUrlText = """
The location of you moodle like "moodle.hostname.org"
Moodle: """

moodleUsernameText = 'Your Moodle username: '

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

argParser.add_argument(
    '-m', '--moodle',
    help='moodle url',
    required=False
    )
argParser.add_argument(
    '-u', '--user',
    help='username',
    required=False
    )
argParser.add_argument(
    '-c', '--config',
    help='config file',
    required=False,
    type=argparse.FileType(mode='w', encoding='utf8')
    )

args = argParser.parse_args();


if args.config is not None:
    cfgPath = args.config

if args.moodle is None:
    moodleUrl = input(moodleUrlText)
else:
    moodleUrl = args.moodle

if None == args.user:
    userName = input(moodleUsernameText)
else:
    userName = args.user

userPassword = getpass.getpass(prompt=passwordText)


tokenUrl = 'https://'+moodleUrl+'/login/token.php'
tokenPostData = {
        'username':userName,
        'password':userPassword,
        'service':'moodle_mobile_app'
        }
tokenRequest = requests.post(tokenUrl, tokenPostData)
tokenJson = json.loads(tokenRequest.text)
token = tokenJson['token']

uidUrl = 'https://'+moodleUrl+'/webservice/rest/server.php'
uidPostData = {
        'wstoken':token,
        'moodlewsrestformat': 'json',
        'wsfunction':'core_webservice_get_site_info'
        }
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
