import glob
import json
import os
import configparser

LOCAL_CONFIG_FOLDER = '.mdt/'
LOCAL_CONFIG = LOCAL_CONFIG_FOLDER + 'config'
LOCAL_CONFIG_USERS = LOCAL_CONFIG_FOLDER + 'users'
LOCAL_CONFIG_MOODLE = LOCAL_CONFIG_FOLDER + 'moodle'
LOCAL_CONFIG_COURSES = LOCAL_CONFIG_FOLDER + 'courses'
ASSIGNMENT_FOLDER = LOCAL_CONFIG_FOLDER + 'assignments/'
SUBMISSION_FOLDER = LOCAL_CONFIG_FOLDER + 'submissions/'
GRADE_FOLDER = LOCAL_CONFIG_FOLDER + 'grades/'


def create_global_config_file():
    file = ''
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isdir(os.environ['XDG_CONFIG_HOME']):
            file = os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
    elif os.path.isdir(os.path.expanduser('~/.config')):
        file = os.path.expanduser('~/.config/mdtconfig')
    else:
        file = os.path.expanduser('~/.mdtconfig')
    text = 'could not find global config, creating {}'
    print(text.format(file))
    open(file, 'w').close()
    return file


def get_global_config_file():
    if 'XDG_CONFIG_HOME' in os.environ:
        if os.path.isfile(os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'):
            return os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
    elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
        return os.path.expanduser('~/.config/mdtconfig')
    elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
        return os.path.expanduser('~/.mdtconfig')
    else:
        return create_global_config_file()


def get_config_file_list():
    global_config = get_global_config_file()
    cfg_files = [global_config]
    work_tree = get_work_tree_root()
    if work_tree is not None:
        # default_config_files order is crucial: work_tree cfg overrides global
        cfg_files.append(work_tree + '/.mdt/config')
    return cfg_files


def get_work_tree_root():
    """ determines the work tree root by looking at the .mdt folder in cwd or parent folders
    :returns the work tree root as String or None
    """
    cwd = os.getcwd()
    repo = None
    while not os.path.isdir('.mdt'):
        if '/' == os.getcwd():
            os.chdir(cwd)
            return None
        os.chdir(os.pardir)
    if os.path.isdir('.mdt'):
        repo = os.getcwd()
    os.chdir(cwd)
    return repo + '/'


def in_root():
    return os.path.isdir(LOCAL_CONFIG_FOLDER)


def in_tree():
    return get_work_tree_root() is not None


def merge_local_json_data(courseids=[]):
    wd = get_work_tree_root()
    if wd is None:
        raise SystemExit(1, 'not in worktree.')
    courses = _load_json_file(wd + LOCAL_CONFIG_COURSES)
    users = _load_json_file(wd + LOCAL_CONFIG_USERS)
    assignments = _merge_json_data_in_folder(wd + ASSIGNMENT_FOLDER)
    submissions = _merge_json_data_in_folder(wd + SUBMISSION_FOLDER)
    grades = _merge_json_data_in_folder(wd + GRADE_FOLDER)

    merged = []
    for course in courses:
        for ulist in users:
            if ulist['courseid'] == course['id']:
                course['users'] = ulist['users']

        course_assignments = [a for a in assignments if a['course'] == course['id']]

        for assignment in course_assignments:
            for submission in submissions:
                if assignment['id'] == submission['assignmentid']:
                    assignment['submissions'] = submission['submissions']
            for grade in grades:
                if assignment['id'] == grade['assignmentid']:
                    assignment['grades'] = grade['grades']
        course['assignments'] = course_assignments

        merged.append(course)

    return merged


def _merge_json_data_in_folder(path):
    files = glob.glob(path + '*')
    data_list = [_load_json_file(file) for file in files]
    return data_list


def _load_json_file(filename):
    with open(filename) as file:
        return json.load(file)


def write_local_course_meta(course_data):
    _write_config(LOCAL_CONFIG_COURSES, course_data)


def write_global_config(config_dict):
    with open(get_global_config_file(), 'w') as file:
        cfg_parser = configparser.ConfigParser()
        cfg_parser['global moodle settings'] = config_dict
        cfg_parser.write(file)


def write_local_config(config_data):
    _write_config(LOCAL_CONFIG, config_data)


def _write_config(path, data):
    with open(path, '') as file:
        file.write(data)


def write_local_user_meta(users):
    _write_config(LOCAL_CONFIG_USERS,users)


def create_folders():
    os.makedirs(LOCAL_CONFIG_FOLDER, exist_ok=True)
    os.makedirs(ASSIGNMENT_FOLDER, exist_ok=True)
    os.makedirs(GRADE_FOLDER, exist_ok=True)
    os.makedirs(SUBMISSION_FOLDER, exist_ok=True)


def update_local_assignment_meta(assignment):
    as_config_file = ASSIGNMENT_FOLDER + assignment['id']
    if os.path.isfile(as_config_file):
        with open(as_config_file, 'r') as local_file:
            local_as_config = json.load(local_file)
        if local_as_config['timemodified'] < assignment['timemodified']:
            _write_config(as_config_file, assignment)
            return True
    else:
        _write_config(as_config_file, assignment)
        return False


def write_local_submission_meta(assignment):
    s_config_file = SUBMISSION_FOLDER + str(assignment['assignmentid'])
    _write_config(s_config_file, assignment)


def write_local_grade_meta(assignment):
    g_config_file = GRADE_FOLDER + str(assignment['assignmentid'])
    _write_config(g_config_file, assignment)


def needs_work_tree():
    if not in_tree():
        raise SystemExit(1, 'needs work tree')
