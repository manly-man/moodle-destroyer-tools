#!/usr/bin/env python
import sys,csv

class Student:
    # name = ""
    # email = ""
    # submissions = []

    def __init__(self):
        self.name = ""
        self.email = ""
        self.submissions = []

    # def addSubmission(self, points):
    #    self.submissions.append(points)

    # def getSubmissions(self):
    #     return self.submissions

    def calcBonus(self, points, maxFailed):

        failedSubmissions = 0

        if len(points) != len(self.submissions):
            print("Exit")
            return
        else:
            for p,s in zip(points,self.submissions):
                if s < p/2:
                    failedSubmissions += 1

        if failedSubmissions > maxFailed:
            return False
        else:
            return True

students = []

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
    reader_moodle = csv.reader(moodle)
    # header = reader_moodle.fieldnames

    # writer = csv.DictWriter( result, header, quotechar='"',
    #         quoting=csv.QUOTE_NONNUMERIC)

    # writer.writeheader()
    # moodlelist = []

    firstName = ""
    lastName = ""
    email = ""
    submission = 0

    for line in reader_moodle:

        print("\n")
        newStudent = Student()
        i = 0
        for key, value in line.items():

            print(key, value)
            print("Header: " + header[i])
            if key == header[i] and key == "Vorname":
                firstName = value
            if key == header[i] and key == "Nachname":
                lastName = value
            if key == header[i] and key == "E-Mail-Adresse":
                email = value
            if key == header[i] and key.startswith("Aufgabe:"):
                newStudent.submissions.append(value)

            newStudent.name = lastName + ", " + firstName
            newStudent.email = email
            i += 1
            
        students.append(newStudent)

        '''
        for k in line:
            a = line[k].replace("\n"," ")
            line[k] = a
        writer.writerow(line)
        '''

    print(students[3].name)
    print(students[3].email)
    print(students[3].submissions)
