# Copyright 2012-2013, University of Amsterdam. This program is free software:
# you can redistribute it and/or modify it under the terms of the GNU Lesser 
# General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License 
# for more details.
# 
# You should have received a copy of the GNU Lesser General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

wpm_dumps = {}
dump_filenames = {
    'translations': 'translations.csv',
    'labels': 'label.csv',
    'pages': 'page.csv'
}


def init_datasource(wpm_languages):
    """Set the datasource and init it"""
    for langcode, langconfig in wpm_languages.iteritems():
        load_wpm_dump(langconfig['source'], langcode, **langconfig['initparams'])

def load_wpm_dump(datasource, langcode, **kwargs):
    importdata = datasource.rsplit('.', 1)
    mod = __import__(importdata[0], fromlist=[importdata[1]])
    class_ = getattr(mod, importdata[1])
    wpm_dumps[langcode] = class_(langcode, **kwargs)


def normalize(raw):
    """Replaces hyphens with spaces, removes accents, lower cases and strips the input text."""
    text = raw
    text = text.replace('-', ' ')
    text = remove_accents(text)
    text = text.lower()
    text = text.strip()
    return text if len(text) else raw


def remove_accents(input_str):
    """Replaces accented characters in the input with their non-accented counterpart."""
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
