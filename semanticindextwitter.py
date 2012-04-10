import os
import sys
import time
import json
import httplib
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
parser.add_option("-p", "--pause", metavar="MINUTES",
                  help="Number of minutes to pause in the loop (default: %default)", type="int", default="30")
parser.add_option("--listlang", 
                  help="list languages that can be recognized",  action="store_true")
parser.add_option("--lm", metavar="DIR",
                  help="language model root (default: %default)", default="LM")
#parser.add_option("--langloc", help="List accepted languages plus location for wikipediaminer dump", nargs=3,
parser.add_option("--langloc", help="Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump", nargs=3,
                  action="append", metavar="LANG LANGCODE LOC")
(options, args) = parser.parse_args()

ngrammodel = textcat.NGram(options.lm)
availablelang = ngrammodel.listLangs()
if options.listlang:
    print sorted(availablelang)
    sys.exit(0)


for lang, langcode, loc in options.langloc:
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

# Helper to compare filenames in gardenhose dump
def addzero(x): 
    parts = x.split('-')
    if parts[1][1] == '.':
        parts[1] = '0' + parts[1]
        return '-'.join(parts)
    else:
         return x
filecmp = lambda x,y: cmp(addzero(x), addzero(y))

def run(dir, file):
    print "Loading tweets from: " + dir + "/" + file + "."
    for line in open(os.path.join(root, dir, file), 'r'):
        try:
            tweet = json.loads(line)
        except ValueError:
            print "Error while loading tweet: " + line
            continue

        if "delete" in tweet:
            print "Deleted tweet, not storing."
            continue
        if not "id" in tweet: assert False, line
        assert "text" in tweet

        lang = ngrammodel.classify(unicode(tweet["text"]).encode('utf-8'))
        if not lang in langmap: 
            print "Tweets of lang " + lang + " will not be stored."
            continue

        langcode = langmap[lang]
        tweet["detectedlang"] = langcode
        tweet["semantic"] = semanticizers[langcode].semanticize(tweet["text"])
        connection.request('POST', '%s%d' % (options.index, tweet["id"], json.dumps(tweet)))
        result = connection.getresponse().read()
        result_json = json.loads(result)

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
        run(dir, file)
        file_index += 1
else:
    for dir in sorted(os.listdir(root)):
        for file in sorted(os.listdir(os.path.join(root, dir)), filecmp):
            run(dir, file)
