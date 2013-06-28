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

""" Semanticizer (WSGI version)

A stripped down, WSGI compatible, version of the semanticizer.

Usage:
  gunicorn --bind 0.0.0.0:5001 --workers 4 semanticizer_wsgi:application
or
  uwsgi --http :5001 --master --processes 4 --wsgi-file semanticizer_wsgi.py

"""

import sys
import re

# Can do without ujson and simplejson, but speeds up considerably.
try:
    import ujson
except ImportError:
    pass
try:
    import simplejson as json
except ImportError:
    import json

from flask import Flask, Response, request

import procpipeline
from config import conf_get
import wpm.wpmutil as wpmutil


wpm_languages = conf_get('wpm', 'languages')
wpmutil.init_datasource(wpm_languages)
PIPELINE = procpipeline.build(wpm_languages, feature_config=None)

# WSGI application!
application = Flask(__name__)
application.debug = True


APPLICATION_JSON = "application/json"

# RegExens for CleanTweet
CLEAN_TWEET = \
    {'user': re.compile(r"(@\w+)"),
     'url': re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)"),
     'punctuation': re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]+"),
     'retweet': re.compile(r"(\bRT\b)")
     }


@application.route('/')
def hello_world():
    """Hello World!"""
    return 'Hello World!\n'


@application.route('/semanticize/<langcode>', methods=['GET', 'POST'])
def _semanticize_handler(langcode):
    """
    The function handling the /semanticize/<langcode> namespace. It uses
    the chain-of-command pattern to run all processors, using the
    corresponding preprocess, process, and postprocess steps.

    @param langcode: The language to use in the semanticizing
    @return: The body of the response, in this case a json formatted list \
             of links and their relevance
    """
    # self.application.logger.debug("Semanticizing: start")
    text = _get_text_from_request()

    # self.application.logger.debug("Semanticizing text: " + text)
    settings = {"langcode": langcode}
    for key, value in request.values.iteritems():
        assert key not in settings
        settings[key] = value

    sem_result = _semanticize(langcode, settings, text)
    json = _json_dumps(sem_result, "pretty" in settings)

    # self.application.logger.debug("Semanticizing: Created %d characters of JSON." \
    #                       % len(json))
    return Response(json, mimetype=APPLICATION_JSON)


@application.route('/cleantweet', methods=['GET', 'POST'])
def _cleantweet():
    """
    The function that handles the /cleantweet namespace. Will use regular
    expressions to completely clean a given tweet.

    @return: The body of the response, in this case a json formatted \
             string containing the cleaned tweet.
    """
    text = _get_text_from_request()
    clean_text = cleantweet(text)

    return _json_dumps({"cleaned_text": clean_text})


def cleantweet(text):
    """
    Tweet cleaner/tokenizer.

    Uses regular expressions to completely clean, and tokenize, a
    given tweet.
    """

    for cleaner in ['user', 'url', 'punctuation', 'retweet']:
        text = CLEAN_TWEET[cleaner].sub(" ", text)
    text = " ".join([w for w in re.split(r'\s+', text) if len(w) > 1])

    return text


def _semanticize(langcode, settings, text):
    """
    Method that performs the actual semantization.
    """
    links = []

    for function in ("preprocess", "process", "postprocess"):
        for step, processor in PIPELINE:
            # self.application.logger.debug("Semanticizing: %s for step %s" \
            #                       % (function, step))
            (links, text, settings) = getattr(processor, function)(links,
                                                                   text,
                                                                   settings
                                                                   )
        # self.application.logger.debug("Semanticizing: %s pipeline with %d steps \
        #                        done" % (function, len(self.pipeline)))

    result = {"links": links, "text": text}

    return result


def _json_dumps(obj, pretty=False):
    """
    Util function to create json dumps based on an object.

    @param o: Object to transform
    @param pretty: Whether or not to prettify the JSON
    @return: The JSON string
    """
    if not pretty and "ujson" in locals():
        return ujson.dumps(obj)
    elif not pretty:
        return json.dumps(obj)
    else:
        return json.dumps(obj, indent=4)

def _get_text_from_request():
    """
    Util function to get the param called "text" from the current request

    @return: the value of "text"
    """

    return request.values['text']
    # content_type = request.headers['Content-Type']
    # if request.method == "POST":
    #     if content_type == 'application/x-www-form-urlencoded':
    #         return request.form['text']
    #     elif content_type == 'text/plain':
    #         return request.data
    #     else:
    #         abort(Response("Unsupported Content Type, use: text/plain\n",
    #                        status=415))
    # elif "text" in request.args:
    #     return request.args["text"]
    # else:
    #     abort(Response("No text provided, use: POST or GET with attribute \
    #                     'text'\n", status=400))


if __name__ == '__main__':
    application.run()
