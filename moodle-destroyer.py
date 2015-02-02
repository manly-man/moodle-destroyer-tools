#!/usr/bin/env python
import sys
import csv

if len(sys.argv) == 1:
    print("Usage: moodle-destroyer moodle-file grading-file output-file")
    print("use in folder where your Zip is located")
    sys.exit(1)

MOODLE_EXPORT = sys.argv[1]
GRADING_FILE = sys.argv[2]
RESULT_FILE = sys.argv[3]

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
