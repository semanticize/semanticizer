wpm_dumps = {}
dump_filenames = {
    'translations': 'translations.csv',
    'labels': 'label.csv',
    'pages': 'page.csv'
}


def load_wpm_dump(datasource, langcode, **kwargs):
    importdata = datasource.rsplit('.', 1)
    mod = __import__(importdata[0], fromlist=[importdata[1]])
    class_ = getattr(mod, importdata[1])
    wpm_dumps[langcode] = class_(langcode, **kwargs)


def normalize(raw):
    """"""
    text = raw
    text = text.replace('-', ' ')
    text = remove_accents(text)
    text = text.lower()
    text = text.strip()
    return text if len(text) else raw


def remove_accents(input_str):
    """"""
    import unicodedata
    if type(input_str) is str:
        input_unicode = unicode(input_str, errors="ignore")
    else:
        input_unicode = input_str
    nkfd_form = unicodedata.normalize('NFKD', input_unicode)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])


def check_dump_path(path):
    """
    Checks whether a path exists and raises an error if it doesn't.

    @param path: The pathname to check
    @raise IOError: If the path doesn't exist or isn't readbale
    """
    import os
    pathlist = [os.path.normpath(path) + os.sep,
                os.path.normpath(os.path.abspath(path)) + os.sep]
    for fullpath in pathlist:
        print "Checking " + fullpath
        if os.path.exists(fullpath):
            for _, filename in dump_filenames.iteritems():
                if os.path.isfile(fullpath + filename) == True:
                    print "Found " + fullpath + filename
                else:
                    raise IOError("Cannot find " + fullpath + filename)
            return fullpath
        else:
            print fullpath + " doesn't exist"
    raise IOError("Cannot find " + path)