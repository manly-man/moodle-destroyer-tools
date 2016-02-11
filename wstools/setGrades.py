#!/usr/bin/env python3
'''mod_assign_save_grade params
  'assignmentid' => new external_value(PARAM_INT, 'The assignment id to operate on'),
  'userid' => new external_value(PARAM_INT, 'The student id to operate on'),
  'grade' => new external_value(PARAM_FLOAT, 'The new grade for this user. Ignored if advanced grading used'),
  'attemptnumber' => new external_value(PARAM_INT, 'The attempt number (-1 means latest attempt)'),
  'addattempt' => new external_value(PARAM_BOOL, 'Allow another attempt if the attempt reopen method is manual'),
  'workflowstate' => new external_value(PARAM_ALPHA, 'The next marking workflow state'),
  'applytoall' => new external_value(PARAM_BOOL, 'If true, this grade will be applied ' .
                                                 'to all members ' .
                                                 'of the group (for group assignments).'),
  'plugindata' => new external_single_structure($pluginfeedbackparams, 'plugin data', VALUE_DEFAULT, array()),
  'advancedgradingdata' => new external_single_structure($advancedgradingdata, 'advanced grading data', VALUE_DEFAULT, array())
      /**
     * Save a student grade for a single assignment.
     *
     * @param int $assignmentid The id of the assignment
     * @param int $userid The id of the user
     * @param float $grade The grade (ignored if the assignment uses advanced grading)
     * @param int $attemptnumber The attempt number
     * @param bool $addattempt Allow another attempt
     * @param string $workflowstate New workflow state
     * @param bool $applytoall Apply the grade to all members of the group
     * @param array $plugindata Custom data used by plugins
     * @param array $advancedgradingdata Advanced grading data
     * @return null
     * @since Moodle 2.6
     */
        return new external_function_parameters(
            array(
                'assignmentid' => new external_value(PARAM_INT, 'The assignment id to operate on'),
                'applytoall' => new external_value(PARAM_BOOL, 'If true, this grade will be applied ' .
                                                               'to all members ' .
                                                               'of the group (for group assignments).'),
                'grades' => new external_multiple_structure(
                    new external_single_structure(
                        array (
                            'userid' => new external_value(PARAM_INT, 'The student id to operate on'),
                            'grade' => new external_value(PARAM_FLOAT, 'The new grade for this user. '.
                                                                       'Ignored if advanced grading used'),
                            'attemptnumber' => new external_value(PARAM_INT, 'The attempt number (-1 means latest attempt)'),
                            'addattempt' => new external_value(PARAM_BOOL, 'Allow another attempt if manual attempt reopen method'),
                            'workflowstate' => new external_value(PARAM_ALPHA, 'The next marking workflow state'),
                            'plugindata' => new external_single_structure($pluginfeedbackparams, 'plugin data',
                                                                          VALUE_DEFAULT, array()),
                            'advancedgradingdata' => new external_single_structure($advancedgradingdata, 'advanced grading data',
                                                                                   VALUE_DEFAULT, array())
                        )
                    )
                )
            )

'''

''' mod_assign_assign_grades
    /**
     * Creates an assign_grades external_single_structure
     * @return external_single_structure
     * @since  Moodle 2.4
     */
    private static function assign_grades() {
        return new external_single_structure(
            array (
                'assignmentid'    => new external_value(PARAM_INT, 'assignment id'),
                'grades'   => new external_multiple_structure(new external_single_structure(
                        array(
                            'id'            => new external_value(PARAM_INT, 'grade id'),
                            'userid'        => new external_value(PARAM_INT, 'student id'),
                            'attemptnumber' => new external_value(PARAM_INT, 'attempt number'),
                            'timecreated'   => new external_value(PARAM_INT, 'grade creation time'),
                            'timemodified'  => new external_value(PARAM_INT, 'grade last modified time'),
                            'grader'        => new external_value(PARAM_INT, 'grader'),
                            'grade'         => new external_value(PARAM_TEXT, 'grade')
                        )
                    )
                )
            )
        );
    }


'''
import argparse
import configparser
import getpass
import json
import requests
import os.path

cfgPath = os.path.expanduser('~/.config/moodle_destroyer')

cfgParser = configparser.ConfigParser()
argParser = argparse.ArgumentParser(prefix_chars='-');

#argParser.add_argument('aids', help='one or more assignment IDs',type=int, metavar='id', nargs='+')
argParser.add_argument('-c', '--config', help='config file', required=False, type=argparse.FileType(mode='r', encoding='utf8'), default=cfgPath)
argParser.add_argument('-a', '--assignment', help='assignment id', required=True)
argParser.add_argument('-u', '--user', help='user id', required=True)
argParser.add_argument('-g', '--grade', help='grade for assignment', required=True)

args = argParser.parse_args()

cfgParser.read_file(args.config)

moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']

url = 'https://'+moodleUrl+'/webservice/rest/server.php'
postData = {
        'wstoken':token,
        'moodlewsrestformat': 'json',
        'wsfunction':'mod_assign_save_grade',
        'assignmentid': args.assignment,
        'userid': args.user,
        'grade': args.grade,
        'attemptnumber': -1,
        'addattempt': 0,
        'workflowstate': "a", #i dunno
        'applytoall': 0,
        'plugindata[assignfeedbackcomments_editor][text]': 'no text',
        'plugindata[assignfeedbackcomments_editor][format]': 2, #plain
        'plugindata[files_filemanager]': 0 # no file
        }
request = requests.post(url, postData)
print(request.text)
