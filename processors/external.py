from core import LinksProcessor

from Queue import Queue, Empty
from threading import Thread

import urllib, urllib2
from lxml import etree as ElementTree

import datetime
import shelve
from copy import deepcopy

class ArticlesProcessor(LinksProcessor):
    def __init__(self, wikipedia_ids, article_url, threads, pickledir):
        self.threads = threads
        self.article_url = article_url
        self.wikipedia_ids = wikipedia_ids
        self.article_cache = {}
        
        for langcode in self.wikipedia_ids:
            pickle_root = pickledir + '/' + langcode + '/'
            self.article_cache[langcode] = shelve.open(pickle_root+'article_cache.db')
            print "Loaded %d articles for %s from cache." % (len(self.article_cache[langcode]), langcode)
            
        self.article_template = {
            "article_id": -1,
            "article_title": "",
            "Definition": "",
            "InLinks": [],
            "OutLinks": [],
            "Labels": [],
            "Images": [],
            "ParentCategories": []
        }

    def preprocess(self, links, text, settings):
        if not "article" in settings and not "features" in settings and not "learning" in settings:
             return (links, text, settings)
        if not self.wikipedia_ids.has_key(settings["langcode"]):
            return (links, text, settings)

        # Start threads
        (self.articles, self.queue) = self.get_articles(links, settings["langcode"], self.threads)

        return (links, text, settings)

    def process(self, links, text, settings):
        if not "article" in settings and not "features" in settings and not "learning" in settings:
             return (links, text, settings)
        if not self.wikipedia_ids.has_key(settings["langcode"]):
            return (links, text, settings)

        self.queue.join()
        for link in links:
            article = self.articles[link["title"]]
            
            link.update(deepcopy(self.article_template))
            
            if "id" in article.attrib:
                link["article_id"] = int(article.attrib["id"])
            if "title" in article.attrib:
                link["article_title"] = article.attrib["title"]
            
            for child in article:
                if child.tag in ('InLinks', 'OutLinks', 'ParentCategories'):
                    for linktag in child:
                        link[child.tag].append(dict(linktag.attrib))
                        if "id" in link[child.tag][-1]: 
                            link[child.tag][-1]["id"] = int(link[child.tag][-1]["id"])
                        if "relatedness" in link[child.tag][-1]: 
                            link[child.tag][-1]["relatedness"] = float(link[child.tag][-1]["relatedness"])
                elif child.tag == 'Labels':
                    for labeltag in child:
                        label = {"title": labeltag.text}
                        label.update(labeltag.attrib)
                        if "fromRedirect" in label: label["fromRedirect"] = bool(label["fromRedirect"])
                        if "fromTitle" in label: label["fromTitle"] = bool(label["fromTitle"])
                        if "isPrimary" in label: label["isPrimary"] = bool(label["isPrimary"])
                        if "occurances" in label: label["occurances"] = int(label["occurances"])
                        if "proportion" in label: label["proportion"] = float(label["proportion"])
                        link["Labels"].append(label)
                elif child.tag == "Image":
                    link["Images"].append(child.attrib['url'])
                elif child.tag == "Definition":
                    if child.text and len(child.text):
                        link["Definition"] = child.text

        for langcode, cache in self.article_cache.iteritems():
            print "Saving %d articles for %s to cache." % (len(cache), langcode)
            cache.sync()
                    
        return (links, text, settings)

    def postprocess(self, links, text, settings):
        if "article" in settings and len(settings["article"]) == 0:
             return (links, text, settings)
        remove = self.article_template.keys()
        remove.extend(["fromTitle", "fromRedirect"])
        if "article" in settings:
             for label in settings["article"].replace(";", ",").split(","):
                 if label in remove: remove.remove(label)
        for link in links:
            for label in remove:
                if label in link: del link[label]
                
        return (links, text, settings)

    def get_articles(self, articles, langcode, num_of_threads):
        results = {}
        def worker():
            while True:
                try:
                    item = queue.get_nowait()
                    results[item] = self.get_article(item.encode('utf-8'), langcode)
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
        
    def get_article(self, article, langcode):
        if self.article_cache[langcode].has_key(article):
            resultDoc = self.article_cache[langcode][article]
        else:
            url = self.article_url + "?"
            url += urllib.urlencode({"wikipedia": self.wikipedia_ids[langcode], 
                                     "title": article, 
                                     "definition": "true",
                                     "definitionLength":"LONG",
                                     "linkRelatedness": True,
                                     "linkFormat":"HTML", 
                                     "inLinks": "true",
                                     "outLinks": "true",
                                     "labels": "true",
#                                    "images": "true",
# Images disabled because of a bug in WikipediaMiner
                                     "parentCategories": "true"})            

            print url
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

            self.article_cache[langcode][article] = resultDoc
    
        result = ElementTree.fromstring(resultDoc).find("Response")
    
        if not result.attrib.has_key("title"):
            print "Error", result.attrib["error"]
            if 'url' in locals(): print url
        else:
            if article.decode("utf-8") != result.attrib["title"]:
                print "%s!=%s" % (article.decode("utf-8"), result.attrib["title"])

        return result

class StatisticsProcessor(LinksProcessor):
    def __init__(self, langcodes, num_of_threads, pickledir):
        self.num_of_threads = num_of_threads
        self.WIKIPEDIA_STATS_URL = {}
        self.wikipedia_statistics_cache = {}
        for langcode in langcodes:
            self.WIKIPEDIA_STATS_URL[langcode] = "http://stats.grok.se/json/"+langcode+"/%d%02d/%s" # 201001/De%20Jakhalzen

            pickle_root = pickledir + '/' + langcode + '/'
            self.wikipedia_statistics_cache[langcode] = shelve.open(pickle_root+'wikipedia_statistics_cache.db')
            print "Loaded %d sets of statistics for %s from cache." % (len(self.wikipedia_statistics_cache[langcode]), langcode)

    def inspect(self):
        return {self.__class__.__name__: self.WIKIPEDIA_STATS_URL}
    
    def preprocess(self, links, text, settings):
        if "wikistats" not in settings:
            return (links, text, settings)
        
        now = self.get_timestamp(settings)
        
        def worker():
            while True:
                try:
                    (year, month, article) = queue.get_nowait()
                    self.wikipedia_page_views(year, month, article, settings["langcode"])
                    queue.task_done()
                except Empty:
                    break

        self.queue = Queue()
        for title in set([link["title"] for link in links]):
            day = now
            for i in range(14):
                self.queue.put((day.year, day.month, article))
                day += timedelta(days=28)

        for i in range(self.num_of_threads):
            t = Thread(target=worker)
            t.daemon = True
            t.start()

    def process(self, links, text, settings):
        if "wikistats" not in settings:
            return (links, text, settings)

        now=self.get_timestamp(settings)
        
        self.queue.join()
            
        for link in links:
            features = {"WIKISTATSDAY": 0,
                        "WIKISTATSWK": 0,
                        "WIKISTATS4WK": 0,
                        "WIKISTATSYEAR": 0,
                        "WIKISTATSDAYOFWK": 0,
                        "WIKISTATSWKOF4WK": 0,
                        "WIKISTATS4WKOFYEAR": 0
                        }

            self.feature_WIKISTATSDAY(datetime, link["title"], features, now)
            self.feature_WIKISTATSWK(datetime, link["title"], features, now)
            self.feature_WIKISTATS4WK(datetime, link["title"], features, now)
            self.feature_WIKISTATSYEAR(datetime, link["title"], features, now)
            self.feature_WIKISTATSTRENDS(features)

            del features["WIKISTATSDAY"]

            link["features"].update(features)

        for langcode, cache in self.wikipedia_statistics_cache.iteritems():
            print "Saving %d sets of statistics for %s from cache." % (len(cache), langcode)
            cache.sync()

        return (links, text, settings)

    def get_timestamp(self, settings):
        # Should be more robust against unexpected values
        if len(settings["wikistats"]) > 0:
            return datetime.datetime.fromtimestamp(int(settings["wikistats"]))
        else:
            return datetime.now()

    def wikipedia_page_views(self, year, month, article, langcode):
        url = self.WIKIPEDIA_STATS_URL[langcode] % (year, month, article)
        url = url.encode('utf-8')
        if self.wikipedia_statistics_cache[langcode].has_key(url):
            resultJson = self.wikipedia_statistics_cache[langcode][url]
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

            self.wikipedia_statistics_cache[langcode][url] = resultJson

        from json import loads
        result = loads(resultJson)

        return result
 
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
