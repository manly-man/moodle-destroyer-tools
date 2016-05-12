#!/usr/bin/env python3
""" login/token.php params
// MDL-43119 Token valid for 3 months (12 weeks).
$username = required_param('username', PARAM_USERNAME);
$password = required_param('password', PARAM_RAW);
$serviceshortname  = required_param('service',  PARAM_ALPHANUMEXT);
"""
import getpass
from MoodleDestroyer import MoodleDestroyer

passwordText = """
 Please insert your Moodle password.
 It will not be saved, it is required to get a token.
 Attention: keep your token safe until MDL-53400 is resolved.
 Until then it CANNOT be reset.
Password: """

moodleUrlText = """
The location of you moodle like "moodle.hostname.org"
Moodle: """

moodleUsernameText = 'Your Moodle username: '

md = MoodleDestroyer()

md.argParser.add_argument(
    '-m', '--moodle',
    help='moodle url',
    required=False
    )
md.argParser.add_argument(
    '-u', '--user',
    help='username',
    required=False
    )

md.initialize()

if md.args.config is not None:
    cfgPath = md.args.config

if md.args.moodle is None:
    md.moodleUrl = input(moodleUrlText)
else:
    md.moodleUrl = md.args.moodle

if None is md.args.user:
    userName = input(moodleUsernameText)
else:
    userName = md.args.user

userPassword = getpass.getpass(prompt=passwordText)


tokenJson = md.rest_direct('/login/token.php', {
        'username':userName,
        'password':userPassword,
        'service':'moodle_mobile_app'
    })
md.token = tokenJson['token']

uidJson = md.rest('core_webservice_get_site_info')
uid = uidJson['userid']

md.cfgParser['moodle'] = {
        'url':md.moodleUrl,
        'user':userName,
        'uid':uid,
        'token':md.token
        }

with open(cfgPath, 'w') as cfgFile:
    md.cfgParser.write(cfgFile)
