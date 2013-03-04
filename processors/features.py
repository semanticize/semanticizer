import feature as features
import context

from core import LinksProcessor

class FeaturesProcessor(LinksProcessor):
    def __init__(self, semanticizer_processor):
        self.features = {}
        
        semanticizers = {}
        for langcode, semanticizer in semanticizer_processor.semanticizers.iteritems():
            semanticizers[langcode] = (semanticizer.wikipediaminer_root, semanticizer.title_page)
        
        for langcode, (loc, title_page) in semanticizers.iteritems():
            self.features[langcode] = features.anchorFeatures(langcode, loc, title_page)

    def process(self, links, text, settings):
        if not settings.has_key("features") and not settings.has_key("learning"):
            return (links, text, settings)
        if not self.features.has_key(settings["langcode"]):
            return (links, text, settings)
            
        featuresets = self.features[settings["langcode"]]

        for link in links:
            link.setdefault("features", {})
            link["features"].update(featuresets.compute_anchor_features(link))
                            
        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.features.keys()}
        
class ArticleFeaturesProcessor(LinksProcessor):
    def __init__(self):
        self.features = features.articleFeatures()

    def process(self, links, text, settings):
        if not settings.has_key("features") and not settings.has_key("learning"):
            return (links, text, settings)
        # Check if ArticleProcessor has run
            
        for link in links:
            link.setdefault("features", {})
            link["features"].update(self.features.compute_article_features(link))
                            
        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.features.__name__}

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
