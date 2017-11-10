from collections import Mapping, Sequence, Sized, namedtuple as nt

from moodle.fieldnames import JsonFieldNames as Jn

import logging

log = logging.getLogger('moodle.responses')


class JsonWrapper(Sized):
    def __len__(self):
        return len(self._data)

    def __init__(self, json):
        self._data = json

    @property
    def raw(self): return self._data


class JsonListWrapper(JsonWrapper, Sequence):
    def __getitem__(self, index):
        return self._data[index]

    def __init__(self, json_list):
        if not issubclass(type(json_list), Sequence):
            raise TypeError(f'received type {type(json_list)}, expected Sequence')
        super().__init__(json_list)

    def __iter__(self):
        raise NotImplementedError('__iter__')

    def get(self, index):
        try:
            return self._data[index]
        except Exception as e:
            print(index)
            raise e


class JsonDictWrapper(JsonWrapper, Mapping):
    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        """
            Search for key.
            KeyError will be thrown, if the key cannot be found.
        """
        try:
            return self._data[key]
        except KeyError:
            raise

    def __init__(self, json_dict):
        if not issubclass(type(json_dict), Mapping):
            raise TypeError(f'received type {type(json_dict)}, expected Mapping')
        super().__init__(json_dict)

    __marker = object()

    def get(self, key, default=__marker):
        try:
            return self._data[key]
        except KeyError:
            if default is self.__marker:
                raise
            else:
                return default


class CourseListResponse(JsonListWrapper):
    def __iter__(self):
        for course in self._data:
            yield self.Course(course)

    class Course(JsonDictWrapper):
        """ optional:
               summary string  Optional //summary
                summaryformat int  Optional //summary format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                format string  Optional //course format: weeks, topics, social, site
                showgrades int  Optional //true if grades are shown, otherwise false
                lang string  Optional //forced course language
                enablecompletion int  Optional //true if completion is enabled, otherwise false
        """

        @property
        def id(self): return self[Jn.id]

        @property
        def short_name(self): return self[Jn.short_name]

        @property
        def full_name(self): return self[Jn.full_name]

        @property
        def enrolled_user_count(self): return self[Jn.enrolled_user_count]

        @property
        def id_number(self): return self[Jn.id_number]

        @property
        def visible(self): return self[Jn.visible]

        def __str__(self): return f'{self.full_name[0:39]:40} id:{self.id:5d} short: {self.short_name}'


class EnrolledUsersListResponse(JsonListWrapper):
    """ optional, unimplemented object {
    username string  Optional //Username policy is defined in Moodle security config
    firstname string  Optional lastname string  Optional
    email string  Optional  address string  Optional phone1 string  Optional phone2 string  Optional
    icq string  Optional skype string  Optional yahoo string  Optional aim string  Optional
    msn string  Optional department string  Optional institution string  Optional
    idnumber string  Optional
    interests string  Optional //user interests (separated by commas)
    firstaccess int  Optional //first access to the site (0 if never)
    lastaccess int  Optional //last access to the site (0 if never)
    description string  Optional //User profile description
    descriptionformat int  Optional //description format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
    city string  Optional //Home city of the user
    url string  Optional //URL of the user
    country string  Optional //Home country code of the user, such as AU or CZ
    profileimageurlsmall string  Optional //User image profile URL - small version
    profileimageurl string  Optional //User image profile URL - big version

    customfields  Optional //User custom fields (also known as user profil fields)
        list of ( object {
        type string   //The type of the custom field - text field, checkbox...
        value string   //The value of the custom field
        name string   //The name of the custom field
        shortname string   //The shortname of the custom field - to be able to build the field class in the code})

    preferences  Optional //User preferences
        list of (object {
        name string   //The name of the preferences
        value string   //The value of the custom field })

    enrolledcourses  Optional //Courses where the user is enrolled - limited by which courses the user is able to see
        list of (object {
        id int   //Id of the course
        fullname string   //Fullname of the course
        shortname string   //Shortname of the course})}"""

    def __iter__(self):
        for user in self._data:
            yield self.User(user)

    class User(JsonDictWrapper):
        @property
        def id(self): return self[Jn.id]

        @property
        def full_name(self): return self[Jn.full_name]

        @property
        def groups(self): return self.GroupsList(self.get(Jn.groups, []))

        @property
        def roles(self): return self.RolesList(self.get(Jn.roles, []))

        class GroupsList(JsonListWrapper):
            def __iter__(self):
                for group in self._data:
                    yield self.Group(group)

            class Group(JsonDictWrapper):
                @property
                def id(self): return self[Jn.id]

                @property
                def name(self): return self[Jn.name]

                @property
                def description(self): return self[Jn.description]

                @property  # description format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN
                def description_format(self): return self[Jn.description_format]

        class RolesList(JsonListWrapper):
            def __iter__(self):
                for role in self._data:
                    yield self.Role(role)

            class Role(JsonDictWrapper):
                @property
                def role_id(self): return self[Jn.role_id]

                @property
                def name(self): return self[Jn.name]

                @property
                def short_name(self): return self[Jn.short_name]

                @property
                def sort_order(self): return self[Jn.sort_order]


class CourseAssignmentResponse(JsonDictWrapper):
    @property
    def warnings(self): return self.WarningList(self[Jn.warnings])

    @property
    def courses(self): return self.CourseList(self[Jn.courses])

    class WarningList(JsonListWrapper):
        def __iter__(self):
            for warning in self._data:
                yield self.Warning(warning)

        class Warning(JsonDictWrapper):
            """    item string  Optional //item can be 'course' (errorcode 1 or 2) or 'module' (errorcode 1)
            itemid int  Optional //When item is a course then itemid is a course id.
                                    When the item is a module then itemid is a module id
            warningcode string   //errorcode can be 1 (no access rights) or 2 (not enrolled or no permissions)
            message string   //untranslated english message to explain the warning})}"""

            @property
            def warning_code(self): return self[Jn.warning_code]

            @property
            def message(self): return self[Jn.message]

    class CourseList(JsonListWrapper):
        def __iter__(self):
            for course in self._data:
                yield self.Course(course)

        class Course(JsonDictWrapper):
            @property
            def id(self): return self[Jn.id]

            @property
            def short_name(self): return self[Jn.short_name]

            @property
            def full_name(self): return self[Jn.full_name]

            @property
            def time_modified(self): return self[Jn.time_modified]

            @property
            def assignments(self): return self.AssignmentList(self[Jn.assignments])

            class AssignmentList(JsonListWrapper):
                def __iter__(self):  # CourseAssignmentListResponse
                    for assignment in self._data:
                        yield self.Assignment(assignment)

                class Assignment(JsonDictWrapper):
                    """ unimplemented fields:
                    nosubmissions int   //no submissions
                    submissiondrafts int   //submissions drafts
                    sendnotifications int   //send notifications
                    sendlatenotifications int   //send notifications
                    sendstudentnotifications int   //send student notifications (default)
                    allowsubmissionsfromdate int   //allow submissions from date
                    timemodified int   //last time assignment was modified
                    completionsubmit int   //if enabled, set activity as complete following submission
                    cutoffdate int   //date after which submission is not accepted without an extension
                    requireallteammemberssubmit int   //if enabled, all team members must submit
                    teamsubmissiongroupingid int   //the grouping id for the team submission groups
                    blindmarking int   //if enabled, hide identities until reveal identities actioned
                    revealidentities int   //show identities for a blind marking assignment
                    attemptreopenmethod string   //method used to control opening new attempts
                    maxattempts int   //maximum number of attempts allowed
                    markingworkflow int   //enable marking workflow
                    markingallocation int   //enable marking allocation
                    requiresubmissionstatement int   //student must accept submission statement

                    configs   //configuration settings
                    list of ( object {   //assignment configuration object

                    intro string  Optional //assignment intro, not allways returned
                                            because it deppends on the activity configuration
                    introformat int  Optional //intro format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                    introattachments  Optional //intro attachments files
                    list of ( object {
                        filename string   //file name
                        mimetype string   //mime type
                        fileurl string   //file download url})})})"""

                    @property
                    def id(self): return self[Jn.id]

                    @property
                    def course_id(self): return self[Jn.course]

                    @property
                    def time_modified(self): return self[Jn.time_modified]

                    @property
                    def is_team_submission(self): return 1 == self[Jn.team_submission]

                    @property
                    def name(self): return self[Jn.name]

                    @property  # documentation states, this would be the grade 'type'. Go figure?
                    def max_points(self): return self[Jn.grade]

                    @property
                    def due_date(self): return self[Jn.due_date]

                    @property
                    def course_module_id(self): return self[Jn.course_module_id]

                    @property
                    def configurations(self): return self.AssignmentConfigList(self[Jn.configs])

                    class AssignmentConfigList(JsonListWrapper):
                        def __iter__(self):
                            for config in self._data:
                                yield self.AssignmentConfig(config)

                        class AssignmentConfig(JsonDictWrapper):
                            @property
                            def id(self): return self[Jn.id]

                            @property
                            def assignment_id(self): return self[Jn.assignment]

                            @property
                            def name(self): return self[Jn.name]

                            @property
                            def plugin(self): return self[Jn.plugin]

                            @property
                            def sub_type(self): return self[Jn.sub_type]

                            @property
                            def value(self): return self[Jn.value]


class AssignmentSubmissionResponse(JsonDictWrapper):
    def print_warnings(self):
        for warning in self.warnings:
            if warning.warning_code == "3":
                # no (new) submissions, can ignore
                pass
            else:
                log.warning(f'{warning.warning_code}: {warning.message}')

    @property
    def warnings(self): return self.WarningList(self[Jn.warnings])

    @property
    def assignments(self): return self.AssignmentList(self[Jn.assignments])

    class WarningList(JsonListWrapper):
        def __iter__(self):
            for warning in self._data:
                yield self.Warning(warning)

        class Warning(JsonDictWrapper):
            """
            item string  Optional //item
            itemid int  Optional //item id
            warningcode string   //the warning code can be used by the client app to implement specific behaviour
            message string   //untranslated english message to explain the warning})}
            """
            @property
            def warning_code(self): return self[Jn.warning_code]

            @property
            def message(self): return self[Jn.message]

    class AssignmentList(JsonListWrapper):

        def __iter__(self):
            for assignment in self._data:
                yield self.Assignment(assignment)

        class Assignment(JsonDictWrapper):
            @property
            def id(self):
                return self[Jn.assignment_id]

            @property
            def submissions(self): return self.SubmissionList(self[Jn.submissions])

            class SubmissionList(JsonListWrapper):
                def __iter__(self):
                    for submission in self._data:
                        yield self.Submission(submission)

                class Submission(JsonDictWrapper):
                    @property
                    def id(self): return self[Jn.id]

                    @property
                    def user_id(self): return self[Jn.user_id]

                    @property
                    def group_id(self): return self[Jn.group_id]

                    @property
                    def time_modified(self): return self[Jn.time_modified]

                    @property
                    def time_created(self): return self[Jn.time_created]

                    @property
                    def status(self): return self[Jn.status]

                    @property
                    def attempt_number(self): return self[Jn.attempt_number]

                    @property
                    def plugin_list(self): return self.PluginList(self.get(Jn.plugins, []))

                    class PluginList(JsonListWrapper):
                        def __iter__(self):
                            for plugin in self._data:
                                yield self.Plugin(plugin)

                        class Plugin(JsonDictWrapper):
                            @property
                            def type(self): return self[Jn.type]

                            @property
                            def name(self): return self[Jn.name]

                            @property
                            def editor_fields(self): return self.EditorFieldList(self.get(Jn.editor_fields, []))

                            @property
                            def file_areas(self): return self.FileAreaList(self.get(Jn.file_areas, []))

                            class FileAreaList(JsonListWrapper):
                                def __iter__(self):
                                    for file_area in self._data:
                                        yield self.FileArea(file_area)

                                class FileArea(JsonDictWrapper):
                                    @property
                                    def area(self): return self[Jn.area]

                                    @property
                                    def file_list(self): return self.FileList(self.get(Jn.files, []))

                                    class FileList(JsonListWrapper):
                                        def __iter__(self):
                                            for file in self._data:
                                                yield self.File(file)

                                        class File(JsonDictWrapper):
                                            @property
                                            def file_path(self): return self[Jn.file_path]

                                            @property
                                            def file_name(self): return self[Jn.file_name]

                                            @property
                                            def file_size(self): return self[Jn.file_size]

                                            @property
                                            def mime_type(self): return self[Jn.mime_type]

                                            @property
                                            def time_modified(self): return self[Jn.time_modified]

                                            @property
                                            def url(self): return self[Jn.file_url]

                            class EditorFieldList(JsonListWrapper):
                                def __iter__(self):
                                    for field in self._data:
                                        yield self.EditorField(field)

                                class EditorField(JsonDictWrapper):
                                    @property
                                    def name(self): return self[Jn.name]

                                    @property
                                    def description(self): return self[Jn.description]

                                    @property
                                    def text(self): return self[Jn.text]

                                    @property  # text format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                                    def fmt(self): return self[Jn.format]


class AssignmentGradeResponse(JsonDictWrapper):
    def print_warnings(self):
        for warning in self.warnings:
            if warning.warning_code == "3":
                # grades empty, no warning necessary
                pass
            elif warning.warning_code == "1":
                log.warning(f'{warning.item_id:5d}: {warning.message}')

    @property
    def assignments(self): return self.AssignmentList(self[Jn.assignments])

    @property
    def warnings(self): return self.WarningList(self.get(Jn.warnings, []))

    class AssignmentList(JsonListWrapper):

        def __iter__(self):
            for assignment in self._data:
                yield self.Assignment(assignment)

        class Assignment(JsonDictWrapper):
            @property
            def id(self): return self[Jn.assignment_id]

            @property
            def grades(self): return self.GradesList(self[Jn.grades])

            class GradesList(JsonListWrapper):
                def __iter__(self):
                    for grade in self._data:
                        yield self.Grade(grade)

                class Grade(JsonDictWrapper):
                    @property
                    def id(self): return self[Jn.id]

                    @property  # string!
                    def grade(self): return self[Jn.grade]

                    @property
                    def grader_id(self): return self[Jn.grader]

                    @property
                    def user_id(self): return self[Jn.user_id]

                    @property
                    def attempt_number(self): return self[Jn.attempt_number]

                    @property
                    def time_created(self): return self[Jn.time_created]

                    @property
                    def time_modified(self): return self[Jn.time_modified]

                    @property
                    def assignment(self): return self.get(Jn.assignment, -1)

    class WarningList(JsonListWrapper):
        def __iter__(self):
            for warning in self._data:
                yield self.Warning(warning)

        class Warning(JsonDictWrapper):
            """
            item string  Optional //item is always 'assignment'
            itemid int  Optional //when errorcode is 3 then itemid is an assignment id.
                        When errorcode is 1, itemid is a course module id
            warningcode string   //errorcode can be 3 (no grades found) or 1 (no permission to get grades)
            message string   //untranslated english message to explain the warning"""

            @property
            def warning_code(self): return self[Jn.warning_code]

            @property
            def message(self): return self[Jn.message]

            @property
            def item_id(self): return self.get(Jn.item_id, -1)

            @property
            def item(self): return self.get(Jn.item, '')


class FileMetaDataResponse(JsonDictWrapper):
    @property
    def parents(self): return self.ParentList(self[Jn.parents])

    @property
    def files(self): return self.FileList(self[Jn.files])

    class ParentList(JsonListWrapper):
        def __iter__(self):
            for parent in self._data:
                yield self.Parent(parent)

        class Parent(JsonDictWrapper):
            @property
            def context_id(self): return self[Jn.context_id]

            @property
            def component(self): return self[Jn.component]

            @property
            def file_area(self): return self[Jn.file_area]

            @property
            def item_id(self): return self[Jn.item_id]

            @property
            def file_path(self): return self[Jn.file_path]

            @property
            def filename(self): return self[Jn.file_name]

    class FileList(JsonListWrapper):
        def __iter__(self):
            for file in self._data:
                yield self.File(file)

        class File(JsonDictWrapper):
            @property
            def context_id(self): return self[Jn.context_id]

            @property
            def component(self): return self[Jn.component]

            @property
            def file_area(self): return self[Jn.file_area]

            @property
            def item_id(self): return self[Jn.item_id]

            @property
            def file_path(self): return self[Jn.file_path]

            @property
            def filename(self): return self[Jn.file_name]

            @property
            def isdir(self): return 1 == self[Jn.is_dir]

            @property
            def url(self): return self[Jn.url]

            @property
            def time_modified(self): return self[Jn.time_modified]

            @property
            def time_created(self): return self.get(Jn.time_created, 0)

            @property
            def file_size(self): return self.get(Jn.file_size, -1)

            @property
            def author(self): return self.get(Jn.author, "")

            @property
            def license(self): return self.get(Jn.license, "")


class CourseContentResponse(JsonListWrapper):
    def __iter__(self):
        for section in self._data:
            yield self.CourseSection(section)

    class CourseSection(JsonDictWrapper):
        @property
        def id(self): return self[Jn.id]

        @property
        def name(self): return self[Jn.name]

        @property
        def visible(self): return self.get(Jn.visible, -1)

        @property
        def summary(self): return self[Jn.summary]

        @property
        def summary_format(self): return self[Jn.summary_format]

        @property
        def modules(self): return self.ModuleList(self[Jn.modules])

        class ModuleList(JsonListWrapper):
            def __iter__(self):
                for module in self._data:
                    yield self.Module(module)

            class Module(JsonDictWrapper):
                """ unimplemented, moodle calls these activity.
                url string  Optional //activity url
                instance int  Optional //instance id
                description string  Optional //activity description
                visible int  Optional //is the module visible
                availability string  Optional //module availability settings
                """
                @property
                def id(self): return self[Jn.id]

                @property
                def instance(self):
                    """ the instance id """
                    return self.get(Jn.instance, -1)

                @property
                def name(self): return self[Jn.name]

                @property
                def modname(self):
                    """activity module type"""
                    return self[Jn.modname]

                @property
                def modicon(self): return self[Jn.modicon]

                @property
                def modplural(self): return self[Jn.modplural]

                @property
                def indent(self): return self[Jn.indent]

                @property
                def contents(self):
                    """is not marked as optional, but is only in modname == 'folder'"""
                    return self.ContentList(self.get(Jn.contents, []))

                class ContentList(JsonListWrapper):
                    def __iter__(self):
                        for content in self._data:
                            yield self.Content(content)

                    class Content(JsonDictWrapper):
                        """
                        fileurl string  Optional //downloadable file url
                        content string  Optional //Raw content, will be used when type is content
                        """
                        @property
                        def type(self): return self[Jn.type]

                        @property
                        def filename(self): return self[Jn.file_name]

                        @property
                        def file_path(self): return self[Jn.file_path]

                        @property
                        def file_size(self): return self[Jn.file_size]

                        @property
                        def time_modified(self): return self[Jn.time_modified]

                        @property
                        def time_created(self): return self[Jn.time_created]

                        @property
                        def author(self): return self[Jn.author]

                        @property
                        def license(self): return self[Jn.license]

                        @property
                        def user_id(self): return self[Jn.user_id]

                        @property
                        def sort_order(self): return 1 == self[Jn.sort_order]

                        @property
                        def url(self): return self[Jn.url]


class FileUploadResponse(JsonListWrapper):
    def __iter__(self):
        for file in self._data:
            yield self.FileResponse(file)

    def __init__(self, json_list):
        super().__init__(json_list)
        self._errors = []
        for item in json_list:
            if 'error' in item:
                self._data.remove(item)
                self._errors.append(item)

    @property
    def has_errors(self):
        return len(self._errors) > 0

    @property
    def errors(self):
        return self.ErrorList(self._errors)

    class FileResponse(JsonDictWrapper):
        """ unimplemented:
        "component":"user",
        "contextid":1591,
        "userid":"358",
        "filearea":"draft",
        "filename":"hurr.pdf",
        "filepath":"\/",
        "itemid":528004240,
        "license":"allrightsreserved",
        "author":"rawr",
        "source":""
        """
        @property
        def item_id(self): return self['itemid']

    class ErrorList(JsonListWrapper):
        def __iter__(self):
            for error in self._data:
                yield self.Error(error)

        class Error(JsonDictWrapper):
            def __str__(self):
                return f'file: {self.file_name}, path: {self.file_path}, type {self.error_type}, error {self.error}'

            @property
            def file_name(self): return self['filename']

            @property
            def file_path(self): return self['filepath']

            @property
            def error_type(self): return self['errortype']

            @property
            def error(self): return self['error']


MoodleAssignment = CourseAssignmentResponse.CourseList.Course.AssignmentList.Assignment
MoodleCourse = CourseListResponse.Course
MoodleUser = EnrolledUsersListResponse.User
MoodleGroup = EnrolledUsersListResponse.User.GroupsList.Group
MoodleSubmissionList = AssignmentSubmissionResponse.AssignmentList.Assignment.SubmissionList
MoodleSubmission = MoodleSubmissionList.Submission
MoodlePlugin = MoodleSubmission.PluginList.Plugin
MoodleFileArea = MoodlePlugin.FileAreaList.FileArea
MoodleEditorField = MoodlePlugin.EditorFieldList.EditorField
MoodleSubmissionFile = MoodleFileArea.FileList.File
MoodleGradeList = AssignmentGradeResponse.AssignmentList.Assignment.GradesList
MoodleGrade = MoodleGradeList.Grade
MoodleFileMeta = FileMetaDataResponse.FileList.File
