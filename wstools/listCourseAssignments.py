#!/usr/bin/env python3
from MoodleDestroyer import MoodleDestroyer

md = MoodleDestroyer()
md.argParser.add_argument(
        'cids',
        help='one or more course IDs',
        type=int, metavar='id',
        nargs='+'
        )
md.initialize()
cids = md.args.cids

assignments = md.rest('mod_assign_get_assignments', {
        'courseids[]': [cids]
    })

for course in assignments['courses']:
    print(str(course['id']) + ' ' + course['fullname'])
    alist=[]
    for assignment in course['assignments']:
        alist.append([assignment['id'], assignment['name']])
    alist.sort()
    for a in alist:
        print(' ' + str(a))
