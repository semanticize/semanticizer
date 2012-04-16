import time
import xml2json
import textcat
import sys
import re
import os
import multiprocessing
import nltk
import lxml
import json
import httplib
import glob
import codecs
from time import sleep
from semanticizer import Semanticizer
from optparse import OptionParser
from lxml import objectify

usage = "Usage: %prog [options] <newsfile>"
parser = OptionParser(usage=usage)
parser.add_option("-c", "--connection",
                  help="Connection string (default: %default)", metavar="HOST:PORT", default="localhost:9200")
parser.add_option("-i", "--index",
                  help="URL to find index (default: %default)", default="/semanticnews/news/")
parser.add_option("-v", "--verbose",
                  help="Set high verbosity",  action="store_true")
parser.add_option("--listlang", 
                  help="list languages that can be recognized",  action="store_true")
parser.add_option("--lm", metavar="DIR",
                  help="language model root (default: %default)", default="LM.lrej2011")
parser.add_option("--langloc", help="Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump (default: english en /zfs/ilps-plexer/wikipediaminer/enwiki-20111007/)", nargs=3,
                  action="append", metavar="LANG LANGCODE LOC")
parser.add_option("-s", "--stopword", metavar="DIR",
                  help="Location of the stopword dir (default: %default)", default="SW")
#parser.add_option("-m", "--multi", metavar="NUM", type="int",
#                  help="Number of cores to use (default: %default)", default=1)
(options, args) = parser.parse_args()

ngrammodel = textcat.NGram(options.lm)
availablelang = ngrammodel.listLangs()
if options.listlang:
    print sorted(availablelang)
    sys.exit(0)

if not os.path.isdir(options.stopword):
    parser.error("The stopword dir does not exist")
stopwords = {}

for fname in glob.glob(os.path.join(options.stopword, "stopwords.*")):
    langcode = os.path.split(fname)[-1].split(".")[-1]
    stopwords[langcode] = {}
    for line in codecs.open(fname, 'r', 'utf-8'):
        stopwords[langcode][line.strip()] = 0

if not options.langloc:
    options.langloc = [("english", "en", "/zfs/ilps-plexer/wikipediaminer/enwiki-20111007/")] 

for lang, langcode, loc in options.langloc:
    if not langcode in stopwords:
        parser.error("No stopwords for " + lang)
    if not lang in availablelang:
        parser.error("Language \"" + lang + "\" is not available, available languages are: " + ", ".join(sorted(availablelang)))
    if not os.path.isdir(loc):
        parser.error("Wikipediaminer dump does not exist: " + loc)

if len(args) != 1:
    parser.error("Provide only the newsfile")
if not os.path.exists(args[0]):
    parser.error("The newsfile does not exist.")

filename = args[0]
connection =  httplib.HTTPConnection(options.connection)

langmap = {}
semanticizers = {}
for lang, langcode, loc in options.langloc:
    langmap[lang] = langcode

    print "Loading semanticizer for " + lang + " from " + loc
    start = time.time()
    semanticizers[langcode] = Semanticizer(langcode, loc)
    print "Loading semanticizer took", time.time() - start, "seconds."

rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")

def cleanText(text):
    text = rl.sub(" ", text)
    text = rp.sub(" ", text)
    text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
    return text

def removeStopwords(text, langcode):
    return " ".join([w for w in re.split('\s+', text) if not w in stopwords[langcode]])

raw = codecs.open(filename, 'r').read()
rawasci = unicode(raw, 'utf-8', 'ignore').encode('ascii', 'ignore')
obj = objectify.fromstring(rawasci)

stats = {"total":0}
for lang in langmap:
    stats[langmap[lang]] = 0

jsonob = xml2json.objectJSONEncoder()
for d in obj['vespaadd']['document']:
    jsonrep = json.loads(jsonob.encode(d))
    text = cleanText(unicode(jsonrep['body']))
    lang = ngrammodel.classify(text.encode('utf-8'))
    if not lang in langmap: 
        if options.verbose: print "News of lang " + lang + " will not be stored."
        continue
    langcode = langmap[lang]
    jsonrep["detected_lang"] = langcode
    jsonrep["cleaned_text"] = ""
    semanticdict = {}
    for sentence in nltk.sent_tokenize(jsonrep['body']):
        clean = removeStopwords(cleanText(sentence), langcode)
        jsonrep["cleaned_text"] += clean + ". "
        semantic = semanticizers[langcode].semanticize(clean)
        if "links" in semantic:
            for s in semantic["links"]:
                title = s['title']
                if title in semanticdict:
                    semanticdict[title]['commonness'] += s['commonness']
                    semanticdict[title]['label'] += s['label']
                else:
                    semanticdict[title] = s
    semantics = []
    for title in semanticdict:
        semantics.append(semanticdict[title])

    jsonrep["semantic"] = {"links":semantics}

    connection.request('POST', '%s%s' % (options.index, jsonrep["newsdocid"]), json.dumps(jsonrep))
    stats[langcode] += 1
    result = connection.getresponse().read()
    result_json = json.loads(result)

print stats
