# Can do without ujson and simplejson, but speeds up considerably.
try:
    import ujson
except ImportError:
    pass 
try:
    import simplejson as json
except ImportError:
    import json

import re
from flask import Flask, Response, request, abort

class Server(object):

    def __init__(self):
        self.app = Flask(__name__)
    
    def set_debug(self, debug, debug_log_format):
        self.app.debug = debug
        self.app.debug_log_format = debug_log_format
        
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
    
    def setup_route_semanticize(self, pipeline):
        self.pipeline = pipeline
        self.app.add_url_rule("/semanticize/<langcode>", "semanticize", self._semanticize, methods=["GET", "POST"])
        
    def setup_route_stopwords(self, stopwords):
        self.stopwords = stopwords
        self.app.add_url_rule("/stopwords/<langcode>", "stopwords", self._remove_stopwords, methods=["GET", "POST"])
        
    def setup_route_cleantweet(self):
        self.app.add_url_rule("/cleantweet", "cleantweet", self._cleantweet, methods=["GET", "POST"])
        
    def setup_route_language(self, ngrammodel):
        self.ngrammodel = ngrammodel
        self.app.add_url_rule("/language", "language", self._language, methods=["GET", "POST"])
        
    def setup_route_inspect(self, pipeline):
        self.pipeline = pipeline
        self.app.add_url_rule("/inspect", "inspect", self._inspect, methods=["GET"])
        
    def setup_all_routes(self, pipeline, stopwords, ngrammodel):
        self.setup_route_semanticize(pipeline)
        self.setup_route_stopwords(stopwords)
        self.setup_route_cleantweet()
        self.setup_route_language(ngrammodel)
        self.setup_route_inspect(pipeline)
        
    def start(self, port, host):
        self.app.run(host, port, self.app.debug, use_reloader=False)
        
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