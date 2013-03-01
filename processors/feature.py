import shelve
import cPickle as pickle
from datetime import datetime, timedelta

from Queue import Queue, Empty
from threading import Thread

from math import log
import urllib, urllib2
from lxml import etree as ElementTree
import re
from json import loads
import collections
import stringUtils

# Als je het EDIT_DISTANCE feature wil gebruiken moet je een Python Levenshtein
# module installeren. Ik had deze gepakt:
# http://pypi.python.org/pypi/python-Levenshtein/0.10.2
import Levenshtein

class anchorFeatures:
    def __init__(self, langcode, wikipediaminer_root, title_page=None):
        pickle_root = '/scratch/dodijk/semanticizer/pickles/%s/' % langcode
        
        #   From Wikipedia miner CSV file:
        self.wikipediaArticleCount = 970139
        self.wikipediaCategoryCount = 63108
        # NEEDS TO BE CHANGED FOR OTHER LANGUAGES THAN NL
        if langcode != "nl": 
            print "WARNING: Statistics for features are incorrect"
            
        if title_page != None:
            self.title_page = title_page
            try:
                self.ngram_in_title = pickle.load(open(pickle_root + 'ngram_in_title.pickle', 'rb'))
                print "Loaded ngram in title from pickle"
            except IOError:
                self.ngram_in_title = {}
                self.load_ngram_in_title()
                pickle.dump(self.ngram_in_title, open(pickle_root + 'ngram_in_title.pickle', 'wb'))
        else:
            try:
                self.title_page = pickle.load(open(pickle_root + 'title_page.pickle', 'rb'))
                self.ngram_in_title = pickle.load(open(pickle_root + 'ngram_in_title.pickle', 'rb'))
                print "Loaded page titles from pickle"
            except IOError:
                self.title_page = {}
                self.ngram_in_title = {}
                self.load_page_titles(wikipediaminer_root + "page.csv")
                pickle.dump(self.title_page, open(pickle_root + 'title_page.pickle', 'wb'))
                pickle.dump(self.ngram_in_title, open(pickle_root + 'ngram_in_title.pickle', 'wb'))

    def load_page_titles(self, filename):
        print "Loading page titles...", 
        file = open(filename, 'r')
        for line in file:
            line = line.replace('\'', '')
            splits = line.split(',')
            id = int(splits[0])
            title = splits[1]
    #       page_title[id] = title
            self.title_page[title] = id
            
            words = title.split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def load_ngram_in_title(self):
        print "Loading ngram in title...", 
        for title in self.title_page:
            words = title.split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def feature_LEN(self, link):
        return len(re.findall(stringUtils.reTokenPattern, link["label"]))
    
    def feature_IDF_title(self, link):
        if self.ngram_in_title.has_key(link["label"]):
            in_title_count = self.ngram_in_title[link["label"]]
        else:
            in_title_count = 0
        return log(float(self.wikipediaArticleCount)/ \
                   (float(in_title_count)+0.00001) )
    
    def feature_IDF_anchor(self, link):
        return log(float(self.wikipediaArticleCount)/ \
                   (float(link["linkDocCount"])+0.00001))
    
    def feature_IDF_content(self, link):
        return log(float(self.wikipediaArticleCount)/ \
                   (float(link["docCount"])+0.00001))
    
    def feature_KEYPHRASENESS(self, link):
        return float(link["linkDocCount"])/(float(link["docCount"])+0.00001)
    
    def feature_LINKPROB(self, link):
        return float(link["linkOccCount"])/(float(link["occCount"])+0.00001)
    
    def feature_SNIL(self, link):
        SNIL = 0
            
        words = link["label"].split()
        for n in range(1, len(words)+1):
            for i in range(0, len(words)-n):
                ngram = " ".join(words[i:i+n])
                if ngram in self.title_page:
                    SNIL += 1
        return SNIL
    
    def feature_SNCL(self, link):
        SNCL = 0
            
        words = link["label"].split()
        for n in range(1, len(words)+1):
            for i in range(0, len(words)-n):
                ngram = " ".join(words[i:i+n])
                if ngram in self.ngram_in_title:
                    SNCL += self.ngram_in_title[ngram]
        return SNCL

    def compute_anchor_features(self, link):
        return {'LEN': self.feature_LEN(link),
                'IDF_title': self.feature_IDF_title(link),
                'IDF_anchor': self.feature_IDF_anchor(link),
                'IDF_content': self.feature_IDF_content(link),
                'KEYPHRASENESS': self.feature_KEYPHRASENESS(link),
                'LINKPROB': self.feature_LINKPROB(link),
                'SNIL': self.feature_SNIL(link),
                'SNCL': self.feature_SNCL(link)
                }
       
class conceptFeatures:
    def __init__(self, langcode, wikipediaminer_root, article_url):
        pickle_root = '/scratch/dodijk/flask-semanticizer/pickles/%s/' % langcode
        
        self.ARTICLE_URL = article_url
        self.WIKIPEDIA_ID = wikipediaminer_root.split('/')[-2]

        print "Loaded %d articles from cache." % len(self.article_cache)

    def feature_INLINKS(self, child):
        return int(child.attrib["total"])
    
    def feature_OUTLINKS(self, child):
        return int(child.attrib["total"])

    def feature_REDIRECT(self, child):
        redirect = 0
        for label in child:
            # Should be fromRedirect but bug in Wikipedia Miner
            if label.attrib["fromTitle"] == "true":
                redirect += 1
        return redirect

    def compute_concept_features(self, article):
        # Eerst initieren want heel soms komen er bijvoorbeeld geen inlinks
        # voor
        features = {'INLINKS': 0,
                    'OUTLINKS': 0,
                    'GEN': 0,
                    'REDIRECT': 0
                    }

        # Hier loop je dus maar 1 keer door het article object heen
        ### Ja, maar dit wordt dus op basis van 1 dict ###
        for child in article:
            if child.tag == 'InLinks':
                features['INLINKS'] = self.feature_INLINKS(child)
            elif child.tag == 'OutLinks':
                features['OUTLINKS'] = self.feature_OUTLINKS(child)
            elif child.tag == 'Labels':
                features['REDIRECT'] == self.feature_REDIRECT(child)
                
        return features

    def get_articles(self, articles, num_of_threads):
        results = {}
        def worker():
            while True:
                try:
                    item = queue.get_nowait()
                    results[item] = self.get_article(item.encode('utf-8'))
                    queue.task_done()
                except Empty:
                    break
        
        queue = Queue()
        for title in set([article["title"] for article in articles]):
            queue.put(title)
        
        for i in range(num_of_threads):
            t = Thread(target=worker)
            t.daemon = True
            t.start()
        
        return (results, queue)
        
    def get_article(self, article):
        if self.article_cache.has_key(article):
            resultDoc = self.article_cache[article]
        else:
            url = self.ARTICLE_URL + "?"
            url += urllib.urlencode({"wikipedia": self.WIKIPEDIA_ID, 
                                     "title": article, 
                                     "definition": "true",
                                     "definitionLength":"LONG",
                                     "linkRelatedness": True,
                                     "linkFormat":"HTML", 
                                     "inLinks": "true",
                                     "outLinks": "true",
                                     "labels": "true",
                                     "parentCategories": "true"})            

            try:
                request = urllib2.urlopen(url)
                encoding = request.headers['content-type'].split('charset=')[-1]
                #resultDoc = unicode(request.read(), encoding)
                resultDoc = request.read()
            except urllib2.HTTPError:
                # Strange bug in some articles, mentioned to Edgar
                print "Strange bug, requesting shorter definition"
        
                request = urllib2.urlopen(url.replace("&definitionLength=LONG", ""))
                encoding = request.headers['content-type'].split('charset=')[-1]
                #resultDoc = unicode(request.read(), encoding)
                resultDoc = request.read()
    
            self.article_cache[article] = resultDoc
        
        result = ElementTree.fromstring(resultDoc).find("Response")
        
        if not result.attrib.has_key("title"):
            print "Error", result.attrib["error"]
            if 'url' in locals(): print url
        else:
            if article.decode("utf-8") != result.attrib["title"]:
                print "%s!=%s" % (article.decode("utf-8"), result.attrib["title"])
    
        return result

class anchorConceptFeatures:
    def __init__(self):
        self.re_non_word_chars = re.compile('(?u)\W+', re.UNICODE)

    def feature_TF(self, link, article, re_label_text, features):
        aMatches = re.findall(re_label_text, link['title'])
        features["TF_title"] = float(len(aMatches))

        text = " "
        for child in article:
            if child.tag == "Definition":
                if child.text and len(child.text):
                    text = re.sub(r"<.*?>", "", child.text)
                    text = re.sub(r"^[|\- }]*", "", text)
                break

        while len(text) and (text[0] == "."):
            text = text[1:].strip()

        # Very rarely articles do not have a Definition text (or a dummy one 
        # like "----") 
        if len(text) == 0:
            features["TF_sentence"] = 0
            features["TF_paragraph"] = 0
            features["POS_first_in_paragraph"] = 1
        else:
            # Sentence is first sentence                                    
            sentence = text.split('.')[0]

            aMatches = re.findall(re_label_text, sentence)
            features["TF_sentence"] = float(len(aMatches))

            aMatches = re.findall(re_label_text, text)
            features["TF_paragraph"] = float(len(aMatches))

            if len(aMatches):
                features["POS_first_in_paragraph"] = \
                               float(re.search(re_label_text, text).start())
            else:
                features["POS_first_in_paragraph"] = 1

    def feature_TITLE(self, link, article, re_label_text, features):
        label_text = unicode(link["label"])

        re_title = stringUtils.ngramToPattern(article.attrib['title'])
        article_title = unicode(article.attrib['title'])
        
        features["NCT"] = 0 if re.search(re_title, label_text) is None \
            else 1

        features["TCN"] = 0 \
            if re.search(re_label_text, article_title) is None else 1

        features["TEN"] = 1 if article_title == label_text else 0

        # Irritatingly enough, split() can give you empty values as last
        # element
        split_label = self.re_non_word_chars.split(label_text)
        if split_label[-1] == '':
            split_label.pop()
        split_title = self.re_non_word_chars.split(article_title)
        if split_title[-1] == '':
            split_title.pop()

        # I: True if the title of the candidate begins with the the query 
        # (e.g. "Cambridge, Massachusetts" and "Cambridge" ) 
        features["SUBSTRING_MATCH_1"] = 1 \
            if split_title[0] == split_label[0] else 0

        # II: True if the title of the candidate ends with the the query 
        # (e.g: "Venice-Simplon Orient Express" and "Orient Express") 
        features["SUBSTRING_MATCH_2"] = 1 \
            if split_title[-1] == split_label[-1] else 0

        # collections.Counter() converts an array to a dict of words
        # and their frequencies
        cSplitLabel = collections.Counter(split_label)
        cSplitTitle = collections.Counter(split_title)

        # Number of shared words between the title of the candidate and
        # the  query 
        features['WORD_MATCH'] = len(list(cSplitLabel & cSplitTitle))

        # Number of different words between the title of the candidate
        # and the query 
        features['WORD_MISS'] = len(split_label) + len(split_title) \
            - (2 * features['WORD_MATCH'])

        # Levenshtein distance between query and title of the candidate 
        features["EDIT_DISTANCE"] = Levenshtein.distance(label_text,
                                                         article_title)
    
    def feature_COMMONNESS(self, link, features):
        features["COMMONNESS"] = link["commonness"]
        
    def compute_anchor_concept_features(self, link, article):
        features = {}

        re_label_text = stringUtils.ngramToPattern(link["label"])
        
        self.feature_TF(link, article, re_label_text, features)
        self.feature_TITLE(link, article, re_label_text, features)
        self.feature_COMMONNESS(link, features)

        ### TK: Ik heb nog wat extra features gemaakt die kijken hoe vaak
        ### inlink anchors en inlink/outlink titels voorkomen in de
        ### referentietekst en de zogenaamde aposition in de titel
        ### ('actress' in 'Sue Johnson (actress)')
        ###
        ### 'NR_OF_MATCHING_INLINK_ANCHORS', 'NR_OF_MATCHING_INLINK_TITLES',
        ### 'NR_OF_MATCHING_OUTLINK_TITLES', 'APOSITION'
        ###
        ### Dat is er nu niet zo makkelijk in te bouwen omdat we hier geen
        ### toegang hebben tot de referentietekst. Maar die features van David
        ### gaan dat ook zeker nodig hebben!
        ###
        ### Maar goed, ik heb ze nu nog even weg gelaten...

class statisticsFeatures:
    def __init__(self, langcode):
        #pickle_root = '/scratch/dodijk/flask-semanticizer/pickles/%s/' % \
        #              langcode 
        pickle_root = '/scratch/tkenter1/pickles/%s/' % langcode

        self.WIKIPEDIA_STATS_URL = "http://stats.grok.se/json/" + \
                                   langcode + \
                                   "/%d%02d/%s" # 201001/De%20Jakhalzen
        self.wikipedia_statistics_cache = \
                    shelve.open(pickle_root + 'wikipedia_statistics_cache.db')
        print "Loaded %d sets of statistics from cache." % \
              len(self.wikipedia_statistics_cache)

        self.date_format = "%d-%02d-%02d"
        
    def compute_statistics_features(self, article, now=datetime.now()):
        features = {"WIKISTATSDAY": 0,
                    "WIKISTATSWK": 0,
                    "WIKISTATS4WK": 0,
                    "WIKISTATSYEAR": 0,
                    "WIKISTATSDAYOFWK": 0,
                    "WIKISTATSWKOF4WK": 0,
                    "WIKISTATS4WKOFYEAR": 0
                    }
    
        self.feature_WIKISTATSDAY(datetime, article, features, now)
        self.feature_WIKISTATSWK(datetime, article, features, now)
        self.feature_WIKISTATS4WK(datetime, article, features, now)
        self.feature_WIKISTATSYEAR(datetime, article, features, now)
        self.feature_WIKISTATSTRENDS(features)

        del features["WIKISTATSDAY"]
        
        return features

    def feature_WIKISTATSDAY(self, datetime, article, features, now): 
        day = now
        day += timedelta(days=-1)
        monthly_views = self.wikipedia_page_views(day.year,
                                                  day.month, article)
        views = monthly_views["daily_views"][self.date_format % \
                                             (day.year,day.month, day.day)]
        features["WIKISTATSDAY"] = views
    
    def feature_WIKISTATSWK(self, datetime, article, features, now): 
        day = now
        for n in range(7):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = \
                  monthly_views["daily_views"][self.date_format % \
                                               (day.year, day.month, day.day)]
            features["WIKISTATSWK"] += views

    def feature_WIKISTATS4WK(self, datetime, article, features, now):
        day = now
        for n in range(28):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = monthly_views["daily_views"][self.date_format % \
                                                 (day.year,day.month, day.day)]
            features["WIKISTATS4WK"] += views

    def feature_WIKISTATSYEAR(self, datetime, article, features, now):
        day = now
        for n in range(365):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = monthly_views["daily_views"][self.date_format % \
                                                 (day.year,day.month, day.day)]
            features["WIKISTATSYEAR"] += views

    def feature_WIKISTATSTRENDS(self, features): 
        if features["WIKISTATSWK"] > 0:
            features["WIKISTATSDAYOFWK"] = \
                       float(features["WIKISTATSDAY"])/features["WIKISTATSWK"]
        if features["WIKISTATS4WK"] > 0:
            features["WIKISTATSWKOF4WK"] = \
                       float(features["WIKISTATSWK"])/features["WIKISTATS4WK"]
        if features["WIKISTATSYEAR"] > 0:
            features["WIKISTATS4WKOFYEAR"] = \
                     float(features["WIKISTATS4WK"])/features["WIKISTATSYEAR"]

    def wikipedia_page_views(self, year, month, article):
        url = self.WIKIPEDIA_STATS_URL % (year, month, article)
        url = url.encode('utf-8')
        if self.wikipedia_statistics_cache.has_key(url):
            resultJson = self.wikipedia_statistics_cache[url]
        else:
            try:
                request = urllib2.urlopen(url, timeout=1)
                encoding = request.headers['content-type'].split('charset=')[-1]
                resultJson = request.read()
            except urllib2.URLError:
                try:
                    request = urllib2.urlopen(url)
                    encoding = request.headers['content-type'].split('charset=')[-1]
                    resultJson = request.read()
                except urllib2.URLError:
                    request = urllib2.urlopen(url)
                    encoding = request.headers['content-type'].split('charset=')[-1]
                    resultJson = request.read()
    
            self.wikipedia_statistics_cache[url] = resultJson
        
        result = loads(resultJson)
        
        return result

    def cache_wikipedia_page_views(self, articles, num_of_threads,
                                   now=datetime.now()):
        def worker():
            while True:
                try:
                    (year, month, article) = queue.get_nowait()
                    self.wikipedia_page_views(year, month, article)
                    queue.task_done()
                except Empty:
                    break
        
        queue = Queue()
        for title in set([article["title"] for article in articles]):
            day = now
            for i in range(14):
                queue.put((day.year, day.month, article))
                day += timedelta(days=28)
        
        for i in range(num_of_threads):
            t = Thread(target=worker)
            t.daemon = True
            t.start()
        
        return queue

if __name__ == "__main__":
    # Some settings
    langcode = "en"
    wikipediaminer_root = '/zfs/ilps-plexer/wikipediaminer/enwiki-20111007/'

    # Test data
    link = {"label":  "Alabama",
            "linkDocCount": 10, # Al deze waardes slaan nergens op natuurlijk,
            "docCount": 20,     # maar ok...
            "linkOccCount": 100,
            "occCount": 200,
            "commonness": 0.12345
            }

    # Article
    article_url = '' # Wordt niet gebruikt nu
    fh_article_xml = open("unitTest.article.xml", "r")
    article_xml = fh_article_xml.read()
    fh_article_xml.close()
    article = ElementTree.fromstring(article_xml).find("Response")
    
    # Initialize the objects
    print "Initializing anchor features"
    anchor_features = anchorFeatures(langcode, wikipediaminer_root)
    print "Initializing concept features"
    concept_features = conceptFeatures(langcode, wikipediaminer_root,
                                       article_url)
    print "Initializing anchor/concept features"
    anchor_concept_features = anchorConceptFeatures()
    print "Initializing statistics features"
    statistics_features = statisticsFeatures(langcode)

    print "Start calculating"
    test_features = {
        "anchor": anchor_features.compute_anchor_features(link),
        "concept": concept_features.compute_concept_features(article),
        "anchor_concept": \
        anchor_concept_features.compute_anchor_concept_features(link, article),
        "statistics": statistics_features.compute_statistics_features(article),
        }

    print "%s" % test_features
