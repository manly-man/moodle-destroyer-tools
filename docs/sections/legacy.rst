Grading without Webservices
===========================

This repository contains two scripts for grading assigments, in case you find yourself with no access to Moodle's Webservices.
**Use at your own risk!**

Prepare moodle
--------------

To use the moodle-destroyer tools, please make sure you configured your submissions like shown in the screenshot.

.. image:: ../images/moodle-settings.png

* `Offline grading worksheet` enables the download of the grading-file.
* `Feedback comments` enables a feedback-column in the grading-file

Description and usage
---------------------

moodle-destroyer.py
^^^^^^^^^^^^^^^^^^^

* Creates a csv file that can be uploaded into moodle.
* Usage: ``python moodle-destroyer --help`` to show usage infos.
* Run this command in the directory where your CSV files are located.
* Single user mode: matching to "Vollständiger Name" instead of "Gruppe"
* Feedback Flag: Set only if gradingfile provides no "Feedback als Kommentar" column. (smart programming led to reverse yoda
  conditions.)

.. code-block:: none

    usage: Moodle Destroyer [-h] -d DESTROY DESTROY [-r RESULT] [-s] [-f] [-v]

    optional arguments:
      -h, --help            show this help message and exit
      -d DESTROY DESTROY, --destroy DESTROY DESTROY
                            grading-file, moodle-file
      -r RESULT, --result RESULT
                            result-file
      -s, --single          is in single mode
      -f, --feedback        no feedback column in grading
      -v, --version         show program's version number and exit

moodle-extractor.py
^^^^^^^^^^^^^^^^^^^

- Unzips exercise submissions
- Run this command in the directory where your Zip is located.

.. code-block:: none

    usage: Moodle Extractor [-h] [-s] [-ng] [-v] zipfile

    positional arguments:
      zipfile               zip file to extract

    optional arguments:
      -h, --help            show this help message and exit
      -s, --single          Single User Mode, default is Group mode
      -ng, --no-grading-file
                            Do not generate grading-file
      -v, --version         show program's version number and exit
