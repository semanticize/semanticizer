import feature as features
import context

from core import LinksProcessor

class FeaturesProcessor(LinksProcessor):
    def __init__(self, semanticizer_processor, article_url, threads):
        self.threads = threads
        self.feature_classes = {}
        
        semanticizers = {}
        for langcode, semanticizer in semanticizer_processor.semanticizers.iteritems():
            semanticizers[langcode] = (semanticizer.wikipediaminer_root, semanticizer.title_page)
        
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
