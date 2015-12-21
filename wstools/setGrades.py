#!/usr/bin/env python3
# -*- coding: utf-8 -*-
 ''' mod_assign_save_grade params
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

args = argParser.parse_args()

cfgParser.read_file(args.config)

moodleUrl = cfgParser['moodle']['url']
token = cfgParser['moodle']['token']

