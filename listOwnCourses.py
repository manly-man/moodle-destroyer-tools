#!/usr/bin/env python3
from MoodleDestroyer import MoodleDestroyer

md = MoodleDestroyer()
md.initialize()
courses = md.rest('core_enrol_get_users_courses', {
        'userid': md.uid
    })

clist = []
for course in courses:
    if 1 == course['visible']:
        clist.append([course['id'],course['fullname']])

clist.sort()
for c in clist:
    print(c)
