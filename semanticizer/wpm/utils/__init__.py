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

import math
import re
import unicodedata
import sys

from .markup_stripper import MarkupStripper 

dump_filenames = {
    'translations': 'translations.csv',
    'stats': 'stats.csv',
    'labels': 'label.csv',
    'pages': 'page.csv',
    'pageLabels': 'pageLabel.csv',
    'pageCategories': 'articleParents.csv',
    'inlinks': 'pageLinkIn.csv',
    'outlinks': 'pageLinkOut.csv'
}


def normalize(raw, dash=True, accents=True, lower=True):
    """Replaces hyphens with spaces, removes accents, lower cases and
    strips the input text.

    All steps, except for the strip(), can be disabled with the
    optional arguments.
    """
    text = raw
    if dash:
        text = text.replace('-', ' ')
    if accents:
        text = remove_accents(text)
    if lower:
        text = text.lower()
    text = text.strip()
    return text if len(text) else raw


def remove_accents(input_str):
    """Replaces accented characters in the input with their
    non-accented counterpart."""
    if isinstance(input_str, str):
        input_unicode = input_str.decode(errors="ignore")
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
    import glob
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
            wiki = glob.glob(fullpath + '*-pages-articles.xml')
            if len(wiki) > 0:
                print "Found " + wiki[0]
            else:
                raise IOError("Cannot find wiki *-pages-articles.xml")
            return fullpath
        else:
            print fullpath + " doesn't exist"
    raise IOError("Cannot find " + path)

def get_relatedness(wpm, artA, artB):
    if artA is artB:
        return 1.0

    linksA = wpm.get_item_inlinks( artA )
    linksB = wpm.get_item_inlinks( artB )
    
    if not linksA or not linksB:
        return 0.0 
    
    intersection = 0
    indexA = 0
    indexB = 0
    
    while indexA < len(linksA) or indexB < len(linksB):
        useA = False
        useB = False

        linkA = None
        linkB = None
        
        if indexA < len(linksA):
            linkA = linksA[indexA]

        if indexB < len(linksB):
            linkB = linksB[indexB]
            
        if linkA and linkB and linkA is linkB:
            useA = True
            useB = True
            intersection += 1
        else:
            if linkA and (not linkB or linkA < linkB):
                useA = True
                if linkA is artB:
                    intersection += 1
            else:
                useB = True
                if linkB is artA:
                    intersection += 1
        
        if useA:
            indexA += 1
        if useB:
            indexB += 1 

    googleMeasure = None

    if intersection is 0:
        googleMeasure = 1.0
    else:
        a = math.log(len(linksA))
        b = math.log(len(linksB))
        ab = math.log(len(intersection))

        googleMeasure = (max(a, b) - ab) / (m - min(a, b))
    
    #normalize
    if not googleMeasure:
        return 0
    if googleMeasure >= 1:
        return 0
    
    return 1 - googleMeasure

def generate_markup_definition(markup):
    stripper = MarkupStripper()

    # strip markup
    markup = re.sub("={2,}(.+)={2,}", "\n", markup) #clear section headings completely - not just formating, but content as well.			
    markup = stripper.strip_all_but_internal_links_and_emphasis(markup) 
    markup = stripper.strip_non_article_internal_links(markup) 
    markup = stripper.strip_excess_newlines(markup) 

    # convert wiki tags to html
    markup = stripper.emphasisResolver.resolve_emphasis(markup) 

    # todo convert links
    #...

    # slice markup to definition
    fp = ""
    pos = 0
    p = re.compile("\n\n", re.DOTALL)
    for m in p.finditer(markup):
        fp = markup[0:pos]
        if (pos > 150): 
            break
        pos = m.start()+2 
    fp = re.sub("\n", " ", fp)
    fp = re.sub("\\s+", " ", fp) #turn all whitespace into spaces, and collapse them.
    fp = fp.strip()

    return fp

def cli_progress(current, total, bar_length=40):
    percent = float(current) / total
    hashes = '#' * int(round(percent * bar_length))
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\rPercent: [{0}] {1}%".format(hashes + spaces, int(round(percent * 100))))
    sys.stdout.flush()