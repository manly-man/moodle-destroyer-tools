#!/usr/bin/env python3
""" get_submissions params
  'assignmentids' => new external_multiple_structure(
      new external_value(PARAM_INT, 'assignment id'),
      '1 or more assignment ids',
      VALUE_REQUIRED),
  'status' => new external_value(PARAM_ALPHA, 'status', VALUE_DEFAULT, ''),
  'since' => new external_value(PARAM_INT, 'submitted since', VALUE_DEFAULT, 0),
  'before' => new external_value(PARAM_INT, 'submitted before', VALUE_DEFAULT, 0)
"""

import json
global singleUser
from MoodleDestroyer import MoodleDestroyer
class Assignment:
    def __init__(self, aid, submissions):
        self.aid= aid
        self.subs = []
        for s in submissions:
            self.subs.append(
                    Submission(s['id'], s['userid'], s['groupid'], s['plugins'])
                    )

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
        string = ''
        for p in self.plugs:
            string += str(p)
        if singleUser:
            if '' != string:
                string = ' ' + str(self.uid) + '\n' + string

        else:
            if 0 == self.gid:
                return ''
            if '' != string:
                string = ' ' + str(self.gid) + '\n' + string

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


def main():
    md = MoodleDestroyer()
    md.argParser.add_argument(
            'aids',
            help='one or more assignment IDs',
            type=int,
            metavar='id',
            nargs='+'
            )
    md.argParser.add_argument(
            '-s', '--single',
            help='single user mode',
            action='store_true',
            default=False
            )

    md.initialize()

    singleUser = md.args.single
    aids = md.args.aids

    asJson = md.rest('mod_assign_get_submissions', {
            'assignmentids[]': [aids]
        })

    print(json.dumps(asJson, indent=1, ensure_ascii=False))
    assignments = []
    for a in asJson['assignments']:
        assignments.append(Assignment(a['assignmentid'], a['submissions']))

    for a in assignments:
        print(a)

if __name__ == '__main__':
    main()
