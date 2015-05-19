#!/usr/bin/env python
import sys
import csv
import argparse

parser = argparse.ArgumentParser(prog="Moodle Destroyer", prefix_chars="-")

parser.add_argument("-v", "--version", help="WE ARE TALKING ABOUT THE VERSION")
parser.add_argument("-g", "--grading", help="ALL YOUR GRADINGS BELONG TO US")
parser.add_argument("-m", "--moodle", help="gimme the moodle stuff")
parser.add_argument("-r", "--result", help="name your result")

args=parser.parse_args()

if len(sys.argv) == 1:
    print("Usage: moodle-destroyer moodle-file grading-file output-file")
    print("use in folder where your Zip is located")
    sys.exit(1)

    if args.grading != None:
        GRADING_FILE = args.grading
    else:
        raise Exception

    if args.moodle != None:
        MOODLE_EXPORT = args.moodle
    else:
        raise Exception

    if args.result != None:
        RESULT_FILE = args.result
    else:
        raise Exception

with open(GRADING_FILE, 'rU', newline='') as grading, \
    open(MOODLE_EXPORT, 'rU', newline='') as moodle, \
    open(RESULT_FILE, 'w', newline='') as result:
    reader_grading = csv.DictReader(grading)
    reader_moodle = csv.DictReader(moodle)

    header = reader_moodle.fieldnames 
    writer = csv.DictWriter(result, \
                            header, \
                            quotechar='"', \
                            quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()   
    moodlelist = []
    gradinglist = []

    for line in reader_moodle:
        moodlelist.append(line)
    for line in reader_grading:
        gradinglist.append(line)

    for line in gradinglist:
        for row in moodlelist:
            #print(line['Gruppe'],"\nrow:",row['Gruppe'])
            if line['Gruppe'] == row['Gruppe']:
                    row['Bewertung'] = line['Bewertung']
                    row['Feedback als Kommentar'] = line['Feedback als Kommentar']
                    writer.writerow(row)
