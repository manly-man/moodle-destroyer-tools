#!/usr/bin/env python

# small script for orderly unzipping of moodle excercise submission downloads
# basic usage: call with path to zipfile
# TODO: change this fuckup with tmpdir, copy it to folder where zipfile is
# located
# TODO: add functions to extract: tarballs, rar
# TODO: detect if UNIX formatted file, if not "dos2unix"
# TODO: handle .rar and files which are not compressed
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

parser.add_argument("zipfile",
                    nargs=1,
                    type=argparse.FileType('rU'),
                    help="zip file to extract")

parser.add_argument("-s", "--single",
                    action="store_true",
                    default=False,
                    help="Single User Mode, default is Group mode")

parser.add_argument("-ng", "--no-grading-file",
                    action="store_true",
                    default=False,
                    help="Do not generate grading-file")

parser.add_argument("-v", "--version",
                    action="version",
                    version="version 0.3.1")

GRADING_FILE_NAME = "gradingfile.csv"
SINGLE_MODE_CSV_HEADER = "Vollständiger Name,Bewertung,Feedback als Kommentar\n"
GROUP_MODE_CSV_HEADER = "Gruppe,Bewertung,Feedback als Kommentar\n"

# deal with stupid filenames...
ENC = "latin-1"


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
def is_zip(filename):
    # there is a method: RTFM ;)
    # https://docs.python.org/3/library/zipfile.html
    return zipfile.is_zipfile(filename)


# take zip archive , make folder, extract it, deletes archive
def ex_zip(zip):
    expath = zip.split("--")[1]
    try:
        os.makedirs(expath)
    except FileExistsError:
        os.makedirs(expath+str(random.randint(1, 1001)))

    z = zipfile.ZipFile(zip)
    z.extractall(path=os.path.join(os.getcwd(), expath))
    os.remove(os.path.join(os.getcwd(), zip))


def create_grading_file(list, mode="GROUP"):
    gradingfile = open(GRADING_FILE_NAME, 'w')
    if mode == "GROUP":
        gradingfile.write(GROUP_MODE_CSV_HEADER)
    elif mode == "SINGLE":
        gradingfile.write(SINGLE_MODE_CSV_HEADER)
    for item in list:
        gradingfile.write(item+",,\n")
    gradingfile.close()


def parse_zipfilename(args):
    print(str(args.zipfile))
    if args.zipfile[0] is not None:
        file_name = args.zipfile[0].name
    else:
        raise Exception

    return os.path.split(file_name)[-1][0:-4].replace(' ', '')


def create_unzip_folder(curr_path, unzip_path):

    if not os.path.isdir(unzip_path):
        # pathnotexisting
        os.makedirs(unzip_path)
    else:
        # path existing, delete and create
        shutil.rmtree(os.path.join(unzip_path))
        os.makedirs(unzip_path)


def handle_group_mode(zipfilename, curr_path, unzip_path, args):

    create_unzip_folder(curr_path, unzip_path)

    # unpack zip
    os.chdir(unzip_path)
    zip = zipfile.ZipFile(os.path.join(curr_path, args.zipfile[0].name))
    zip.extractall()
    # iterate trough files
    remove_duplicates(os.getcwd(), ENC)

    # get group names for grading file. does not work after unzipping
    groups_unsorted = [file.split("--")[1] for file in os.listdir(unzip_path)]
    groups = sorted(list(set(groups_unsorted)))

    # iterate through archives and extract
    zips = [file for file in os.listdir() if zipfile.is_zipfile(file)]
    for zip in zips:
        ex_zip(zip)

    # ich soll keine doppelte verneinung nicht verwenden...
    if not args.no_grading_file:
        create_grading_file(groups)


def handle_single_mode(zipfilename, curr_path, unzip_path, args):

    create_unzip_folder(curr_path, unzip_path)

    # change into folder
    os.chdir(unzip_path)
    zip = zipfile.ZipFile(os.path.join(os.path.split(os.getcwd())[0],
                                       args.zipfile[0].name))
    namelist = zip.namelist()
    namelist = [name.split("_")[0] for name in namelist]

    # remove duplicates
    unique_names = []
    [unique_names.append(x) for x in namelist if x not in unique_names]

    # extrctall
    zip.extractall()

    # create user folders
    for name in unique_names:
        os.makedirs(name)

    # move files into folders
    dirfilelist = next(os.walk(os.getcwd()))[2]
    for filename in dirfilelist:
        if filename.split("_")[0] in unique_names:
            shutil.move(filename, filename.split("_")[0])

    if not args.no_grading_file:
        create_grading_file(unique_names, "SINGLE")


def main():
    args = parser.parse_args()
    if len(sys.argv) == 1:
        print("usage: command.py zipfile")
        print("use in folder where your Zip is located")
        sys.exit(1)

    ZIPFILENAME = parse_zipfilename(args)
    CURR_PATH = os.getcwd()
    UNZIP_PATH = os.path.join(CURR_PATH, ZIPFILENAME)

    if not args.single:
        handle_group_mode(ZIPFILENAME, CURR_PATH, UNZIP_PATH, args)
    else:  # single user mode
        handle_single_mode(ZIPFILENAME, CURR_PATH, UNZIP_PATH,args)

# create gradingfile for single users

# extract whole folder
# take first.. create folder from name
# if next startwith=same as last folder... extract into
# store takefirst in gradinglist

if __name__ == "__main__":
    main()
