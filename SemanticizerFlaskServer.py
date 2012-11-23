import os
import sys
import time
import json
import re
import httplib
import glob
import codecs
from optparse import OptionParser

import textcat

import LinksProcessors

usage = "Usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option("-v", "--verbose",
                  help="Set high verbosity",  action="store_true")
parser.add_option("-f", "--features",
                  help="Include features",  action="store_true")
parser.add_option("--listlang", 
                  help="list languages that can be recognized",  action="store_true")
parser.add_option("--lm", metavar="DIR",
                  help="language model root (default: %default)", default="LM.lrej2011")
parser.add_option("--langloc", help="Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump (default: english en /zfs/ilps-plexer/wikipediaminer/enwiki-20111007/)", nargs=3,
                  action="append", metavar="LANG LANGCODE LOC")
parser.add_option("-s", "--stopword", metavar="DIR",
                  help="Location of the stopword dir (default: %default)", default="SW") 
parser.add_option("-a", "--article", metavar="URL",
                  help="Location article webservices (default: %default)", 
                  default="http://zookst13.science.uva.nl:8080/dutchsemcor/article")
parser.add_option("-l", "--learn", metavar="URL",
                  help="Location scikit-learn webservices (default: %default)", 
                  default="http://fietstas.science.uva.nl:5001")
parser.add_option("--scikit",
                  help="Run own version of scikit",  action="store_true")
parser.add_option("-p", "--port", metavar="NUM", type="int",
                   help="Port number to start services (counting upwards) (default: %default)", default=5000)
parser.add_option("-t", "--threads", metavar="NUM", type="int",
                   help="Number of threads to use (default: %default)", default=16)
# parser.add_option("-m", "--multi", metavar="NUM", type="int",
#                   help="Number of cores to use (default: %default)", default=1)
parser.add_option("--log", metavar="FILE", help="Log file location (default: %default)", default="log.txt")
(options, args) = parser.parse_args()

from flask import Flask, Response, request, abort
app = Flask(__name__)
# Debug mode is not exactly the same as verbose.
if options.verbose: app.debug = True
app.debug_log_format = '[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s'
import logging
from logging.handlers import TimedRotatingFileHandler
file_handler = TimedRotatingFileHandler("logs/log", when='midnight')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s'))
app.logger.addHandler(file_handler)

app.logger.info("Loading ngram model")
ngrammodel = textcat.NGram(options.lm)
availablelang = ngrammodel.listLangs()
if options.listlang:
    print sorted(availablelang)
    sys.exit(0)

app.logger.info("Loading stopwords")
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

pipeline = []

@app.route("/semanticize/<langcode>", methods=["GET", "POST"])
def semanticize(langcode):
    app.logger.debug("Semanticizing: start")
    text = get_text_from_request()
    app.logger.debug("Semanticizing text: " + text)
    links = []
    settings = {"langcode": langcode}
    for key, value in request.args.iteritems():
        assert key not in settings
        settings[key] = value

    for function in ("preprocess", "process", "postprocess"):
        for step, processor in pipeline:
            app.logger.debug("Semanticizing: %s for step %s" % (function, step))
            (links, text, settings) = getattr(processor, function)(links, text, settings)
        app.logger.debug("Semanticizing: %s pipeline with %d steps done" % (function, len(pipeline)))

    return json.dumps({"links": links, "text": text}, indent=4)
        
@app.route("/stopwords/<langcode>", methods=["GET", "POST"])
def remove_stopwords(langcode):
    if not stopwords.has_key(langcode): 
        abort(404)
    text = get_text_from_request()
    text = " ".join([w for w in re.split('\s+', text) if not w in stopwords[langcode]])
    return json.dumps({"cleaned_text": text}, indent=4)

# RegEx for CleanTweet
ru = re.compile(r"(@\w+)")
rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")
rt = re.compile(r"(\bRT\b)")

@app.route("/cleantweet", methods=["GET", "POST"])
def cleantweet():
    text = get_text_from_request()
    text = ru.sub(" ", text)
    text = rl.sub(" ", text)
    text = rp.sub(" ", text)
    text = rt.sub(" ", text)
    text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
    return json.dumps({"cleaned_text": text}, indent=4)
        
@app.route("/language", methods=["GET", "POST"])
def language():
    text = get_text_from_request()
    app.logger.debug(unicode(text))
#    lang = ngrammodel.classify(data.encode('utf-8'))
    lang = ngrammodel.classify(text)
    return json.dumps({"language": lang})
        
def get_text_from_request():
    if request.method == "POST":
        if not request.headers['Content-Type'] == 'text/plain':
            abort(Response("Unsupported Content Type, use: text/plain\n", status=415))        
        return request.data
    elif request.args.has_key("text"):
        return request.args["text"].encode('utf-8')
    else:
        abort(Response("No text provided, use: POST or GET with attribute text\n", status=400))

if __name__ == '__main__':
    pipeline.append(("Settings", LinksProcessors.SettingsProcessor()))

    semanticize_processor = LinksProcessors.SemanticizeProcessor()
    
    start = time.time()
    for lang, langcode, loc in options.langloc:
        app.logger.info("Loading semanticizer for " + lang + " from " + loc)
    semanticize_processor.load_languages(options.langloc)        
    app.logger.info("Loading semanticizers took %.2f seconds." % (time.time() - start))

    pipeline.append(("Semanticize", semanticize_processor))
    pipeline.append(("Filter", LinksProcessors.FilterProcessor()))
    if options.features:
        app.logger.info("Loading features...")
        start = time.time()
        import features
        pipeline.append(("Features", LinksProcessors.FeaturesProcessor(semanticize_processor, options.article, options.threads)))
        pipeline.append(("ContextFeatures", LinksProcessors.ContextFeaturesProcessor()))
        app.logger.info("Loading features took %.2f seconds." % (time.time() - start))
        if options.scikit:
            pipeline.append(("Learning", LinksProcessors.LearningProcessor()))
        else:
            pipeline.append(("Learning", LinksProcessors.LearningProcessor(options.learn)))
    pipeline.append(("AddImage", LinksProcessors.AddImageProcessor()))

    app.run(host='0.0.0.0', port=options.port, debug=options.verbose, use_reloader=False)
    
