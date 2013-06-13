# Copyright 2012-2013, University of Amsterdam. This program is free software:
# you can redistribute it and/or modify it under the terms of the GNU Lesser 
# General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License 
# for more details.
# 
# You should have received a copy of the GNU Lesser General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
import wpm.wpmutil as wpmutil
from flask import Flask, Response, request, abort


class Server(object):
    """
    The HTTP server that will serve the complete namespace
    """

    APPLICATION_JSON="application/json"

    def __init__(self):
        """
        Initialize the server. The constructor creates the initial Flask server
        object.
        """
        self.app = Flask(__name__)

    def set_debug(self, debug=None, debug_log_format=None):
        """
        Set Flask server debug parameters.

        @param debug: Enable or disable debug mode
        @param debug_log_format: Set the logformat string for the server
        """
        if not debug is None:
            self.app.debug = debug
        if not debug_log_format is None:
            self.app.debug_log_format = debug_log_format

    def _json_dumps(self, o, pretty=False):
        """
        Util function to create json dumps based on an object.

        @param o: Object to transform
        @param pretty: Whether or not to prettify the JSON
        @return: The JSON string
        """
        if not pretty and "ujson" in locals():
            return ujson.dumps(o)
        elif not pretty:
            return json.dumps(o)
        else:
            return json.dumps(o, indent=4)

    def _get_text_from_request(self):
        """
        Util function to get the param called "text" from the current request

        @return: the value of "text"
        """
        content_type = request.headers['Content-Type']
        if request.method == "POST":
            if content_type == 'application/x-www-form-urlencoded':
                return request.form['text']
            elif content_type == 'text/plain':
                return request.data
            else:
                abort(Response("Unsupported Content Type, use: text/plain\n",
                               status=415))
        elif "text" in request.args:
            return request.args["text"]
        else:
            abort(Response("No text provided, use: POST or GET with attribute \
                            'text'\n", status=400))

    def setup_route_semanticize(self, pipeline, langcodes):
        """
        Setup the /semanticize/<langcode> namespace.

        @param pipeline: The pipeline that will be used to semanticize the \
                         given text
        """
        self.pipeline = pipeline
        self.langcodes = langcodes
        self.app.add_url_rule("/semanticize/<langcode>", "_semanticize",
                              self._semanticize_handler, methods=["GET", "POST"])
        self.app.add_url_rule("/semanticize", "_autolang_semanticize",
                              self._autolang_semanticize,
                              methods=["GET", "POST"])

    def setup_route_language(self, textcat):
        """
        Setup the /language namespace.

        @param textcat: The textcat language guesser instance to use
        """
        self.textcat = textcat
        self.app.add_url_rule("/language", "_language",
                              self._language, methods=["GET", "POST"])

    def setup_route_inspect(self, pipeline):
        """
        Setup the /inspect namespace.

        @param pipeline: The pipeline of processors to inspect.
        """
        self.pipeline = pipeline
        self.app.add_url_rule("/inspect", "_inspect",
                              self._inspect, methods=["GET"])

    def setup_all_routes(self, pipeline, langcodes, textcat):
        """
        Convenience function to start all namespaces at once.

        @param pipeline: The pipeline of processors
        @param textcat: The textcat language guesser instance to use
        """
        self.setup_route_semanticize(pipeline, langcodes)
        self.setup_route_language(textcat)
        self.setup_route_inspect(pipeline)

    def start(self, host, port):
        """
        Wrapper for the Flask run() function. Will start the HTTP server with
        all initialized namespaces.

        @param host: The hostname to bind on
        @param port: The port to bind on
        """
        print "Server started on %s:%d" % (host, port)
        self.app.run(host, port, self.app.debug, use_reloader=False)

    def _autolang_semanticize(self):
        """
        The function handling the /semanticize namespace. It calls _semanticize
        to handle the request after determining the language.

        @return: The body of the response, in this case a json formatted list \
                 of links and their relevance
        @see: _semanticize
        """
        if request.method == "GET" and not "text" in request.args:
            return self._json_dumps({"languages": self.langcodes},
                                    "pretty" in request.args)

        text = self._get_text_from_request()
        lang = self.textcat.classify(text.encode('utf-8'))
        for langcode in self.langcodes:
            if wpmutil.wpm_dumps[langcode].get_lang_name() == lang:
                break
        else:
            return self._json_dumps({"language": lang, "text": text,
                                     "links": []},
                                    "pretty" in request.args)

        settings = {"langcode": langcode}
        for key, value in request.args.iteritems():
            assert key not in settings
            settings[key] = value

        sem_result = self._semanticize(key, settings, text)
        sem_result["language"] = lang
        json = self._json_dumps(sem_result, "pretty" in settings)
        return Response(json, mimetype=Server.APPLICATION_JSON)

    def _semanticize_handler(self, langcode):
        """
        The function handling the /semanticize/<langcode> namespace. It uses
        the chain-of-command pattern to run all processors, using the
        corresponding preprocess, process, and postprocess steps.

        @param langcode: The language to use in the semanticizing
        @return: The body of the response, in this case a json formatted list \
                 of links and their relevance
        """
        self.app.logger.debug("Semanticizing: start")
        text = self._get_text_from_request()
        self.app.logger.debug("Semanticizing text: " + text)
        links = []
        settings = {"langcode": langcode}
        for key, value in request.values.iteritems():
            assert key not in settings
            settings[key] = value

        sem_result = self._semanticize(langcode, settings, text)
        json = self._json_dumps(sem_result, "pretty" in settings)

        self.app.logger.debug("Semanticizing: Created %d characters of JSON." \
                              % len(json))
        return Response(json, mimetype=Server.APPLICATION_JSON)

    def _semanticize(self, langcode, settings, text):
        """
        Method that performs the actual semantization.
        """
        links = []

        for function in ("preprocess", "process", "postprocess"):
            for step, processor in self.pipeline:
                self.app.logger.debug("Semanticizing: %s for step %s" \
                                      % (function, step))
                (links, text, settings) = getattr(processor, function)(links,
                                                                       text,
                                                                       settings
                                                                       )
            self.app.logger.debug("Semanticizing: %s pipeline with %d steps \
                                   done" % (function, len(self.pipeline)))

        result = {"links": links, "text": text}

        return result

    def _language(self):
        """
        Function that handles the /language namespace. Will try to use the
        textcat instance for classifying the string and detecting the language.

        @return: The body of the response, in this case a json formatted \
                 string containing the detected language.
        """
        text = self._get_text_from_request()
        self.app.logger.debug(unicode(text))
        lang = self.textcat.classify(text.encode("utf-8"))
        return self._json_dumps({"language": lang})

    def _inspect(self):
        """
        Function that handles the /inspect namespace. Will print the settings
        used by the different processors.

        @return: The body of the response, in this case a json formatted \
                 string containing all found settings.
        """
        inspect = {}
        for _, processor in self.pipeline:
            inspect.update(processor.inspect())
        return self._json_dumps(inspect, pretty=True)
