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
import features
import textcat
import context

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
parser.add_option("-a", "--article", metavar="DIR",
                  help="Location article webservices (default: %default)", 
                  default="http://zookst13.science.uva.nl:8080/dutchsemcor/article")
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

langmap = {}
semanticizers = {}
feature_classes = {}
context_features = {}
ilps_semanticizers = {}

class ILPSSemanticizer:
    def __init__(self, langcode, wikipediaminer_root):
        self.SEMANTICIZE_URL = "http://zookst13.science.uva.nl:8080/dutchsemcor/commonness"
        self.WIKIPEDIA_ID = wikipediaminer_root.split('/')[-2]
        self.WIKIPEDIA_URL_TEMPLATE = "http://%s.wikipedia.org/wiki/%s"
        self.langcode = langcode

    def semanticize(self, text):
        results = {"links": []}
    
        import urllib, urllib2
        url = self.SEMANTICIZE_URL + "?"
        url += urllib.urlencode({"wikipedia": self.WIKIPEDIA_ID, 
                                 "verbose": "true", "normalise": "true",
                                 "input": text})
    
        try:
            request = urllib2.urlopen(url)
            encoding = request.headers['content-type'].split('charset=')[-1]
            #resultDoc = unicode(request.read(), encoding)
            resultDoc = request.read()
        except urllib2.HTTPError:
            return results        
    
        from lxml import etree as ElementTree
        result = ElementTree.fromstring(resultDoc).find("Response")
        
        for sense in result.findall("Sense"):
            for ngram in sense.findall("Ngram"):
                link = {
                    "id": int(sense.attrib["id"]),
                    "title": sense.attrib["title"],
                    "url": self.WIKIPEDIA_URL_TEMPLATE % (langcode, urllib.quote(sense.attrib["title"].encode('utf-8'))),
                    "label": ngram.attrib["text"],
                    "occCount": int(ngram.attrib["occCount"]),
                    "docCount": int(ngram.attrib["docCount"]),
                    "linkOccCount": int(ngram.attrib["linkOccCount"]),
                    "linkDocCount": int(ngram.attrib["linkDocCount"]),
                    "commonness": float(ngram.attrib["score"]),
                    "prior_probability": float(ngram.attrib["linkOccCount"])/float(ngram.attrib["occCount"]),
                    "sense_probability": 
                        float(ngram.attrib["score"])*float(ngram.attrib["linkOccCount"])/float(ngram.attrib["occCount"]),
                }
                results["links"].append(link)
    #             
    #             "fromRedirect": false, 
    #             "url": "http://nl.wikipedia.org/wiki/Franse%20presidentsverkiezingen%20%282002%29", 
    #             "fromTitle": false, 
        return results    

@app.route("/semanticize/<langcode>", methods=["GET", "POST"])
def semanticize(langcode):
    text = get_text_from_request()
    if "semanticizer" in request.args and request.args["semanticizer"] == "ilps":
        if not ilps_semanticizers.has_key(langcode): 
            abort(404)
        results = ilps_semanticizers[langcode].semanticize(text)
    else:
        if not semanticizers.has_key(langcode): 
            abort(404)
        results = semanticizers[langcode].semanticize(text, counts=True, senseprobthreshold=-1)

    if request.args.has_key("features"):
        if not feature_classes.has_key(langcode):
            abort(404)
        else:
            results = compute_features(langcode, results)
    return json.dumps(results, indent=4)
        
def compute_features(langcode, results):
    assert feature_classes.has_key(langcode)
    if not results.has_key("links"):
        return results
    
    # Start threads
    (articles, article_queue) = feature_classes[langcode]["concept"].get_articles(results["links"], options.threads)
    if "wikistats" in request.args:
        import datetime
        if len(request.args["wikistats"]) > 0:
            timestamp = datetime.datetime.fromtimestamp(int(request.args["wikistats"]))
        else:
            timestamp = datetime.now()

        statistics_queue = feature_classes[langcode]["statistics"].cache_wikipedia_page_views(results["links"], options.threads, timestamp)
    if "context" in request.args:
        if request.args["context"] not in context_features:
            new_context(request.args["context"])
        for label in context_features[request.args["context"]]:
            context_features[request.args["context"]][label].add_chunk()
            for link in results["links"]:
                context_features[request.args["context"]][label].add_link(link)
            context_features[request.args["context"]][label].prepare_features()

    for link in results["links"]:
        link["features"] = feature_classes[langcode]["anchor"].compute_anchor_features(link)
    article_queue.join()
    for link in results["links"]:
        article = articles[link["title"]]
        link["features"].update(feature_classes[langcode]["concept"].compute_concept_features(article))
        link["features"].update(feature_classes[langcode]["anchor_concept"].compute_anchor_concept_features(link, article))
    if "wikistats" in request.args:
        statistics_queue.join()
        for link in results["links"]:
            link["features"].update(feature_classes[langcode]["statistics"].compute_statistics_features(link["title"], timestamp))

    if "context" in request.args:
        for label in context_features[request.args["context"]]:
            for link in results["links"]:
                link["features"].update(context_features[request.args["context"]][label].compute_features(link["title"]))
            
    print "Syncing %d category depths for cache." % len(feature_classes[langcode]["concept"].category_depth_cache)
    feature_classes[langcode]["concept"].category_depth_cache.sync()
    print "Syncing %d articles for cache." % len(feature_classes[langcode]["concept"].article_cache)
    feature_classes[langcode]["concept"].article_cache.sync()
        
    print "Sync %d sets of statistics for cache." % len(feature_classes[langcode]["statistics"].wikipedia_statistics_cache)
    feature_classes[langcode]["statistics"].wikipedia_statistics_cache.sync()
            
    return results

def new_context(context_label):
    context_features[context_label] = {}
    for f in ["sense_probability", "prior_probability", "commonness"]:
        for p in [0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
            for t in [10, 25, 50, 75, 100]:
                label = "%s_%.3f_%d" % (f, p, t)
                context_features[context_label][label] = context.contextGraph(label, f, p, t)

        
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
    for lang, langcode, loc in options.langloc:
        langmap[lang] = langcode
        app.logger.info("Loading semanticizer for " + lang + " from " + loc)
        start = time.time()
        semanticizers[langcode] = Semanticizer(langcode, loc)
        ilps_semanticizers[langcode] = ILPSSemanticizer(langcode, loc)
        app.logger.info("Loading semanticizer took %.2f seconds." % (time.time() - start))
        if options.features:
            app.logger.info("Loading features for " + lang + " from " + loc)
            start = time.time()
            import features
            if langcode in semanticizers:
                anchor_features = features.anchorFeatures(langcode, loc, semanticizers[langcode].title_page)
            else:
                anchor_features = features.anchorFeatures(langcode, loc)
            feature_classes[langcode] = {
                "anchor": anchor_features,
                "concept": features.conceptFeatures(langcode, loc, options.article),
                "anchor_concept": features.anchorConceptFeatures(),
                "statistics": features.statisticsFeatures(langcode),
            }
            app.logger.info("Loading features for %s took %.2f seconds." % (lang, time.time() - start))

    app.run(host='0.0.0.0', port=options.port, debug=options.verbose, use_reloader=False)
    
