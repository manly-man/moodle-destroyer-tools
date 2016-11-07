Grading with Webservices
========================

This branch is a work in progress for exploiting the moodle WebService backend.
Mostly for easier grading, but also to use moodle from the commandline.
Conquer the moodle world with the best tools provided by manly-man.
**Use at your own risk!**

Prerequisites
-------------

There are some things to do before you can use these tools.

Moodle Server
^^^^^^^^^^^^^

Have you administrator enable the Moodle Mobile backend for you.
If that is not possible, you might want to fall back to the master branch.

Your PC
^^^^^^^

linux machine with python3 installed and the following additional python-libraries:

* requests

why linux? because -1 did not care to make it platform independent.

Installation and usage
----------------------

Installation
^^^^^^^^^^^^

clone the master (!) repository, not develop.
you can then just link mdt.py into your path.

Usage
^^^^^

Why you might not want to use this
""""""""""""""""""""""""""""""""""

* everything is changing, this is a development branch, after all
* code: quality is dubious, interfaces unstable, documentation non-existant. WIP
* no/wonky error handling, moodle almost always says 200 OK, even on exceptions \o/ WIP

If you want to use it anyway:
"""""""""""""""""""""""""""""

mdt.py is a wrapper like git, but not as powerfull:
 some commands are built-in, they will be presented if you execute mdt.
 If you want to hook additional scripts into mdt, put them in you path and prefix the filename with 'mdt-'.
 Mdt will try to execute them, so you can have them in the same toolchain, for nicer workflows.
 Until now, mdt cannot pass information to external scripts. it is planned.

Configuration works much like git, there is a global and some local config files.

global:
 *mdtconfig* will be in one of these folders if present: $XDG_CONFIG_HOME/, ~/.config/
 If none of these folders is found, the global config will be ~/.mdtconfig

local:
 after you use **mdt init** in a directory, you should find the folder .mdt
 Every value in .mdt/config will override the global values.


Implemented Subcommands
"""""""""""""""""""""""

* auth: get a token for the webservice, do that first. It is interactive
* init: will list the courses you enrolled in you can interactively select the ones you want to grade.  Don't put in too many, your admin will thank you.
* sync: retreives the metadata from moodle for your selected courses. If many courses are selected, this will take a while.
* status: without any arguments, it will only display due assignments, see commandline help.
* pull: retrieves and stores submissions for grading. Creates a file for grading result and feedback, interface unstable.
* grade: interprets pull's file with grades in it, submits grades to moodle users, interface unstable.

Planned Subcommands
"""""""""""""""""""

* config: like git, could be useful.
* ?: maybe help grading even further.

planned
"""""""

* extend the scripts to detect which commands you Moodle serves.
* add documentation after decision for a sensible code-architecture.
* accessing Moodle Quizzes
* shell completion
* threaded download
* curses UI, maybe interactive.

unplanned functionality
"""""""""""""""""""""""

* Functionality not involving Web Services: We don't want to navigate the front-end DOM. At least -1 doesn't

