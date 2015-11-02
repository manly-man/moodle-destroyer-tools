#!/usr/bin/env python
# -*- coding: utf-8 -*-
# small script for orderly unzipping of moodle excercise submission downloads
# basic usage: call with path to zipfile
# TODO: change this fuckup with tmpdir, copy it to folder where zipfile is
# located
# TODO: add functions to extract: tarballs, rar
# TODO: detect if UNIX formatted file, if not "dos2unix"
# TODO: make
import sys
import os
import argparse
import shutil
import zipfile
import hashlib
import random
# import argparse
# from os.path import expanduser

parser = argparse.ArgumentParser(prog="Moodle Extractor", prefix_chars="-")

parser.add_argument("-e", "--extract",
                    nargs=1,
                    required=True,
                    type=argparse.FileType('rU'),
                    help="zip file to extract")
parser.add_argument("-s", "--single",
                    action="store_true",
                    default=False,
                    help="Single User Mode, default is Group mode")
parser.add_argument("-v", "--version",
                    action="version",
                    version="version 0.2.0")

args = parser.parse_args()


# iterate through files and delete duplicates based on filehash
def remove_duplicates(directory, ENC="latin-1"):
    unique = []
    for filename in os.listdir(directory):
        f = open(filename, encoding=ENC)
        if os.path.isfile(filename):
            filehash = hashlib.md5(f.read().encode(ENC)).hexdigest()
        if filehash not in unique:
            unique.append(filehash)
        else:
            os.remove(filename)


# check if Archivefile
# true if zip
# false if somethingelse
def isZip(filename):
    # there is a method: RTFM ;)
    # https://docs.python.org/3/library/zipfile.html
    return zipfile.is_zipfile(filename)


# take zip archive , make folder, extract it, deletes archive
def exZip(zip):
    expath = zip.split("-")[0]
    try:
        os.makedirs(expath)
    except FileExistsError:
        os.makedirs(expath+str(random.randint(1, 1001)))

    z = zipfile.ZipFile(zip)
    z.extractall(path=os.path.join(os.getcwd(), expath))
    os.remove(os.path.join(os.getcwd(), zip))


def creategradingfile(dir):
    groupsUnsorted = []
    for file in os.listdir(dir):
        groupsUnsorted.append(file.split("-")[0])
    groups = sorted(list(set(groupsUnsorted)))
    gradingfile = open("gradingfile.csv", 'w')
    gradingfile.write("Gruppe,Bewertung,Feedback als Kommentar\n")
    for group in groups:
        gradingfile.write(group+",,\n")
    gradingfile.close()


def main():

    if args.extract[0] != None:
        ZIPFILENAME = args.extract[0].name
    else:
        raise Exception

    if len(sys.argv) == 1:
        print("usage: command.py zipfile")
        print("use in folder where your Zip is located")
        sys.exit(1)

    # deal with stupid filenames...
    ENC = "latin-1"
    TITLE = "moodle"
    EXCOUNT = 3

    ZIPFILENAME = os.path.split(ZIPFILENAME)[-1][0:-4].replace(' ', '')

    if not args.single:
        CURR_PATH = os.getcwd()
        UNZIPPATH = os.path.join(CURR_PATH, ZIPFILENAME)

        if not os.path.isdir(UNZIPPATH):
            # pathnotexisting
            os.makedirs(UNZIPPATH)
        else:
            # path existing, delete and create
            shutil.rmtree(os.path.join(CURR_PATH))
            os.makedirs(UNZIPPATH)

        # unpack zip
        os.chdir(UNZIPPATH)
        zip = zipfile.ZipFile(os.path.join(CURR_PATH, args.extract[0].name))
        zip.extractall()
        # iterate trough files
        remove_duplicates(os.getcwd(), ENC)

        # iterate through archives and extract
        for file in os.listdir(os.getcwd()):
            if isZip(file):
                exZip(file)

        creategradingfile(os.getcwd())
    else:  # single user mode
        print("single user mode ...")
        curr_path = os.getcwd()
        unzippath = os.path.join(curr_path, ZIPFILENAME)

        if not os.path.isdir(unzippath):
            os.makedirs(unzippath)
        else:
            pass

        # change into folder
        os.chdir(unzippath)
        print(os.path.split(os.getcwd())[0])
        zip = zipfile.ZipFile(os.path.join(os.path.split(os.getcwd())[0],
                                           args.extract[0].name))
        namelist = zip.namelist()
        namelist = [name.split("_")[0] for name in namelist]
        # remove duplicates

        unique_names = []
        [unique_names.append(x) for x in namelist if x not in unique_names]
        print(unique_names)

        # extrctall
        zip.extractall()
        print(os.getcwd())

        # create user folders
        for name in unique_names:
            os.makedirs(name)

        # move files into folders
        dirfilelist = next(os.walk(os.getcwd()))[2]
        for filename in dirfilelist:
            if filename.split("_")[0] in unique_names:
                shutil.move(filename, filename.split("_")[0])

        gradingfile = open("gradingfile.csv", 'w')
        gradingfile.write("Vollständiger Name,Bewertung,Feedback als Kommentar\n")
        for name in sorted(unique_names):
            gradingfile.write(name+",1,\n")
        gradingfile.close()

# create gradingfile for single users

# extract whole folder
# take first.. create folder from name
# if next startwith=same as last folder... extract into
# store takefirst in gradinglist

if __name__ == "__main__":
    main()
