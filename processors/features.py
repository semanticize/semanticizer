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

import processors.feature as features
import processors.context as context

from processors.core import LinksProcessor


class FeaturesProcessor(LinksProcessor):
    def __init__(self, langcodes):
        self.features = {}
        for langcode in langcodes:
            self.features[langcode] = features.anchorFeatures(langcode)

    def process(self, links, text, settings):
        if not "features" in settings and not "learning" in settings:
            return (links, text, settings)
        if not settings["langcode"] in self.features:
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
        if not "features" in settings and not "learning" in settings:
            return (links, text, settings)
        # Check if ArticleProcessor has run

        for link in links:
            link.setdefault("features", {})
            link["features"].update(
                self.features.compute_article_features(link)
            )

        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.features.__name__}


class ContextFeaturesProcessor(LinksProcessor):
    def __init__(self):
        self.context_features = {}

    def new_context(self, context_label):
        self.context_features[context_label] = {
            "SP0.2-100": context.contextGraph("SP0.2-100", "senseProbability",
                                              0.2, 100)
        }

    def process(self, links, text, settings):
        if not "features" in settings and not "learning" in settings:
            return (links, text, settings)

        if "context" in settings:
            if settings["context"] not in self.context_features:
                self.new_context(settings["context"])
            for label in self.context_features[settings["context"]]:
                self.context_features[settings["context"]][label].add_chunk()
                for link in links:
                    self.context_features[
                            settings["context"]
                         ][label].add_link(link)
                self.context_features[
                        settings["context"]
                     ][label].prepare_features()

        if "context" in settings:
            for label in self.context_features[settings["context"]]:
                for link in links:
                    link["features"].update(self.context_features[settings["context"]][label].compute_features(link["title"]))

        return (links, text, settings)

    def inspect(self):
        cntxt = {}
        for context_label, features in self.context_features.iteritems():
            cntxt[context_label] = {}
            for label, context_graph in features.iteritems():
                graph = {"page_ranked": context_graph.page_ranked,
                         "graph": context_graph.to_dict_of_dicts(),
                         "chunk": context_graph.chunk}
                cntxt[context_label][label] = graph

        return {self.__class__.__name__: cntxt}
