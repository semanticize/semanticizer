'''
Created on 15 Apr 2013

@author: evert
'''

import codecs
import redis
import unicodedata
import os
import stat
import sys


wpm_dump_filenames = {
    'translations': 'translations.csv',
    'labels': 'label.csv',
    'pages': 'page.csv'
}

rds = redis.StrictRedis(host='localhost', port=6379, db=0)

translation_langs = ['en', 'nl', 'fr', 'es']


def check_dump_path(path):
    """
    Checks whether a path exists and raises an error if it doesn't.

    @param path: The pathname to check
    @raise IOError: If the path doesn't exist or isn't readbale
    """
    pathlist = [os.path.normpath(path) + os.sep,
                os.path.normpath(os.path.abspath(path)) + os.sep]
    for fullpath in pathlist:
        print "Checking " + fullpath
        if os.path.exists(fullpath):
            for _, filename in wpm_dump_filenames.iteritems():
                if os.path.isfile(fullpath + filename) == True:
                    print "Found " + fullpath + filename
                else:
                    raise IOError("Cannot find " + fullpath + filename)
            return fullpath
        else:
            print fullpath + " doesn't exist"
    raise IOError("Cannot find " + path)


def load_wpminer_dump(langname, langcode, path):
    """
    <langcode>:name = language name
    <langcode>:path = wpminer path
    <langcode>:txt:<text> = set(prob, prob, prob, prob [, senseid...])
    <langcode>:txt:<text>:<senseid> = set(prob, prob, bool, bool)
    <langcode>:norm:<text> = list([text, ...])
    <langcode>:trnsl = set([senseid, ...])
    <langcode>:trnsl:<senseid> = list([langcode, ...])
    <langcode>:trnsl:<senseid>:<langcode> = translated title
    <langcode>:titles:<pageid> = title
    <langcode>:ids:<pagetitle> = id
    """
    path = check_dump_path(path)
    rds.set(langcode + ":name", langname)
    rds.set(langcode + ":path", path)
    load_labels(path + wpm_dump_filenames["labels"], langcode)
    load_translations(path + wpm_dump_filenames["translations"], langcode)
    load_page_titles(path + wpm_dump_filenames["pages"], langcode)


def load_labels(filename, prefix):
    """"""
    print 'Loading labels into redis...'
    pipe = rds.pipeline()
    linenr = 0
    labels_file = codecs.open(filename, "r", "utf-8")
    for line in labels_file:
        linenr += 1
        try:
            stats_part, senses_part = line.split(',v{')
            senses = senses_part[:-1].split('s')[1:]
            stats = stats_part[1:].split(',')
            text = stats[0]
            txtkey = prefix + ':txt:' + text
            pipe.rpush(txtkey, *[st for st in stats[1:]])
            for sense_text in senses:
                sense_parts = sense_text[1:-1].split(',')
                pipe.rpush(txtkey, sense_parts[0])
                pipe.rpush(txtkey + ':' + sense_parts[0], *sense_parts[1:])
            normalized = normalize(text)
            pipe.sadd(prefix + ':norm:' + normalized, text)
            pipe.execute()
        except:
            print "Error loading on line " + str(linenr) + ": " + line
            continue
    print 'Done loading labels'
    labels_file.close()


def load_translations(filename, prefix):
    """"""
    print 'Loading translations into redis...'
    pipe = rds.pipeline()
    linenr = 0
    trnsl_file = codecs.open(filename, "r", "utf-8")
    for line in trnsl_file:
        linenr += 1
        try:
            tr_id_str, translation_part = line.strip()[:-1].split(",m{'")
            tr_id = tr_id_str
            parts = translation_part.split(",'")
            pipe.sadd(prefix + ":trnsl", tr_id)
            #self.translation[tr_id] = {}
            for i in range(0, len(parts), 2):
                lang = parts[i]
                if lang in translation_langs:
                    pipe.rpush(prefix + ":trnsl:" + tr_id, lang)
                    pipe.sadd(prefix + ":trnsl:" + tr_id + ":" + lang,
                              parts[i + 1])
            pipe.execute()
        except:
            print "Error loading on line " + str(linenr) + ": " + line
            continue
    trnsl_file.close()
    print 'Done loading translations'


def load_page_titles(filename, prefix):
    """"""
    print 'Loading page titles...'
    pipe = rds.pipeline()
    linenr = 0
    titles_file = codecs.open(filename, "r", "utf-8")
    for line in titles_file:
        linenr += 1
        try:
            splits = line.split(',')
            pageid = splits[0]
            title = splits[1][1:]
            pipe.set(prefix + ":titles:" + pageid, title)
            pipe.set(prefix + ":ids:" + title, pageid)
            pipe.execute()
        except:
            print "Error loading on line " + str(linenr) + ": " + line
            continue
    titles_file.close()
    print 'Done loading pages (%d pages loaded)' % linenr


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
    if type(input_str) is str:
        input_unicode = unicode(input_str, errors="ignore")
    else:
        input_unicode = input_str
    nkfd_form = unicodedata.normalize('NFKD', input_unicode)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print "Usage: %s language_name language_code path_to_wpm_dump" \
               % sys.argv[0]
        sys.exit(1)
    try:
        load_wpminer_dump(sys.argv[1], sys.argv[2], sys.argv[3])
    except IOError as err:
        print err.message
