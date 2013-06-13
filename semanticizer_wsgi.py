""" Semanticizer (WSGI version)

A stripped down, WSGI compatible, version of the semanticizer.

Usage:
  gunicorn --bind 0.0.0.0:5001 --workers 4 semanticizer_wsgi:app

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

# Kurwa broken config handling in config.py
WPMDATA = {'nl': ['dutch', '/zfs/ilps-plexer/wikipediaminer/nlwiki-20111104']}

# WSGI app!
app = Flask(__name__)
app.debug = True

APPLICATION_JSON = "application/json"
PIPELINE = procpipeline.build(WPMDATA, feature_config=None)

# RegExens for CleanTweet
CLEAN_TWEET = \
    {'user': re.compile(r"(@\w+)"),
     'url': re.compile(r"(http://[a-zA-Z0-9_=\-\.\?&/#]+)"),
     'punctuation': re.compile(r"[-!\"#\$%&'\(\)\*\+,\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]+"),
     'retweet': re.compile(r"(\bRT\b)")
     }


@app.route('/')
def hello_world():
    """Hello World!"""
    return 'Hello World!\n'


@app.route('/semanticize/<langcode>', methods=['GET', 'POST'])
def _semanticize_handler(langcode):
    """
    The function handling the /semanticize/<langcode> namespace. It uses
    the chain-of-command pattern to run all processors, using the
    corresponding preprocess, process, and postprocess steps.

    @param langcode: The language to use in the semanticizing
    @return: The body of the response, in this case a json formatted list \
             of links and their relevance
    """
    # self.app.logger.debug("Semanticizing: start")
    text = _get_text_from_request()

    # self.app.logger.debug("Semanticizing text: " + text)
    settings = {"langcode": langcode}
    for key, value in request.values.iteritems():
        assert key not in settings
        settings[key] = value

    sem_result = _semanticize(langcode, settings, text)
    json = _json_dumps(sem_result, "pretty" in settings)

    # self.app.logger.debug("Semanticizing: Created %d characters of JSON." \
    #                       % len(json))
    return Response(json, mimetype=APPLICATION_JSON)


@app.route('/cleantweet', methods=['GET', 'POST'])
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
            # self.app.logger.debug("Semanticizing: %s for step %s" \
            #                       % (function, step))
            (links, text, settings) = getattr(processor, function)(links,
                                                                   text,
                                                                   settings
                                                                   )
        # self.app.logger.debug("Semanticizing: %s pipeline with %d steps \
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
        return ujson.dumps(o)
    elif not pretty:
        return json.dumps(o)
    else:
        return json.dumps(o, indent=4)

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
    app.run()
