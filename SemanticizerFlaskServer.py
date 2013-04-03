import os
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
from Configuration import conf_get
from argparse import ArgumentTypeError

from flask import Flask, Response, request, abort

import logging
from logging.handlers import TimedRotatingFileHandler

class SemanticizerFlaskServer(object):
    
    def __init__(self):
        self.app = Flask(__name__)
        self._init_logging()
        self._load_ngram_model()
    
    def start_server(self):
        self._load_stopwords()
        self._validate_langloc()
        self._init_pipeline()
        self._create_routes()
        self.app.run(host='0.0.0.0', port=conf_get("port"), debug=conf_get("verbose"), use_reloader=False)
    
    def _init_logging(self, logformat='[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s'):
        if conf_get("verbose"):
            self.app.debug = True
        self.app.debug_log_format = logformat
    
        file_handler = TimedRotatingFileHandler(conf_get("log"), when='midnight')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(logformat))
        self.app.logger.addHandler(file_handler)
        
    def _load_ngram_model(self):
        self.app.logger.info("Loading ngram model")
        self.ngrammodel = textcat.NGram(conf_get("lm"))
        self.availablelang = self.ngrammodel.listLangs()
    
    def list_lang(self):
        print sorted(self.availablelang)
        
    def _load_stopwords(self):
        self.app.logger.info("Loading stopwords")
        stopwords = {}
    
        for fname in glob.glob(os.path.join(conf_get("stopword"), "stopwords.*")):
            langcode = os.path.split(fname)[-1].split(".")[-1]
            stopwords[langcode] = {}
            for line in codecs.open(fname, 'r', 'utf-8'):
                stopwords[langcode][line.strip()] = 0
            self.stopwords = stopwords
            
    def _validate_langloc(self):
        uniqlangs = {}
        wikipedia_ids = {}
        for lang, langcode, loc in conf_get("langloc"):
            if not langcode in self.stopwords:
                raise ArgumentTypeError("No stopwords")
            if not lang in self.availablelang:
                raise ArgumentTypeError("Language \"" + lang + "\" is not available, available languages are: " + ", ".join(sorted(self.availablelang)))
            if langcode in uniqlangs:
                continue
            wikipedia_ids[langcode] = loc.split('/')[-2]
            uniqlangs[langcode] = [lang, loc]
        self.langcodes = uniqlangs.keys()
        self.uniqlangs = uniqlangs
        self.wikipedia_ids = wikipedia_ids
    
    def _json_dumps(self, o, pretty=False):
        if not pretty and "ujson" in locals():
            return ujson.dumps(o)
        elif not pretty:
            return json.dumps(o)
        else:
            return json.dumps(o, indent=4)
        
    def _get_text_from_request(self):
        if request.method == "POST":
            if not request.headers['Content-Type'] == 'text/plain':
                abort(Response("Unsupported Content Type, use: text/plain\n", status=415))        
            return request.data
        elif request.args.has_key("text"):
            return request.args["text"]#.encode('utf-8')
        else:
            abort(Response("No text provided, use: POST or GET with attribute text\n", status=400))
        
    def _create_routes(self):
        self.app.add_url_rule("/semanticize/<langcode>", "semanticize", self._semanticize, methods=["GET", "POST"])
        self.app.add_url_rule("/stopwords/<langcode>", "stopwords", self._remove_stopwords, methods=["GET", "POST"])
        self.app.add_url_rule("/cleantweet", "cleantweet", self._cleantweet, methods=["GET", "POST"])
        self.app.add_url_rule("/language", "language", self._language, methods=["GET", "POST"])
        self.app.add_url_rule("/inspect", "inspect", self._inspect, methods=["GET"])
        
    def _semanticize(self, langcode):
        self.app.logger.debug("Semanticizing: start")
        text = self._get_text_from_request()
        self.app.logger.debug("Semanticizing text: " + text)
        links = []
        settings = {"langcode": langcode}
        for key, value in request.args.iteritems():
            assert key not in settings
            settings[key] = value

        for function in ("preprocess", "process", "postprocess"):
            for step, processor in self.pipeline:
                self.app.logger.debug("Semanticizing: %s for step %s" % (function, step))
                (links, text, settings) = getattr(processor, function)(links, text, settings)
            self.app.logger.debug("Semanticizing: %s pipeline with %d steps done" % (function, len(self.pipeline)))

        result = self._json_dumps({"links": links, "text": text}, "pretty" in settings)
        self.app.logger.debug("Semanticizing: Created %d characters of JSON." % len(result))
        return result
    
    def _init_pipeline(self):
        pipeline = []
        semanticize_processor = self._init_semanticize_processor()
        pipeline.append(("Settings", SettingsProcessor()))
        pipeline.append(("Semanticize", semanticize_processor))
        pipeline.append(("Filter", FilterProcessor()))
        if conf_get("features") == True:
            self.app.logger.info("Loading features...")
            start = time.time()
            pipeline.append(("Features", FeaturesProcessor(semanticize_processor, conf_get("pickledir"))))
            pipeline.append(("Articles", ArticlesProcessor(self.wikipedia_ids, conf_get("article"), conf_get("threads"), conf_get("pickledir"))))
            pipeline.append(("Statistics", StatisticsProcessor(self.langcodes, conf_get("threads"), conf_get("pickledir"))))
            pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))
            pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
            self.app.logger.info("Loading features took %.2f seconds." % (time.time() - start))
            if conf_get("scikit"):
                pipeline.append(("Learning", LearningProcessor()))
            else:
                pipeline.append(("Learning", LearningProcessor(conf_get("learn"))))
        pipeline.append(("AddImage", AddImageProcessor()))
        self.pipeline = pipeline
    
    def _init_semanticize_processor(self):
        semanticize_processor = SemanticizeProcessor()
        start = time.time()
        self.app.logger.info("Loading semanticizers for langcode(s) " + ", ".join(self.langcodes))
        semanticize_processor.load_languages(self.uniqlangs)
        self.app.logger.info("Loading semanticizers took %.2f seconds." % (time.time() - start))
        return semanticize_processor

    def _remove_stopwords(self, langcode):
        if not self.stopwords.has_key(langcode): 
            abort(404)
        text = self._get_text_from_request()
        text = " ".join([w for w in re.split('\s+', text) if not w in self.stopwords[langcode]])
        return self._json_dumps({"cleaned_text": text})
    
    def _cleantweet(self):
        # RegEx for CleanTweet
        ru = re.compile(r"(@\w+)")
        rl = re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)")
        rp = re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]")
        rt = re.compile(r"(\bRT\b)")
        text = self._get_text_from_request()
        text = ru.sub(" ", text)
        text = rl.sub(" ", text)
        text = rp.sub(" ", text)
        text = rt.sub(" ", text)
        text = " ".join([w for w in re.split('\s+', text) if len(w) > 1])
        return self._json_dumps({"cleaned_text": text})
        
    def _language(self):
        text = self._get_text_from_request()
        self.app.logger.debug(unicode(text))
        lang = self.ngrammodel.classify(text)
        return self._json_dumps({"language": lang})
    
    def _inspect(self):
        inspect = {}
        for step, processor in self.pipeline:
            inspect.update(processor.inspect())
            
        return self._json_dumps(inspect, pretty=True)
    
if __name__ == '__main__':
    server = SemanticizerFlaskServer()
    if conf_get("listlang"):
        server.list_lang()
    else:
        server.start_server()
    
