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

from core import LinksProcessor


class LearningProcessor(LinksProcessor):
    def __init__(self, scikit_url=None):
        self.scikit_url = scikit_url

    def process(self, links, text, settings):
        if "learning" in settings:
            links = self.apply_learning(settings["learning"],
                                        links,
                                        "features" in settings)
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

            import urllib2
            url = self.scikit_url + "/predict/" + model
            request = urllib2.urlopen(urllib2.Request(url, data, {"Content-Type": "text/plain"}))
            scores = request.read().split('\n')
            for link, score in zip(links, scores):
                if len(score) == 0 or " " not in score:
                    score = "0 0"
                link["learning_probability"] = float(score.split()[1])
                if not keep_features:
                    del link["features"]

        return links
