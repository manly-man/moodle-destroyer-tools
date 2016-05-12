#!/usr/bin/env python3
from MoodleDestroyer import MoodleDestroyer

md = MoodleDestroyer()
#md.argParser.add_argument('aids', help='one or more assignment IDs',type=int, metavar='id', nargs='+')
md.argParser.add_argument('-a', '--assignment', help='assignment id', required=True)
md.initialize()

grades = md.rest('mod_assign_get_grades', {
        'assignmentids[]': md.args.assignment
    })
print(grades)
