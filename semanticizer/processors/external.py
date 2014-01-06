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

from Queue import Queue, Empty
from threading import Thread

import urllib2

import datetime
import shelve
import os
from copy import deepcopy

from .core import LinksProcessor
from ..wpm.data import wpm_dumps
from ..wpm.utils import get_relatedness


class ArticlesProcessor(LinksProcessor):
    def __init__(self, langcodes, pickledir):
        self.langcodes = langcodes
        self.article_cache = {}

        for langcode in langcodes:
            pickle_root = os.path.join(pickledir, langcode)
            if not os.path.isdir(pickle_root):
                os.makedirs(pickle_root)
            self.article_cache[langcode] = \
                shelve.open(os.path.join(pickle_root, 'article_cache.db'))
            print "Loaded %d articles for %s from cache." \
                  % (len(self.article_cache[langcode]), langcode)

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
        if not "article" in settings and not "features" in settings and not \
               "learning" in settings and "multi" not in settings:
            return (links, text, settings)
        if not settings["langcode"] in self.langcodes:
            return (links, text, settings)

        return (links, text, settings)

    def process(self, links, text, settings):
        if not "article" in settings and not "features" in settings and not \
               "learning" in settings:
            return (links, text, settings)
        if not settings["langcode"] in self.langcodes:
            return (links, text, settings)
        
        wpm = wpm_dumps[langcode]
        for link in links:
            
            link.update(deepcopy(self.article_template))

            link["article_title"] = link["title"]
            
            id = wpm.get_item_id(link["title"])
            if id:
                link["article_id"] = id
            
            inlinks = wpm.get_item_inlinks( link["article_id"] )
            if inlinks:
                for inlink in inlinks:
                    # below data is not used, for now only append inlink id to reduce load on db
                    #title = wpm.get_item_title(inlink)
                    #relatedness = get_relatedness(inlinks, wpm.get_item_inlinks(inlink) )
                    #link["InLinks"].append( {title:title, id:int(inlink), relatedness:relatedness} )
                    link["InLinks"].append( { id:int(inlink) } )
            
            if outlinks:
                for outlink in outlinks:
                    # below data is not used, for now only append inlink id to reduce load on db
                    #title = wpm.get_item_title(outlink)
                    #relatedness = get_relatedness(outlinks, wpm.get_item_outlinks(outlin) )
                    #link["OutLinks"].append( {title:title, id:int(outlink), relatedness:relatedness} )
                    link["OutLinks"].append( { id:int(outlink) } )

            #categories = wpm.get_item_categories( link["article_id"] )
            #if categories:
            #    for category in categories:
            #        title = wpm.get_item_title(category)
            #        link["ParentCategories"].append( {title:title, id:int(category)} )

            #definition = wpm.get_item_definitions(link["article_id"])
            #if definition:
            #    link["Definition"] = definition
            
            labels = wpm.get_item_labels(link["article_id"])
            if labels:
                link["Labels"] = labels

        for langcode, cache in self.article_cache.iteritems():
            print "Saving %d articles for %s to cache." \
                   % (len(cache), langcode)
            cache.sync()

        return (links, text, settings)

    def postprocess(self, links, text, settings):
        if "article" in settings and len(settings["article"]) == 0:
            return (links, text, settings)
        remove = [key.lower() for key in self.article_template.keys()]
        remove.extend(["fromtitle", "fromredirect"])
        if "article" in settings:
            for label in settings["article"].replace(";", ",").split(","):
                if label.lower() in remove:
                    remove.remove(label)
        for link in links:
            for label in link.keys():
                if label.lower() in remove:
                    del link[label]

        return (links, text, settings)


class StatisticsProcessor(LinksProcessor):
    def __init__(self, langcodes, num_of_threads, pickledir):
        self.num_of_threads = num_of_threads
        self.WIKIPEDIA_STATS_URL = {}
        self.wikipedia_statistics_cache = {}
        for langcode in langcodes:
            self.WIKIPEDIA_STATS_URL[langcode] = \
                          "http://stats.grok.se/json/" \
                          + langcode \
                          + "/%d%02d/%s"  # 201001/De%20Jakhalzen

            pickle_root = os.path.join(pickledir, langcode)
            if not os.path.isdir(pickle_root):
                os.makedirs(pickle_root)
            self.wikipedia_statistics_cache[langcode] = \
                shelve.open(os.path.join(pickle_root, \
                                         'wikipedia_statistics_cache.db'))
            print "Loaded %d sets of statistics for %s from cache." \
                  % (len(self.wikipedia_statistics_cache[langcode]), langcode)

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
                    self.wikipedia_page_views(year, month,
                                              article, settings["langcode"])
                    queue.task_done()
                except Empty:
                    break

        queue = Queue()
        for _ in set([link["title"] for link in links]):
            day = now
            for _ in range(14):
                self.queue.put((day.year, day.month, article))
                day += timedelta(days=28)

        for _ in range(self.num_of_threads):
            t = Thread(target=worker)
            t.daemon = True
            t.start()

    def process(self, links, text, settings):
        if "wikistats" not in settings:
            return (links, text, settings)

        now = self.get_timestamp(settings)

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
            print "Saving %d sets of statistics for %s from cache." \
                  % (len(cache), langcode)
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
        if url in self.wikipedia_statistics_cache[langcode]:
            resultJson = self.wikipedia_statistics_cache[langcode][url]
        else:
            try:
                request = urllib2.urlopen(url, timeout=1)
                resultJson = request.read()
            except urllib2.URLError:
                try:
                    request = urllib2.urlopen(url)
                    resultJson = request.read()
                except urllib2.URLError:
                    request = urllib2.urlopen(url)
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
                                             (day.year, day.month, day.day)]
        features["WIKISTATSDAY"] = views

    def feature_WIKISTATSWK(self, datetime, article, features, now):
        day = now
        for _ in range(7):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = \
                  monthly_views["daily_views"][self.date_format % \
                                               (day.year, day.month, day.day)]
            features["WIKISTATSWK"] += views

    def feature_WIKISTATS4WK(self, datetime, article, features, now):
        day = now
        for _ in range(28):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = monthly_views["daily_views"][self.date_format % \
                                                (day.year, day.month, day.day)]
            features["WIKISTATS4WK"] += views

    def feature_WIKISTATSYEAR(self, datetime, article, features, now):
        day = now
        for _ in range(365):
            day += timedelta(days=-1)
            monthly_views = self.wikipedia_page_views(day.year,
                                                      day.month, article)
            views = monthly_views["daily_views"][self.date_format % \
                                                (day.year, day.month, day.day)]
            features["WIKISTATSYEAR"] += views

    def feature_WIKISTATSTRENDS(self, features):
        if features["WIKISTATSWK"] > 0:
            features["WIKISTATSDAYOFWK"] = \
                    float(features["WIKISTATSDAY"]) / features["WIKISTATSWK"]
        if features["WIKISTATS4WK"] > 0:
            features["WIKISTATSWKOF4WK"] = \
                    float(features["WIKISTATSWK"]) / features["WIKISTATS4WK"]
        if features["WIKISTATSYEAR"] > 0:
            features["WIKISTATS4WKOFYEAR"] = \
                    float(features["WIKISTATS4WK"]) / features["WIKISTATSYEAR"]
