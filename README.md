# Moodle Destroyer Tools

This repository is a collection of scripts used for grading assigments.
Conquer the moodle world with the best tools provided by manly-man.
**Use at your own risk!**

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
                        grading-file, moodle-file, result-file
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

 
