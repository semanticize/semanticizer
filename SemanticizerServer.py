import os
import sys
import time
import json
import re
import httplib
import glob
import codecs
# import multiprocessing
# from time import sleep
from optparse import OptionParser
from semanticizer import Semanticizer
import textcat

usage = "Usage: %prog [options]"
parser = OptionParser(usage=usage)
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
parser.add_option("-p", "--port", metavar="NUM", type="int",
                   help="Port number to start services (counting upwards) (default: %default)", default=8005)
# parser.add_option("-m", "--multi", metavar="NUM", type="int",
#                   help="Number of cores to use (default: %default)", default=1)
parser.add_option("--log", metavar="FILE", help="Log file location (default: %default)", default="log.txt")
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

# All settings are OK

langmap = {}
semanticizers = {}

# Set up services

from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

class SemanticizerProtocol(Protocol):
    def dataReceived(self, data):
        semanticizer = self.factory.semanticizer
        response = semanticizer.semanticize(data)
        self.transport.write(json.dumps(response))
        self.transport.loseConnection()
        
class SemanticizerFactory(Factory):
    protocol = SemanticizerProtocol
    
    def __init__(self, lang, langcode, loc):
        self.lang = lang
        self.langcode = langcode
        self.loc = loc

    def startFactory(self):
        print "Loading semanticizer for " + self.lang + " from " + self.loc
        start = time.time()
        self.semanticizer = Semanticizer(self.langcode, self.loc)
        print "Loading semanticizer took", time.time() - start, "seconds."

class StopwordProtocol(Protocol):
    def dataReceived(self, text):
        text = " ".join([w for w in re.split('\s+', text) if not w in stopwords[langcode]])
        self.transport.write(json.dumps({"cleaned_text": text}))
        self.transport.loseConnection()

class StopwordFactory(Factory):
    protocol = StopwordProtocol
    
    def __init__(self, langcode):
        self.langcode = langcode

class CleanTweetProtocol(Protocol):
    def dataReceived(self, text):
        text = self.factory.ru.sub(" ", text)
        text = self.factory.rl.sub(" ", text)
        text = self.factory.rp.sub(" ", text)
        text = self.factory.rt.sub(" ", text)
        text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
        self.transport.write(json.dumps({"cleaned_text": text}))
        self.transport.loseConnection()
        
class CleanTweetFactory(Factory):
    protocol = CleanTweetProtocol
    
    # RegEx for CleanTweet
    ru = re.compile(r"(@\w+)")
    rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
    rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")
    rt = re.compile(r"(\bRT\b)")

class TextcatProtocol(Protocol):
    def dataReceived(self, data):
#         lang = ngrammodel.classify(data.encode('utf-8'))
        lang = ngrammodel.classify(data)
        self.transport.write(json.dumps({"language": lang}))
        self.transport.loseConnection()

class TextcatFactory(Factory):
    protocol = TextcatProtocol

service_overview = {}
class OverviewProtocol(Protocol):
    def dataReceived(self, data):
        global service_overview
        self.transport.write(json.dumps(service_overview))
        self.transport.loseConnection()
        
class OverviewFactory(Factory):
    protocol = OverviewProtocol

port = options.port

def new_server_endpoint(factory, description):
    global port
    global service_overview
    
    print "Will start %s on port %d" % (description, port)
    service_overview[description] = port
    endpoint = TCP4ServerEndpoint(reactor, port)
    endpoint.listen(factory)
    port += 1
        
if __name__ == '__main__':
    new_server_endpoint(OverviewFactory(), "Overview service")
    new_server_endpoint(TextcatFactory(), "Textcat language detection")
    new_server_endpoint(CleanTweetFactory(), "Tweet Cleaning")

    for lang, langcode, loc in options.langloc:
        langmap[lang] = langcode
        new_server_endpoint(SemanticizerFactory(lang, langcode, loc), "Semanticizer for " + lang)
        new_server_endpoint(StopwordFactory(langcode), "Stopword removal for " + lang)

    print "Running services."
    reactor.run()