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

assignments = json.loads(request2.text)


for assignment in assignments['assignments']:
    print(str(assignment['assignmentid']))
    alist=[]
    for group in assignment['submissions']:
        plist=[]
        for plugin in group['plugins']:
            if(plugin['type'] == 'file'):                
                flist = []
                for filearea in plugin['fileareas']:
                    #print(str(filearea))
                    if 'files' in filearea:
                        for f in filearea['files']:
                            flist.append(f['fileurl'])
                if len(flist) > 0:
                    flist.sort()
                    plist.append([plugin['type'],flist])
                    plist.sort()
                    print(' ' + str(group['groupid']))
                    alist.append([group['groupid'],plist])
                    print('  ' + f['fileurl'])

alist.sort()


#            for file in plugin['filearias']:
#    alist.sort()
#    for a in alist:
#        print(' ' + str(a))
