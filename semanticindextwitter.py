import os
import sys
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
parser.add_option("-l", "--loop",
                  help="Loop, with a pause",  action="store_true")
parser.add_option("-p", "--pause", metavar="MINUTES",
                  help="Number of minutes to pause in the loop (default: %default)", type="int", default="30")
parser.add_option("--listlang", 
                  help="list languages that can be recognized",  action="store_true")
parser.add_option("--lm", metavar="DIR",
                  help="language model root (default: %default)", default="LM")

(options, args) = parser.parse_args()

ngrammodel = textcat.NGram(options.lm)
availablelang = ngrammodel.listLangs()
if options.listlang:
    print sorted(availablelang)
    sys.exit(0)

if len(args) != 1:
    parser.error("provide (only) the tweetdir-root directory please, eg: /zfs/ilps-plexer/twitter-data/data/2012")

root = args[0]
connection =  httplib.HTTPConnection(options.connection)
semanticizer = Semanticizer()

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
    print "Loading tweets from: " + dir + "/" + file
    for line in open(os.path.join(root, dir, file), 'r'):
        try:
            tweet = json.loads(line)
        except ValueError:
            print "Error in tweet: " + line
            continue

        if "delete" in tweet: continue
        if not "id" in tweet: assert False, line
        assert "text" in tweet
        tweet["semantic"] = semanticizer.semanticize(tweet["text"])
        connection.request('POST', '/semantictwitter/tweet/%d' % tweet["id"], json.dumps(tweet))
        result = connection.getresponse().read()
        result_json = json.loads(result)
        if "ok" in result_json or not result_json["ok"]:
            print result

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
