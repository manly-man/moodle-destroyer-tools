# Moodle Destroyer Tools

This repository is a collection of scripts used for grading assigments.
Conquer the moodle world with the best tools provided by manly-man.
**Use at your own risk!**

## Prepare moodle

To use the moodle-destroyer tools, please make sure you configured your submissions like shown in the screenshot.

![moodle-settings](https://raw.githubusercontent.com/manly-man/moodle-destroyer-tools/develop/docs/images/moodle-settings.png)

* `Offline grading worksheet` enables the download of the grading-file.
* `Feedback comments` enables a feedback-column in the grading-file

## Description and usage

* moodle-destroyer.py:
  - Creates a csv file that can be uploaded into moodle.
  - Usage: ```python moodle-destroyer --helpi``` to show usage infos.
  - Run this command in the directory where your CSV files are located.
  - Single user mode: matching to "Vollständiger Name" instead of "Gruppe"
  - Feedback Flag: Set only if gradingfile provides no "Feedback als Kommentar" column. (smart programming led to reverse yoda
    conditions.)
```
optional arguments: -h, --help            show this help message and exit
  -d DESTROY DESTROY, --destroy DESTROY DESTROY
                        grading-file, moodle-file
  -r RESULT, --result RESULT
                        result-file
  -s, --single          is in single mode
  -f, --feedback        no feedback column in grading
```
* moodle.extractor.py:
  - Unzips exercise submissions
  - Usage:
```
usage: Moodle Extractor [-h] -e EXTRACT [-s] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -e EXTRACT, --extract EXTRACT
                        zip file to extract
  -s, --single          Single User Mode, default is Group mode
  -v, --version         show program's version number and exit
``` 
  - Run this command in the directory where your Zip is located.

## Development

Before starting to develop on manly-man moodle scripts you should run the `boostrap` script.
This will setup `git-flow` with the default settings.

We recommend [`git-flow AVH Edition`](https://github.com/petervanderdoes/gitflow/).
For detailed installation instructions have a look at [https://github.com/petervanderdoes/gitflow/wiki](https://github.com/petervanderdoes/gitflow/wiki)

### Working with git-flow

1. Start a new feature with `git-flow feature start FEATURE_NAME` (this creates a new branch)
2. Hack on your feature
3. Finish your feature with `git-flow feature stop FEATURE_NAME` (this merges the branch into `develop`)

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

linux machine with python3 installed and the following additional python-libraries: 
* configargparse
* requests

## Installation and usage

### Installation

just link mdt.py into your path.

### Usage

#### Why you might not want to use this

* everything is changing, this is a development branch, after all
* code: quality is dubious, interfaces unstable, documentation non-existant. WIP
* no/wonky error handling, moodle almost always says 200 OK, even on exceptions \o/ WIP

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
* status: without any arguments, it will only display due assignments, see commandline help.
* pull: retrieves and stores submissions for grading. Creates a file for grading result and feedback, interface unstable.
* grade: interprets pull's file with grades in it, submits grades to moodle users, interface unstable.  

#### Planned Subcommands

* config: like git, could be useful.
* ?: maybe help grading even further.

#### planned

* extend the scripts to detect which commands you Moodle serves.
* add documentation after decision for a sensible code-architecture.
* accessing Moodle Quizzes
* shell completion
* threaded download
* curses UI, maybe interactive.

#### unplanned functionality

* Functionality not involving Web Services: We don't want to navigate the front-end DOM. At least -1 doesn't

## Development

### Where you can help 

Backend:

* moodle.communication: MoodleSession implements Moodle's Web Service API: it is incomplete and has no support for different service versions.
Implementing those is tedious, especially since Moodles API is pretty wonky: You will almost always receive 200 OK, and will have to handle exceptions on foot.

* moodle.models: contains various half-hearted representations of Moodle data structures. 
They are badly interconnected and need restructuring. 

Frontend:

* wstools: needs command structure. maybe a curses interface.


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

### Bootstrap

Before starting to develop on manly-man moodle scripts you should run the `boostrap` script.
This will setup `git-flow` with the default settings.

We recommend [`git-flow AVH Edition`](https://github.com/petervanderdoes/gitflow/).
For detailed installation instructions have a look at [https://github.com/petervanderdoes/gitflow/wiki](https://github.com/petervanderdoes/gitflow/wiki)

### Working with git-flow

1. Start a new feature with `git-flow feature start FEATURE_NAME` (this creates a new branch)
2. Hack on your feature
3. Finish your feature with `git-flow feature stop FEATURE_NAME` (this merges the branch into `develop`)


