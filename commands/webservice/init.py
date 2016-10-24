def register_subcommand(subparser):
    init_parser = subparser.add_parser(
        'init',
        help='initialize work tree'
    )
    init_parser.add_argument('--uid', dest='user_id')
    init_parser.add_argument('--force', help='overwrite the config', action='store_true')
    init_parser.add_argument('-c', '--courseids', dest='course_ids', nargs='+', help='moodle course id',
                             action='append')
    init_parser.set_defaults(func=init)


def init(url, token, user_id, force=False, course_ids=None):
    """initializes working tree: creates local .mdt/config, with chosen courses"""

    ms = MoodleSession(moodle_url=url, token=token)

    wrapped = wrappers.CourseListResponse(ms.get_users_course_list(user_id))
    courses = list(wrapped)

    courses.sort(key=lambda course: course.full_name)

    saved_data = []
    if course_ids is None or force:
        choices = interaction.input_choices_from_list(courses, '\n  choose courses, seperate with space: ')
        if len(choices) == 0:
            print('nothing chosen.')
            raise SystemExit(0)
        chosen_courses = [courses[c] for c in choices]
        print('using:\n' + ' '.join([str(c) for c in chosen_courses]))
        course_ids = [c.id for c in chosen_courses]
        saved_data = [c for c in wrapped.raw if c['id'] in course_ids]

    try:
        wt = WorkTree(init=True, force=force)
    except FileExistsError:
        print('already initialized')
        raise SystemExit(1)

    wt.courses = saved_data

    wt.write_local_config('courseids = ' + str(course_ids))
    sync(url=url, token=token)

