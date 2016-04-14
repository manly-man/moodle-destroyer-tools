#!/usr/bin/env python3
from MoodleDestroyer import MoodleDestroyer

md = MoodleDestroyer()

wsFunc = md.rest('core_webservice_get_site_info')

functions = [func['name'] for func in wsFunc['functions']]
for function in sorted(functions):
    print(function)
