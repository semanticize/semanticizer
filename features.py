import shelve
import cPickle as pickle
from datetime import datetime, timedelta

from Queue import Queue, Empty
from threading import Thread

class anchorFeatures:
    def __init__(self, langcode, wikipediaminer_root, title_page=None):
        pickle_root = '/scratch/dodijk/flask-semanticizer/pickles/%s/' % langcode
        
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

    def compute_anchor_features(self, link):
        # Not entirely correct?:
        def feature_LEN(link):
            return 1+link["label"].count(' ')+link["label"].count('-')
            
        def feature_IDF_title(link):
            from math import log
            if self.ngram_in_title.has_key(link["label"]):
                in_title_count = self.ngram_in_title[link["label"]]
            else:
                in_title_count = 0
            return log(float(self.wikipediaArticleCount)/(float(in_title_count)+0.00001))
            
        def feature_IDF_anchor(link):
            from math import log
            return log(float(self.wikipediaArticleCount)/(float(link["linkDocCount"])+0.00001))
    
        def feature_IDF_content(link):
            from math import log
            return log(float(self.wikipediaArticleCount)/(float(link["docCount"])+0.00001))
    
        def feature_KEYPHRASENESS(link):
            return float(link["linkDocCount"])/(float(link["docCount"])+0.00001)
    
        def feature_LINKPROB(link):
            return float(link["linkOccCount"])/(float(link["occCount"])+0.00001)
    
        def feature_SNIL(link):
            SNIL = 0
            
            words = link["label"].split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    if ngram in self.title_page:
                        SNIL += 1
            return SNIL
    
        def feature_SNCL(link):
            SNCL = 0
            
            words = link["label"].split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    if ngram in self.ngram_in_title:
                        SNCL += self.ngram_in_title[ngram]
            return SNCL
            
        feature_functions = [str(feature) for feature in locals()]
        
        # N-gram features
        features = {}
        for feature in feature_functions:
            if feature in ["link", "self"]: continue
            assert str(feature).startswith('feature_')
            feature_name = str(feature)[8:]
            features[feature_name] = eval(feature + "(link)")
    
        return features
        
class conceptFeatures:
    def __init__(self, langcode, wikipediaminer_root, article_url):
        pickle_root = '/scratch/dodijk/flask-semanticizer/pickles/%s/' % langcode
        
        self.load_category_parents(wikipediaminer_root + "categoryParents.csv")     

        self.category_depth_cache = shelve.open(pickle_root+'category_depth_cache.db')
        print "Loaded %d category depths from cache." % len(self.category_depth_cache)

        self.ARTICLE_URL = article_url
        self.WIKIPEDIA_ID = wikipediaminer_root.split('/')[-2]
        self.article_cache = shelve.open(pickle_root+'article_cache.db')
        print "Loaded %d articles from cache." % len(self.article_cache)
        
    def compute_concept_features(self, article):
        def feature_INLINKS(article):
            for child in article:
                if child.tag == "InLinks":
                    return int(child.attrib["total"])
            return 0
            
        def feature_OUTLINKS(article):
            for child in article:
                if child.tag == "OutLinks":
                    return int(child.attrib["total"])
            return 0
            
    #   def feature_CAT(article):
    #       for child in article:
    #           if child.tag == "ParentCategories":
    #               return int(child.attrib["total"])
    #       return 0
            
        def feature_GEN(article):
            for child in article:
                if child.tag == "ParentCategories":
                    depth = 999
                    for cat in child:
                        depth = min(self.category_depth(int(cat.attrib["id"])), depth)
                    return depth
            return 999
                    
        def feature_REDIRECT(article):
            redirect = 0
            for child in article:
                if child.tag == "Labels":
                    for label in child:
                        # Should be fromRedirect but bug in Wikipedia Miner
                        if label.attrib["fromTitle"] == "true":
                            redirect += 1
            return redirect
    
        feature_functions = [str(feature) for feature in locals()]  
        features = {}
        for feature in feature_functions:
            if feature in ["link", "article", "self"]: continue
            assert str(feature).startswith('feature_')
            feature_name = str(feature)[8:]
            features[feature_name] = eval(feature + "(article)")
    
        return features
        
    def load_category_parents(self, filename):
        self.category_parents = {}
        print "Loading category parents...", 
        file = open(filename, 'r')
        for line in file:
            line = line.replace('v{', '').replace('}\n', '')
            ids = line.split(',')
            category_id = int(ids[0])
            self.category_parents[category_id] = []
            for parent_id in ids[1:]:
                self.category_parents[category_id].append(int(parent_id))
        print "done"
        return self.category_parents
    
    def category_depth(self, category_id):
        if str(category_id) in self.category_depth_cache:
           return self.category_depth_cache[str(category_id)]
        else:
            depth = self.shortest_tree([[category_id]])
            self.category_depth_cache[str(category_id)] = depth
            return depth

    def shortest_tree(self, trees):
        assert len(trees), "No more trees."
        assert len(trees) < 5000, "Too many trees."
        assert len(trees[0]) < 50, "Trees are too long."
    
        new_trees = []
        for tree in trees:
            category_id = tree[-1]
            if not self.category_parents.has_key(category_id):
                # Shortest tree found!
                return len(tree)
            
            assert len(self.category_parents[category_id])
            for parent_id in self.category_parents[category_id]:
                if parent_id in tree: continue # Prevent recursive tree
                new_tree = []
                new_tree.extend(tree)
                new_tree.append(parent_id)
                new_trees.append(new_tree)
    
        return self.shortest_tree(new_trees)
        
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
            import urllib, urllib2
            url = self.ARTICLE_URL + "?"
            url += urllib.urlencode({"wikipedia": self.WIKIPEDIA_ID, 
                                     "title": article, 
                                     "definition": "true", "definitionLength":"LONG",
                                     "linkRelatedness": True, "linkFormat":"HTML", 
                                     "inLinks": "true", "outLinks": "true",
                                     "labels": "true", "parentCategories": "true"})            

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
        
        from lxml import etree as ElementTree
        result = ElementTree.fromstring(resultDoc).find("Response")
        
        if not result.attrib.has_key("title"):
            print "Error", result.attrib["error"]
            if 'url' in locals(): print url
        else:
            assert article.decode("utf-8")==result.attrib["title"], \
                "%s!=%s" % (article.decode("utf-8"), result.attrib["title"])
    
        return result

class anchorConceptFeatures:
    def compute_anchor_concept_features(self, link, article):
        features = {}
    
        def feature_TF(link, article):
            text = " "
            for child in article:
                if child.tag == "Definition":
                    from re import sub
                    if child.text and len(child.text):
                        text = sub(r"<.*?>", "", child.text)
                        text = sub(r"^[|\- }]*", "", text)
                    break
                    
            features["TF_title"] = float(link["title"].count(link["label"]))/len(link["title"])
            while len(text) and text[0] == ".":
                text = text[1:].strip()
            sentence = text.split('.')[0]
            if len(sentence) > 0:
                features["TF_sentence"] = float(sentence.count(link["label"]))/len(sentence)
            else:
                features["TF_sentence"] = 0
            if len(text) > 0:
                features["TF_paragraph"] = float(text.count(link["label"]))/len(text)
            else:
                features["TF_paragraph"] = 0
            if text.count(link["label"]):
                features["POS_first_in_paragraph"] = float(text.index(link["label"]))/len(text)
            else:
                features["POS_first_in_paragraph"] = 1
    
        feature_TF(link, article)
    
        def feature_TITLE(link):
            features["NCT"] = 1 if link["label"].count(link["title"]) > 0 else 0
            features["TCN"] = 1 if link["title"].count(link["label"]) > 0 else 0
            features["TEN"] = 1 if link["title"] == link["label"] else 0
        feature_TITLE(link)
    
        def feature_COMMONNESS(link):
            features["COMMONNESS"] = link["commonness"]
        feature_COMMONNESS(link)
        
    #   def feature_SENSES(sense):
    #       features["SENSES"] = len(link["senses"])
    #   feature_SENSES(sense)
        
        return features

class statisticsFeatures:
    def __init__(self, langcode):
        pickle_root = '/scratch/dodijk/flask-semanticizer/pickles/%s/' % langcode
        
        self.WIKIPEDIA_STATS_URL = "http://stats.grok.se/json/"+langcode+"/%d%02d/%s" # 201001/De%20Jakhalzen
        self.wikipedia_statistics_cache = shelve.open(pickle_root+'wikipedia_statistics_cache.db')
        print "Loaded %d sets of statistics from cache." % len(self.wikipedia_statistics_cache)
        
    def compute_statistics_features(self, article, now=datetime.now()):
        features = {"WIKISTATSDAY": 0, "WIKISTATSWK": 0, "WIKISTATS4WK": 0, "WIKISTATSYEAR": 0,
    #               "WIKISTATSWKOFYEAR": 0, "WIKISTATSDAYOF4WK": 0, "WIKISTATSDAYOFYEAR": 0, 
                    "WIKISTATSDAYOFWK": 0, "WIKISTATSWKOF4WK": 0, "WIKISTATS4WKOFYEAR": 0}
    
        date_format = "%d-%02d-%02d"
        
        def feature_WIKISTATSDAY(datetime, article):    
            day = now
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year, day.month, article)
            views = monthly_views["daily_views"][date_format % (day.year, day.month, day.day)]
            features["WIKISTATSDAY"] = views
    
        def feature_WIKISTATSWK(datetime, article): 
            day = now
            for n in range(7):
                day += timedelta(days=-1)
                monthly_views = self.wikipedia_page_views(day.year, day.month, article)
                views = monthly_views["daily_views"][date_format % (day.year, day.month, day.day)]
                features["WIKISTATSWK"] += views
        def feature_WIKISTATS4WK(datetime, article):
            day = now
            for n in range(28):
                day += timedelta(days=-1)
                monthly_views = self.wikipedia_page_views(day.year, day.month, article)
                views = monthly_views["daily_views"][date_format % (day.year, day.month, day.day)]
                features["WIKISTATS4WK"] += views
        def feature_WIKISTATSYEAR(datetime, article):
            day = now
            for n in range(365):
                day += timedelta(days=-1)
                monthly_views = self.wikipedia_page_views(day.year, day.month, article)
                views = monthly_views["daily_views"][date_format % (day.year, day.month, day.day)]
                features["WIKISTATSYEAR"] += views
        feature_WIKISTATSDAY(datetime, article)
        feature_WIKISTATSWK(datetime, article)
        feature_WIKISTATS4WK(datetime, article)
        feature_WIKISTATSYEAR(datetime, article)
    
        def feature_WIKISTATSTRENDS():          
            if features["WIKISTATSWK"] > 0:
                features["WIKISTATSDAYOFWK"] = float(features["WIKISTATSDAY"])/features["WIKISTATSWK"]
            if features["WIKISTATS4WK"] > 0:
    #           features["WIKISTATSDAYOF4WK"] = float(features["WIKISTATSDAY"])/features["WIKISTATS4WK"]
                features["WIKISTATSWKOF4WK"] = float(features["WIKISTATSWK"])/features["WIKISTATS4WK"]
            if features["WIKISTATSYEAR"] > 0:
    #           features["WIKISTATSDAYOFYEAR"] = float(features["WIKISTATSDAY"])/features["WIKISTATSYEAR"]
    #           features["WIKISTATSWKOFYEAR"] = float(features["WIKISTATSWK"])/features["WIKISTATSYEAR"]
                features["WIKISTATS4WKOFYEAR"] = float(features["WIKISTATS4WK"])/features["WIKISTATSYEAR"]
        feature_WIKISTATSTRENDS()
        del features["WIKISTATSDAY"]
        
        return features

    def wikipedia_page_views(self, year, month, article):
        url = self.WIKIPEDIA_STATS_URL % (year, month, article)
        url = url.encode('utf-8')
        if self.wikipedia_statistics_cache.has_key(url):
            resultJson = self.wikipedia_statistics_cache[url]
        else:
            import urllib, urllib2      
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
        
        from json import loads
        result = loads(resultJson)
        
        return result

    def cache_wikipedia_page_views(self, articles, num_of_threads, now=datetime.now()):
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
