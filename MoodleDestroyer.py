#!/usr/bin/env python3
import argparse
import configparser
import json
import requests
import os.path


class MoodleDestroyer:
    def __init__(self, cfg_file='~/.config/moodle_destroyer'):
        self.cfgFile = cfg_file

        cfgPath = os.path.expanduser(self.cfgFile)

        self.cfgParser = configparser.ConfigParser()
        self.argParser = argparse.ArgumentParser(prefix_chars='-')

        self.argParser.add_argument(
                '-c', '--config',
                help='config file',
                required=False,
                default=cfgPath
                )

        self.initialized = False

    def initialize(self):
        if self.initialized:
            return

        self.args = self.argParser.parse_args()
        try:
            f = open(self.args.config, 'r')
            self.cfgParser.read_file(f)

            self.moodleUrl = self.cfgParser['moodle']['url']
            self.token = self.cfgParser['moodle']['token']
            self.uid = self.cfgParser['moodle']['uid']

        except:
            pass

        self.urlpath = '/webservice/rest/server.php'

        self.initialized = True

    def rest_direct(self, path, args={}):
        self.initialize()

        request = requests.post('https://'+self.moodleUrl+path, args)
        return json.loads(request.text)

    def rest(self, function, args={}):
        self.initialize()

        postData = {
                'wstoken': self.token,
                'moodlewsrestformat': 'json',
                'wsfunction': function
                }
        postData.update(args)
        return self.rest_direct(self.urlpath, postData)
