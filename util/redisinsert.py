'''
Created on 15 Apr 2013

@author: evert
'''

import codecs
import redis
import unicodedata
import os
import stat
import logging


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
    pathlist = [path, os.path.abspath(path)]
    for fullpath in pathlist:
        logging.getLogger().info("Checking " + fullpath)
        if os.path.exists(fullpath) and \
           bool(os.stat(fullpath).st_mode & stat.S_IRUSR):
            for filename in wpm_dump_filenames:
                if os.path.exists(filename):
                    logging.getLogger().info("Found " + fullpath + filename)
                else:
                    logging.getLogger().fatal("Cannot find " + fullpath
                                              + filename + ", exiting")
                    raise IOError("Cannot find " + fullpath + filename)
            return os.path.normpath(fullpath) + os.sep
    raise IOError("Cannot find " + path)


def load_wpminer_dump(langname, langcode, path):
    """"""
    path = check_dump_path(path)
    load_labels(path + wpm_dump_filenames["labels"], langcode)
    load_translations(path + wpm_dump_filenames["translations"], langcode)


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
    for line in codecs.open(filename, "r", "utf-8"):
        linenr += 1
        try:
            tr_id_str, translation_part = line.strip()[:-1].split(",m{'")
            tr_id = int(tr_id_str)
            parts = translation_part.split(",'")
            pipe.sadd(prefix + ":translations", tr_id)
            #self.translation[tr_id] = {}
            for i in range(0, len(parts), 2):
                lang = parts[i]
                if lang in translation_langs:
                    pipe.rpush(prefix + ":translations:" + tr_id, lang)
                    pipe.sadd(prefix + ":translations:" + tr_id + ":" + lang, parts[i + 1])
                    #self.translation[tr_id][parts[i]] = parts[i + 1]
            pipe.execute()
        except:
            print "Error loading on line " + str(linenr) + ": " + line
            continue


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
    load_labels('/Users/evertlammerts/Downloads/zfs/ilps-plexer/wikipediaminer/nlwiki-20111104/label.csv')
