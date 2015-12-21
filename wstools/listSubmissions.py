#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' get_submissions params
  'assignmentids' => new external_multiple_structure(
      new external_value(PARAM_INT, 'assignment id'),
      '1 or more assignment ids',
      VALUE_REQUIRED),
  'status' => new external_value(PARAM_ALPHA, 'status', VALUE_DEFAULT, ''),
  'since' => new external_value(PARAM_INT, 'submitted since', VALUE_DEFAULT, 0),
  'before' => new external_value(PARAM_INT, 'submitted before', VALUE_DEFAULT, 0)
'''

import argparse
import configparser
import getpass
import json
import requests
import os.path
class Assignment:
    def __init__(self, aid, submissions):
        self.aid= aid
        self.subs = []
        for s in submissions:
            self.subs.append(Submission(s['id'],s['userid'],s['groupid'],s['plugins']))

    def __str__(self):
        string = str(self.aid) + '\n'
        for s in self.subs:
            string += str(s)
        return string

class Submission:
    def __init__(self, sid, uid, gid, plugs):
        self.sid=sid
        self.uid=uid
        self.gid=gid
        self.plugs=[]
        for p in plugs:
            self.plugs.append(Plugin(p))
        #times

    def __str__(self):
        if 0 == self.gid:
            return ''
        string = ' ' + str(self.gid) + '\n'
        for p in self.plugs:
            string += str(p)
        return string

class Plugin:
    def __init__(self, pd):
        self.kind = pd['type']
        self.name = pd['name']
        if 'editorfields' in pd:
            self.efields = []
            for e in pd['editorfields']:
                self.efields.append(Editorfield(e))
        if 'fileareas' in pd:
            self.fareas = []
            for f in pd['fileareas']:
                self.fareas.append(Filearea(f))

    def __str__(self):
        if 'file' != self.kind:
            return ''
        string = ''
        for fa in self.fareas:
            string += str(fa)
        return string

class Filearea:
    def __init__(self,fd):
        self.area = fd['area']
        self.urls=[]
        if 'files' in fd:
            for f in fd['files']:
                self.urls.append(f['fileurl'])

    def __str__(self):
        string = ''
        if 0 == len(self.urls):
            return ''
        for u in self.urls:
            string += '  ' + u + '\n'
        return string

class Editorfield:
    def __init__(self, ed):
        self.name = ed['name']
        self.descr = ed['description']
        self.text = ed['text']
        self.fmt = ed['format']


#class AssignmentDecoder(json.JSONDecoder):
#    def decode(self, json_string):
#        obj = super(AssignmentDecoder, self).decode(json_string)


cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

argParser.add_argument('aids', help='one or more assignment IDs',type=int, metavar='id', nargs='+')
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='r', encoding='utf8'), default=cfgPath)

args = argParser.parse_args()

cfgParser.read_file(args.config)

moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']
uid = cfgParser['moodle']['uid']
aids = args.aids
url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData2 = {'wstoken':token, 'moodlewsrestformat': 'json', 'wsfunction':'mod_assign_get_submissions', 'assignmentids[]': [aids]}
request2 = requests.post(url, postData2)

asJson = json.loads(request2.text)

assignments = []
for a in asJson['assignments']:
    assignments.append(Assignment(a['assignmentid'], a['submissions']))

for a in assignments:
    print(a)

#for assignment in asJson['assignments']:
#    print(str(assignment['assignmentid']))
#
#    alist=[]
#    for group in assignment['submissions']:
#        plist=[]
#        for plugin in group['plugins']:
#            if(plugin['type'] == 'file'):                
#                flist = []
#                for filearea in plugin['fileareas']:
#                    #print(str(filearea))
#                    if 'files' in filearea:
#                        for f in filearea['files']:
#                            flist.append(f['fileurl'])
#                if len(flist) > 0:
#                    flist.sort()
#                    plist.append([plugin['type'],flist])
#                   # plist.sort()
#                    print(' ' + str(group['groupid']))
#                    alist.append([group['groupid'],plist])
#                    print('  ' + f['fileurl'])
#
#alist.sort()
#
#
#            for file in plugin['filearias']:
#    alist.sort()
#    for a in alist:
###        print(' ' + str(a))
