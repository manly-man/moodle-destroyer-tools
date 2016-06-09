import re


def strip_mlang(string, preferred_lang='en'):
    # todo make preferred language configurable
    # creates mlang tuples like ('en', 'eng text')
    # tuple_regex = re.compile(r'(?:\{mlang (\w{2})\}(.+?)\{mlang\})+?', flags=re.S)
    # tuples = tuple_regex.findall(string)

    # creates set with possible languages like {'en', 'de'}
    lang_regex = re.compile(r'\{mlang\s*(\w{2})\}')
    lang_set = set(lang_regex.findall(string))

    if len(lang_set) > 1:
        lang_set.discard(preferred_lang)  # removes preferred lang from set, langs in set will be purged
        discard_mlang = '|'.join(lang_set)
        pattern = re.compile(r'((?=\{mlang ('+discard_mlang+r')\})(.*?)\{mlang\})+?', flags=re.S)
        string = pattern.sub('', string)

    strip_mlang = re.compile(r'(\s*\{mlang.*?\}\s*)+?')
    return strip_mlang.sub('', string)

