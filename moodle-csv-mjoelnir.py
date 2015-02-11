#!/usr/bin/env python
import sys,csv

if len(sys.argv) == 1:
    print("Usage: moodle-csv-mjoelnir moodle-csv-file  output-file")
    print("use in folder where your csv file is located")
    sys.exit(1)

try:
    MOODLE_EXPORT = sys.argv[1]
    RESULT_FILE = sys.argv[2] 
except IndexError:
    print("provide a filename for smashing csv")
    print("Usage: moodle-csv-mjoelnir moodle-csv-file  [output-file]")
    print("use in folder where your csv file is located")
    sys.exit(1);

with open(MOODLE_EXPORT, 'rU', newline='') as moodle, \
        open(RESULT_FILE, 'w', newline='') as result:
    reader_moodle = csv.DictReader(moodle)
    header = reader_moodle.fieldnames

    writer = csv.DictWriter( result, header, quotechar='"',
            quoting=csv.QUOTE_NONNUMERIC)

    writer.writeheader()
    moodlelist = []

    for line in reader_moodle:
        for k in line:
            a = line[k].replace("\n"," ")
            line[k] = a
        writer.writerow(line)
