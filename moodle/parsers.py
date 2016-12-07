import re

mlang_tags = re.compile(r'\{mlang\s*(\w{2})\}')


def strip_mlang(string, preferred_lang='en'):
    # todo make preferred language configurable
    # creates mlang tuples like ('en', 'eng text')
    # tuple_regex = re.compile(r'(?:\{mlang (\w{2})\}(.+?)\{mlang\})+?', flags=re.S)
    # tuples = tuple_regex.findall(string)

    # creates set with possible languages like {'en', 'de'}
    """
    Strips all {mlang} tags from a string.
    Also strips content between tags except for tags matching preferred_lang.

    :param string: The string, possibly containing mlang tags
    :param preferred_lang: Strip all mlang content extept this, default: en
    :return: stripped text, free of mlang tags, only containing preferred_lang content.
    """
    lang_set = set(mlang_tags.findall(string))

    # if there is more than one language, discard all but preferred_lang
    if len(lang_set) > 1:
        lang_set.discard(preferred_lang)  # removes preferred lang from set, langs in set will be purged
        discard_mlang = '|'.join(lang_set)
        pattern = re.compile(r'((?=\{mlang (' + discard_mlang + r')\})(.*?)\{mlang\})+?', flags=re.S)
        string = pattern.sub('', string)

    # remove remaining mlang tags.
    strip_mlang_tag = re.compile(r'(\s*\{mlang.*?\}\s*)+?')
    return strip_mlang_tag.sub('', string)


parse_args_from_url = re.compile(r'.*pluginfile.php'
                                 r'/(?P<context_id>[0-9]*)'
                                 r'/(?P<component>\w+)'
                                 r'/(?P<file_area>\w+)'
                                 r'/(?P<item_id>[0-9]*).*')


def file_meta_dict_from_url(url):
    match = parse_args_from_url.match(url)
    return match.groupdict()


