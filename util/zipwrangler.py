from pathlib import Path
from zipfile import ZipFile
from tempfile import TemporaryDirectory
import shutil

ignore = ['__MACOSX', '.DS_Store']


def get_cleaned_contents(zipfile, ignore_list=ignore):
    contents = []
    for info in zipfile.infolist():
        if not any(ignored in info.filename for ignored in ignore_list):
            contents.append(info)
        else:
            print(f'ignored: {info.filename}')
    return contents


def clean_unzip_with_temp_dir(zipfilename: Path, ignore_list=ignore, exist_ok=False):
    zipfile = ZipFile(zipfilename.name)
    target = Path.cwd() / zipfilename.stem
    try:
        target.mkdir(exist_ok)
    except FileExistsError:
        print(f'file exists, not extracting {zipfilename.name} to {target}')
        return

    contents = get_cleaned_contents(zipfile, ignore_list)
    with TemporaryDirectory(dir=Path.cwd().absolute()) as tempdir:
        temp = Path(tempdir)
        for file in contents:
            zipfile.extract(file, path=tempdir)

        contents = list(temp.iterdir())
        while len(contents) == 1:
            content = contents.pop()
            contents = list(content.iterdir())

        for i in contents:
            shutil.move(str(i), str(target))


def main():
    for zipfilename in Path.cwd().glob('*.zip'):
        clean_unzip_with_temp_dir(zipfilename)


if __name__ == '__main__':
    main()

