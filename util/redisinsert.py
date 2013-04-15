'''
Created on 15 Apr 2013

@author: evert
'''

import codecs
import redis
import unicodedata


def load_labels(filename):
    """"""
    print 'Loading labels...'
    rds = redis.StrictRedis(host='localhost', port=6379, db=0)
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
            txtkey = 'txt:' + text
            pipe.rpush(txtkey, *[stat for stat in stats[1:]])
            for sense_text in senses:
                sense_parts = sense_text[1:-1].split(',')
                pipe.rpush(txtkey, sense_parts[0])
                pipe.rpush(txtkey + ':' + sense_parts[0], *sense_parts[1:])
            normalized = normalize(text)
            pipe.sadd('norm:' + normalized, text)
            pipe.execute()
        except:
            print "Error loading on line " + str(linenr) + ": " + line
            continue
    print 'Done loading labels'
    labels_file.close()


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
