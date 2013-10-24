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

from collections import defaultdict

from . import feature as features
from . import context

from .core import LinksProcessor

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
        return {self.__class__.__name__: str(self.features)}


class ContextFeaturesProcessor(LinksProcessor):
    def __init__(self):
        self.context_features = {}
        self.context_text = defaultdict(list)
        self.context_id_pattern = "%s:%d"

    def new_context(self, context_label):
        self.context_features[context_label] = {
            "SP0.2-100": context.contextGraph("SP0.2-100", "senseProbability",
                                              0.2, 100)
        }

    def preprocess(self, links, text, settings):
        if "context" in settings:
            settings["context_id"] = self.context_id_pattern % \
                (settings["context"], len(self.context_text[settings["context"]]))
            self.context_text[settings["context"]].append(text)

        return (links, text, settings)

    def process(self, links, text, settings):
        if not "context" in settings or "skip_context_features" in settings or \
          (not "features" in settings and not "learning" in settings):
            return (links, text, settings)

        # Create context_features if it does not exist
        if settings["context"] not in self.context_features:
            self.new_context(settings["context"])

        # For each set of context features
        for label in self.context_features[settings["context"]]:
            # Create a new chunk
            self.context_features[settings["context"]][label].add_chunk()
            graph = self.context_features[settings["context"]][label]
            # Add each link to graph and prepare features
            for link in links:
                graph.add_link(link)
                graph.prepare_features()

            # Compute context features for each link
            for link in links:
                link["features"].update(graph.compute_features(link["title"]))

        return (links, text, settings)

    def inspect(self):
        context = {}
        for context_label, features in self.context_features.iteritems():
            context[context_label] = {"text": self.context_text[context_label]}
            for label, context_graph in features.iteritems():
                graph = {"page_ranked": context_graph.page_ranked,
                         "graph": context_graph.to_dict_of_dicts(),
                         "chunk": context_graph.chunk}
                context[context_label][label] = graph

        return {self.__class__.__name__: context}
