# Moodle Destroyer Tools - Web Service Edition

This branch is a work in progress for exploiting the moodle WebService backend for easier grading of assigments.
Conquer the moodle world with the best tools provided by manly-man.
**Use at your own risk!**

## Prerequisites

There are some things to do before you can use these tools.

### Moodle Server

Have you administrator enable the Moodle Mobile backend for you.
If that is not possible, you might want to fall back to the master branch.

### Your PC

have python3 installed and the following additional python-libraries: 
* configargparse
* requests

## Installation and usage

### Installation

just link mdt.py into your path.

### Usage

#### Why you might not want to use this

* everything is changing, this is a development branch, after all
* code: quality is dubious, interfaces unstable, documentation non-existant.
* no/wonky error handling

#### If you want to use it anyway:

mdt.py is a wrapper like git, but not as powerfull:
 some commands are built-in, they will be presented if you execute mdt.
 If you want to hook additional scripts into mdt, put them in you path and prefix the filename with 'mdt-'.
 Mdt will try to execute them, so you can have them in the same toolchain, for nicer workflows.
 Until now, mdt cannot pass information to external scripts. it is planned.
 
Configuration works much like git, there is a global and some local config files.

global: *mdtconfig* will be in one of these folders if present: $XDG_CONFIG_HOME/, ~/.config/
If none of these folders is found, the global config will be ~/.mdtconfig

local: after you use **mdt init** in a directory, you should find the folder .mdt
Every value in .mdt/config will override the global values.


#### Implemented Subcommands

* auth: get a token for the webservice, do that first. It is interactive
* init: will list the courses you enrolled in you can interactively select the ones you want to grade.  Don't put in too many, your admin will thank you.
* sync: retreives the metadata from moodle for your selected courses. If many courses are selected, this will take a while.
* status: without any arguments, it will only display due assignments, detection is WIP.

#### Planned Subcommands

* pull: retrieves and stores submissions for grading. Creates a file for grading result and Feedback. Is up next.
* config: like git, could be useful.
* ?: use grading file from pull as input to submit grades to moodle.
* ?: maybe help grading even further.

#### planned

* extend the scripts to detect which commands you Moodle serves.
* add documentation after decision for a sensible code-architecture.

#### unplanned functionality

* Moodle Quizzes have no Web Service exported functions, must be implemented in Moodle first.
* Functionality not involving Web Services: We don't want to navigate the front-end DOM. At least -1 doesn't

## Development

### Documentation

#### Moodle back-end

Moodle Developers do not provide direct access to the Web Service API.
The WS API Documentation is only available per Moodle instance, so you are left with some choices:

* Ask your Moodle Administrator for it,
* set-up your own Moodle Instance (I recommend you don't, installation takes a really long time),
* get it from the [Moodle Demo Server](https://moodle.org/demo/),
* dig in Moodle's PHP sources (I also recommend against that, use as last resort. Does not help understanding the data structures.)

#### This Code

Well, you are reading it… That is how much documentation there is.
If you really, really want to help the tool along or ask for an explanation, ask -1 via [twitter](https://twitter.com/einsweniger/) or mail.

### Bootsrap

Before starting to develop on manly-man moodle scripts you should run the `boostrap` script.
This will setup `git-flow` with the default settings.

We recommend [`git-flow AVH Edition`](https://github.com/petervanderdoes/gitflow/).
For detailed installation instructions have a look at [https://github.com/petervanderdoes/gitflow/wiki](https://github.com/petervanderdoes/gitflow/wiki)

### Working with git-flow

1. Start a new feature with `git-flow feature start FEATURE_NAME` (this creates a new branch)
2. Hack on your feature
3. Finish your feature with `git-flow feature stop FEATURE_NAME` (this merges the branch into `develop`)


