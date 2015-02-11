# **Moodle Destroyer Tools**

This repository is a collection of scripts manly-man uses for correcting exercises. Conquer the moodle world with the best tools provided by manly-man. Use at own risk!

---
## Description and usage

* moodle-destroyer.py:
  - Creates a csv file that can be uploaded into moodle.
  - Usage: `moodle-destroyer.py moodle-file grading-file output-file`
  - Run this command in the directory where your CSV files are located.
* moodle.extractor.py:
  - Unzips exercise submissions
  - Usage: `moodle-extractor.py zipfile`
  - Run this command in the directory where your Zip is located.
  
**DO NOT USE moodle-destroyer.rb !!**

## Development

Before starting to develop on manly-man moodle scripts you should run the `boostrap` script.
This will setup `git-flow` with the default settings.

We recommend [`git-flow AVH Edition`](https://github.com/petervanderdoes/gitflow/).
For detailed installation instructions have a look at [https://github.com/petervanderdoes/gitflow/wiki](https://github.com/petervanderdoes/gitflow/wiki)

### Working with git-flow

1. Start a new feature with `git-flow feature start FEATURE_NAME` (this creates a new branch)
2. Hack on your feature
3. Finish your feature with `git-flow feature stop FEATURE_NAME` (this merges the branch into `develop`)

 
