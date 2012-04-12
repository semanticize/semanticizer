import os
import sys
import time
import json
import re
import httplib
import glob
import codecs
from time import sleep
from optparse import OptionParser
from semanticizer import Semanticizer
import textcat

usage = "Usage: %prog [options] <tweetdir-root>"
parser = OptionParser(usage=usage)
parser.add_option("-c", "--connection",
                  help="Connection string (default: %default)", metavar="HOST:PORT", default="localhost:9200")
parser.add_option("-i", "--index",
                  help="URL to find index (default: %default)", default="/semantictwitter/tweet/")
parser.add_option("-l", "--loop",
                  help="Loop, with a pause",  action="store_true")
parser.add_option("-v", "--verbose",
                  help="Set high verbosity",  action="store_true")
parser.add_option("-d", "--delete",
                  help="Delete json file after processing",  action="store_true")
parser.add_option("-p", "--pause", metavar="MINUTES",
                  help="Number of minutes to pause in the loop (default: %default)", type="int", default="30")
parser.add_option("--listlang", 
                  help="list languages that can be recognized",  action="store_true")
parser.add_option("--lm", metavar="DIR",
                  help="language model root (default: %default)", default="LM.lrej2011")
parser.add_option("--langloc", help="Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump", nargs=3,
                  action="append", metavar="LANG LANGCODE LOC")
parser.add_option("-s", "--stopword", metavar="DIR",
                  help="Location of the stopword dir (default: %default)", default="SW")
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

for lang, langcode, loc in options.langloc:
    if not langcode in stopwords:
        parser.error("No stopwords for " + lang)
    if not lang in availablelang:
        parser.error("Language \"" + lang + "\" is not available, available languages are: " + ", ".join(sorted(availablelang)))
    if not os.path.isdir(loc):
        parser.error("Wikipediaminer dump does not exist: " + loc)

if len(args) != 1:
    parser.error("Provide (only) the tweetdir-root directory please, eg: /zfs/ilps-plexer/twitter-data/data/2012")
if not os.path.isdir(args[0]):
    parser.error("The tweetdir-root directory does not exist.")

root = args[0]
connection =  httplib.HTTPConnection(options.connection)

langmap = {}
semanticizers = {}
for lang, langcode, loc in options.langloc:
    langmap[lang] = langcode

    print "Loading semanticizer for " + lang + " from " + loc
    start = time.time()
    semanticizers[langcode] = Semanticizer(langcode, loc)
    print "Loading semanticizer took", time.time() - start, "seconds."

def addzero(x): 
    parts = x.split('-')
    if parts[1][1] == '.':
        parts[1] = '0' + parts[1]
        return '-'.join(parts)
    else:
         return x
filecmp = lambda x,y: cmp(addzero(x), addzero(y))

ru = re.compile(r"(@\w+)")
rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")
rt = re.compile(r"(\bRT\b)")

def cleanText(text):
    text = ru.sub(" ", text)
    text = rl.sub(" ", text)
    text = rp.sub(" ", text)
    text = rt.sub(" ", text)
    text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
    return text

def removeStopwords(text, langcode):
    return " ".join([w for w in re.split('\s+', text) if not w in stopwords[langcode]])

def run(file):
    stats = {"total":0}
    for lang in langmap:
        stats[langmap[lang]] = 0
    print "Loading tweets from:", file
    for line in open(file, 'r'):
        stats["total"]+=1
        try:
            tweet = json.loads(line)
        except ValueError:
            if options.verbose: print "Error while loading tweet: " + line
            continue

        if "delete" in tweet:
            if options.verbose: print "Deleted tweet, not storing."
            continue

        assert "id" in tweet, line
        assert "text" in tweet, line

        text = cleanText(unicode(tweet["text"]))
        lang = ngrammodel.classify(text.encode('utf-8'))
        if not lang in langmap: 
            if options.verbose: print "Tweets of lang " + lang + " will not be stored."
            continue
        langcode = langmap[lang]
        text = removeStopwords(text, langcode)
        tweet["detected_lang"] = langcode
        tweet["cleaned_text"] = text
        tweet["semantic"] = semanticizers[langcode].semanticize(text)
        connection.request('POST', '%s%d' % (options.index, tweet["id"]), json.dumps(tweet))
        stats[langcode] += 1
        result = connection.getresponse().read()
        result_json = json.loads(result)
    if options.delete:
        print "Deleting file: " + dir + "/" + file
        os.remove(os.path.join(root, dir, file))
    return stats

if options.loop:
    dir_index = 0
    file_index = 0
    while True:
        dirs = sorted(os.listdir(root))
        assert dir_index < len(dirs)
        dir = dirs[dir_index]
        files = sorted(os.listdir(os.path.join(root, dir)), filecmp)
        if file_index == (len(files)-1) and dir_index == (len(files)-1):
            # The last file of the last dir
            print("At last file, so sleeping for 30 minutes.")
            sleep(options.pause*60)
            continue
        if file_index >= len(files):
            if dir_index < (len(dirs)-1):
                # Go to next dir
                dir_index += 1
                file_index = 0
                continue
            else:
                print("I should be here, so sleeping for 30 minutes.")
                sleep(options.pause*60)
                continue
        file = files[file_index]
        fullname = os.path.join(root, dir, file)
        stats = run(fullname)
        file_index += 1
else:
    totalstats = {}
    for dir in sorted(os.listdir(root)):
        for file in sorted(os.listdir(os.path.join(root, dir)), filecmp):
            fullname = os.path.join(root, dir, file)
            stats = run(fullname)
            for k in stats:
                if not k in totalstats:
                    totalstats[k] = 0
                totalstats[k] += stats[k]
            print "file:", stats
            print "cum:", totalstats
