#!/usr/bin/env python

#small script for orderly unzipping of moodle excercise submission downloads
#basic usage: call with path to zipfile
#TODO: change this fuckup with tmpdir, copy it to folder where zipfile is located
#TODO: add functions to extract: tarballs, rar
#TODO: detect if UNIX formatted file, if not "dos2unix"
#TODO: make
import sys, os
import shutil
import zipfile
import hashlib
#import argparse
#from os.path import expanduser
if len(sys.argv) == 1:
    print("usage: command.py zipfile")
    print("use in folder where your Zip is located")
    sys.exit(1)

ENC = "latin-1" #deal with stupid filenames...
TITLE = "moodle"
EXCOUNT = 3

#iterate through files and delete duplicates based on filehash
def remove_duplicates(directory):
    unique = []
    for filename in os.listdir(directory):
        f = open(filename, encoding=ENC)
        if os.path.isfile(filename):
            filehash = hashlib.md5(f.read().encode(ENC)).hexdigest()
        if filehash not in unique:
            unique.append(filehash)
        else:
            os.remove(filename)

#check if Archivefile
# true if zip
# false if somethingelse
def isZip(filename):
    if filename.split(".")[-1] == "zip":
        return True
    else:
        return False

#take zip archive , make folder, extract it, deletes archive
def exZip(zip):
    expath = zip.split("-")[0]
    os.makedirs(expath)
    z = zipfile.ZipFile(zip)
    z.extractall(path=os.path.join(os.getcwd(), expath))
    os.remove(os.path.join(os.getcwd(), zip))

def creategradingfile(dir):
    groupsUnsorted = []
    for file in os.listdir(dir):
        groupsUnsorted.append(file.split("-")[0][7:])
    groups = sorted(list(set(groupsUnsorted)))
    gradingfile = open("gradingfile.csv", 'w')
    gradingfile.write("Gruppe, Bewertung, Feedback als Kommentar\n")
    for group in groups:
        gradingfile.write(group+",,\n")
    gradingfile.close()


ZIPFILENAME = sys.argv[-1]
ZIPFILENAME = os.path.split(ZIPFILENAME)[-1][0:-4].replace(' ', '')
#unzip file

CURR_PATH = os.getcwd()
UNZIPPATH = os.path.join(CURR_PATH, ZIPFILENAME)

if not os.path.isdir(UNZIPPATH):
    #pathnotexisting
    os.makedirs(UNZIPPATH)
else:
    #path existing, delete and create
    shutil.rmtree(os.path.join(CURR_PATH))
    os.makedirs(UNZIPPATH)

#unpack zip
os.chdir(UNZIPPATH)
zip = zipfile.ZipFile(os.path.join(CURR_PATH, sys.argv[-1]))
zip.extractall()
#iterate trough files
remove_duplicates(os.getcwd())

#iterate through archives and extract
for file in os.listdir(os.getcwd()):
    if isZip(file):
        exZip(file)

creategradingfile(os.getcwd())
