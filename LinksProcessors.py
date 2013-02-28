from semanticizer import Semanticizer
import features
import context
from wikipedia_images import add_image_url
from ilps_semanticizer import ILPSSemanticizer

class LinksProcessor:
    '''A LinksProcessor takes a set of links, a text and a language code to 
       produce or process links. Processing is done in two steps, a preprocessing
       step and a processing step. '''
       
    def preprocess(self, links, text, settings):
        return (links, text, settings)
        
    def process(self, links, text, settings):
        return (links, text, settings)

    def postprocess(self, links, text, settings):
        return (links, text, settings)
        
    def inspect(self):
        return {}

class SettingsProcessor(LinksProcessor):
    def __init__(self):
        self.settings = {
            "vara": {
                "pre_filter": "unique,sense_probability>0.01",
                "learning": "coling-SP0.2-100.RandomForestClassifier-10-auto.pkl",
                "filter": "unique,learning_probability>=0.5"
            }}
    def preprocess(self, links, text, settings):
        if "settings" in settings and settings["settings"] in self.settings:
            for k, v in self.settings[settings["settings"]].iteritems():
                if k not in settings:
                    settings[k] = v
            del settings["settings"]
        return (links, text, settings)
    def inspect(self):
        return {self.__class__.__name__: self.settings}
                
class SemanticizeProcessor(LinksProcessor):
    def __init__(self):
        self.languages = {}
        self.semanticizers = {}
        self.ilps_semanticizers = {}

    def load_languages(self, languages):
        for lang, langcode, loc in languages:
            self.languages[langcode] = (lang, loc)
            self.semanticizers[langcode] = Semanticizer(langcode, loc)
            self.ilps_semanticizers[langcode] = ILPSSemanticizer(langcode, loc)
            
    def preprocess(self, links, text, settings):
        links = []
        if settings.has_key("langcode"): 
            if "semanticizer" in settings and settings["semanticizer"] == "ilps":
                if self.ilps_semanticizers.has_key(settings["langcode"]): 
                    links = self.ilps_semanticizers[settings["langcode"]].semanticize(text)
            else:
                if self.semanticizers.has_key(settings["langcode"]): 
                    translations = settings.has_key("translations")
                    results = self.semanticizers[settings["langcode"]] \
                                .semanticize(text, counts=True, \
                                             translations=translations, \
                                             senseprobthreshold=-1)
                    links = results["links"]
                else:
                    links = []
            
        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.languages}

class FilterProcessor(LinksProcessor):
    def __init__(self):
        self.context_links = {}

    def preprocess(self, links, text, settings):
        if settings.has_key("prefilter"):
            links = self.filter_links(settings["prefilter"].split(","), links, settings)

        return (links, text, settings)

    def postprocess(self, links, text, settings):
        if settings.has_key("filter"):
            links = self.filter_links(settings["filter"].split(","), links, settings)

        return (links, text, settings)
    
    def filter_links(self, filters, links, settings):
        filters_gte = [filter.split(">=") for filter in filters if ">=" in filter]
        filters_gt = [filter.split(">") for filter in filters \
                      if ">" in filter and not ">=" in filter]
    
        filter_unique = ("unique" in filters) and settings.has_key("context")
    
        if len(filters_gte) == 0 and len(filters_gt) == 0 and not filter_unique: 
           return links
    
        filtered_links = []
        for link in links:
            skip = False
            for filter in filters_gte:
                if not link[filter[0]] >= float(filter[1]):
                    skip = True
                    break
            else:
                for filter in filters_gt:
                    if not link[filter[0]] > float(filter[1]):
                        skip = True
                        break
    
            if filter_unique:
                self.context_links.setdefault(settings["context"], {})
                if link["title"] in self.context_links[settings["context"]]:
                    skip = True
    
            if not skip:
                filtered_links.append(link)
    
                if filter_unique:
                    self.context_links[settings["context"]][link["title"]] = link
                
        print "Filtered %d links to %d" % (len(links), len(filtered_links))
    
        return filtered_links

    def inspect(self):
        return {self.__class__.__name__: self.context_links}

class FeaturesProcessor(LinksProcessor):
    def __init__(self, semanticizer_processor, article_url, threads):
        self.threads = threads
        self.feature_classes = {}
        
        semanticizers = {}
        for langcode, semanticizer in semanticizer_processor.semanticizers.iteritems():
            semanticizers[langcode] = (semanticizer.wikipediaminer_root, semanticizer.title_page)
        for langcode, semanticizer in semanticizer_processor.ilps_semanticizers.iteritems():
            if langcode not in semanticizers:
                semanticizers[langcode] = (semanticizer.wikipediaminer_root, None)
        
        for langcode, (loc, title_page) in semanticizers.iteritems():
            anchor_features = features.anchorFeatures(langcode, loc, title_page)
            self.feature_classes[langcode] = {
                "anchor": anchor_features,
                "concept": features.conceptFeatures(langcode, loc, article_url),
                "anchor_concept": features.anchorConceptFeatures(),
                "statistics": features.statisticsFeatures(langcode),
            }

    def process(self, links, text, settings):
        if not settings.has_key("features") and not settings.has_key("learning"):
            return (links, text, settings)
        if not self.feature_classes.has_key(settings["langcode"]):
            return (links, text, settings)

        featuresets = self.feature_classes[settings["langcode"]]
        # Start threads
        (articles, article_queue) = featuresets["concept"].get_articles(links, self.threads)
        if "wikistats" in settings:
            import datetime
            # Should be more robust against unexpected values
            if len(settings["wikistats"]) > 0:
                timestamp = datetime.datetime.fromtimestamp(int(settings["wikistats"]))
            else:
                timestamp = datetime.now()

            statistics_queue = featureset["statistics"].cache_wikipedia_page_views(links, self.threads, timestamp)
            
        for link in links:
            link["features"] = featuresets["anchor"].compute_anchor_features(link)
        article_queue.join()
        for link in links:
            article = articles[link["title"]]
            link["features"].update(featuresets["concept"].compute_concept_features(article))
            link["features"].update(featuresets["anchor_concept"].compute_anchor_concept_features(link, article))
        if "wikistats" in settings:
            statistics_queue.join()
            for link in links:
                link["features"].update(featuresets["statistics"].compute_statistics_features(link["title"], timestamp))
                
        print "Syncing %d category depths for cache." % len(featuresets["concept"].category_depth_cache)
        featuresets["concept"].category_depth_cache.sync()
        print "Syncing %d articles for cache." % len(featuresets["concept"].article_cache)
        featuresets["concept"].article_cache.sync()
        
        print "Sync %d sets of statistics for cache." % len(featuresets["statistics"].wikipedia_statistics_cache)
        featuresets["statistics"].wikipedia_statistics_cache.sync()
            
        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: [(lang, classes.keys()) for (lang, classes) in self.feature_classes.iteritems()]}

class ContextFeaturesProcessor(LinksProcessor):
    def __init__(self):
        self.context_features = {}

    def new_context(self, context_label):
        self.context_features[context_label] = {
            "SP0.2-100": context.contextGraph("SP0.2-100", "sense_probability", 0.2, 100)
        }

    def process(self, links, text, settings):
        if not settings.has_key("features") and not settings.has_key("learning"):
            return (links, text, settings)

        if "context" in settings:
            if settings["context"] not in self.context_features:
                self.new_context(settings["context"])
            for label in self.context_features[settings["context"]]:
                self.context_features[settings["context"]][label].add_chunk()
                for link in links:
                    self.context_features[settings["context"]][label].add_link(link)
                self.context_features[settings["context"]][label].prepare_features()

        if "context" in settings:
            for label in self.context_features[settings["context"]]:
                for link in links:
                    link["features"].update(self.context_features[settings["context"]][label].compute_features(link["title"]))
            
        return (links, text, settings)

    def inspect(self):
        context = {}
        for context_label, features in self.context_features.iteritems():
            context[context_label] = {}
            for label, context_graph in features.iteritems():
                graph = {"page_ranked": context_graph.page_ranked,
                         "graph": context_graph.to_dict_of_dicts(),
                         "chunk": context_graph.chunk}
                context[context_label][label] = graph

        return {self.__class__.__name__: context}

class LearningProcessor(LinksProcessor):
    def __init__(self, scikit_url=None):
        self.scikit_url = scikit_url
        if scikit_url == None:
            import scikit_light

    def process(self, links, text, settings):
        if "learning" in settings:
            links = self.apply_learning(settings["learning"], links, settings.has_key("features"))
        return (links, text, settings)

    def apply_learning(self, model, links, keep_features):
        if len(links) == 0:
            return links

        features = sorted(links[0]["features"].keys())
        
        if self.scikit_url == None:            
            import scikit_light

            testfeatures = []
            for link in links:
                linkfeatures = []
                for feature in features:
                    linkfeatures.append(link["features"][feature])
                testfeatures.append(linkfeatures)
                
            scores = scikit_light.predict(model, testfeatures)
            for link, score in zip(links, scores):
                link["learning_probability"] = score[1]
                if not keep_features:
                    del link["features"]

        else:
            data = ""
            for link in links:
                data += "-1 qid:0"
                for index, feature in enumerate(features):
                    data += " %d:%f" % (index, link["features"][feature])
                data += "\n"
                
            import urllib, urllib2
            url = self.scikit_url + "/predict/" + model
            request = urllib2.urlopen(urllib2.Request(url, data, {"Content-Type": "text/plain"}))
            scores = request.read().split('\n')
            for link, score in zip(links, scores):
                if len(score) == 0 or " " not in score: score = "0 0"
                link["learning_probability"] = float(score.split()[1])
                if not keep_features:
                    del link["features"]
        
        return links

class AddImageProcessor(LinksProcessor):
    def postprocess(self, links, text, settings):
        if "image" in settings and "langcode" in settings:
            links = add_image_url(links, settings["langcode"])
        return (links, text, settings)
