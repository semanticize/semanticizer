import os
import sys
import time
# Can do without ujson and simplejson, but speeds up considerably.
try: import ujson
except ImportError: pass 
try: import simplejson as json
except ImportError: import json
import re
import glob
import codecs

import textcat

from processors.core import SettingsProcessor, FilterProcessor
from processors.semanticizer import SemanticizeProcessor
from processors.features import FeaturesProcessor, ArticleFeaturesProcessor, ContextFeaturesProcessor
from processors.external import ArticlesProcessor, StatisticsProcessor
from processors.learning import LearningProcessor
from processors.image import AddImageProcessor
import Configuration

from flask import Flask, Response, request, abort

import logging
from logging.handlers import TimedRotatingFileHandler

def initialize(parser, app):
    (options, args) = parser.parse_args()
    # Debug mode is not exactly the same as verbose.
    if options.verbose: app.debug = True
    app.debug_log_format = '[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s'
    
    file_handler = TimedRotatingFileHandler(options.log, when='midnight')
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

        result = json_dumps({"links": links, "text": text}, "pretty" in settings)
        app.logger.debug("Semanticizing: Created %d characters of JSON." % len(result))
        return result
        
    @app.route("/stopwords/<langcode>", methods=["GET", "POST"])
    def remove_stopwords(langcode):
        if not stopwords.has_key(langcode): 
            abort(404)
        text = get_text_from_request()
        text = " ".join([w for w in re.split('\s+', text) if not w in stopwords[langcode]])
        return json_dumps({"cleaned_text": text})
    
    @app.route("/cleantweet", methods=["GET", "POST"])
    def cleantweet():
        # RegEx for CleanTweet
        ru = re.compile(r"(@\w+)")
        rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
        rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")
        rt = re.compile(r"(\bRT\b)")
        text = get_text_from_request()
        text = ru.sub(" ", text)
        text = rl.sub(" ", text)
        text = rp.sub(" ", text)
        text = rt.sub(" ", text)
        text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
        return json_dumps({"cleaned_text": text})
        
    @app.route("/language", methods=["GET", "POST"])
    def language():
        text = get_text_from_request()
        app.logger.debug(unicode(text))
    #    lang = ngrammodel.classify(data.encode('utf-8'))
        lang = ngrammodel.classify(text)
        return json_dumps({"language": lang})
            
    def get_text_from_request():
        if request.method == "POST":
            if not request.headers['Content-Type'] == 'text/plain':
                abort(Response("Unsupported Content Type, use: text/plain\n", status=415))        
            return request.data
        elif request.args.has_key("text"):
            return request.args["text"]#.encode('utf-8')
        else:
            abort(Response("No text provided, use: POST or GET with attribute text\n", status=400))
            
    def json_dumps(object, pretty=False):
        if not pretty and "ujson" in locals():
            return ujson.dumps(object)
        elif not pretty:
            return json.dumps(object)
        else:
            return json.dumps(object, indent=4)
    
    @app.route("/inspect", methods=["GET"])
    def inspect():
        inspect = {}
        for step, processor in pipeline:
            inspect.update(processor.inspect())
            
        return json_dumps(inspect, pretty=True)
    
    return pipeline

def main(parser):
    (options, args) = parser.parse_args()
    app = Flask(__name__)
    pipeline = initialize(parser, app)
    pipeline.append(("Settings", SettingsProcessor()))

    semanticize_processor = SemanticizeProcessor()
    
    start = time.time()
    uniqlangs = {}
    for lang, langcode, loc in options.langloc:
        uniqlangs[langcode] = [lang, loc]
    langcodes = uniqlangs.keys()
    wikipedia_ids = {}
    for langcode in uniqlangs:
        wikipedia_ids[langcode] = uniqlangs[langcode][1].split('/')[-2]
    for langcode in uniqlangs:
        app.logger.info("Loading semanticizer for " + uniqlangs[langcode][0] + " from " + uniqlangs[langcode][1])
    semanticize_processor.load_languages(uniqlangs)        
    app.logger.info("Loading semanticizers took %.2f seconds." % (time.time() - start))

    pipeline.append(("Semanticize", semanticize_processor))
    pipeline.append(("Filter", FilterProcessor()))
    if options.features:
        app.logger.info("Loading features...")
        start = time.time()
        pipeline.append(("Features", FeaturesProcessor(semanticize_processor)))
        pipeline.append(("Articles", ArticlesProcessor(wikipedia_ids, options.article, options.threads)))
        pipeline.append(("Statistics", StatisticsProcessor(langcodes, options.threads)))
        pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))#semanticize_processor)))
        pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
        app.logger.info("Loading features took %.2f seconds." % (time.time() - start))
        if options.scikit:
            pipeline.append(("Learning", LearningProcessor()))
        else:
            pipeline.append(("Learning", LearningProcessor(options.learn)))
    pipeline.append(("AddImage", AddImageProcessor()))

    app.run(host='0.0.0.0', port=options.port, debug=options.verbose, use_reloader=False)

if __name__ == '__main__':
    conf = Configuration.Conf()
    main(conf.get_conf())
    
