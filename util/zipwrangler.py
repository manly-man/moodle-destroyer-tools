from pathlib import PurePath, Path
from zipfile import ZipFile


ignore = ['__MACOSX', '.DS_Store']


def path_in_root(zipinfo):
    if PurePath('.') == PurePath(zipinfo.filename).parent:
        print(PurePath(zipinfo.filename))
    return PurePath('.') == PurePath(zipinfo.filename).parent


def get_root_content(zipfile_contents):
    """
    FIXME: this will not always work like that and return an empty list
    for example <ZipInfo filename='assignment04/3/' external_attr=0x10>
    where assignment04 is the only folder in the root,
    but does not have an entry in the zip structure for itself.

    This really is a problem and might entail:
     * unzipping everything to a temp folder
       * clean up crud,
       * analyze the resulting folder tree
       * move relevant files to the actual target
       * remove temp folder

    UGH.

    :param zipfile_contents:
    :return:
    """
    return [p for p in zipfile_contents if path_in_root(p)]


def has_multiple_in_root(zipfile):
    return len(get_root_content(zipfile)) > 1


def flatten_content(contents):
    in_root = get_root_content(contents)
    print(in_root)
    while len(in_root) == 1:
        print("we need to go deeper!")
        root = in_root.pop()
        # if root.is_dir():
        print(f"root is: {root.filename}, stripping!")
        contents.remove(root)
        contents = strip_root_from_contents(root, contents)
        in_root = get_root_content(contents)
        # else:
        #     print(f"root is no dir, aborging")
        #     break
    return contents


def strip_root_from_contents(root, contents):
    root_path = PurePath(root.filename)
    for zipinfo in contents:
        path = PurePath(zipinfo.filename)
        new_path = path.relative_to(root_path)
        if zipinfo.is_dir():
            zipinfo.filename = str(new_path) + '/'
        else:
            zipinfo.filename = str(new_path)
        print(zipinfo.filename)
    return contents


def get_cleaned_contents(zipfile):
    contents = []
    for info in zipfile.infolist():
        if not any(ignored in info.filename for ignored in ignore):
            contents.append(info)
        else:
            print(f"ignored: {info.filename}")
    return contents


def get_zips_in_cwd():
    return Path.cwd().glob('*.zip')


def main():
    for zipfilename in get_zips_in_cwd():
        print(zipfilename.name)
        zipfile = ZipFile(zipfilename.name)
        contents = get_cleaned_contents(zipfile)
        target = PurePath(zipfilename).stem
        flat = flatten_content(contents)
        for file in flat:
            zipfile.extract(file, target)



if __name__ == '__main__':
    main()

