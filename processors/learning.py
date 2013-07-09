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

from sklearn.externals import joblib

import os, yaml, warnings

class LearningProcessor(LinksProcessor):
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model_cache = {}

    def process(self, links, text, settings):
        if "learning" in settings:
            links = self.apply_learning(settings,
                                        links,
                                        "features" in settings)
        return (links, text, settings)
        
    def load_model(self, modelname):
        if modelname in self.model_cache:
            return self.model_cache[modelname]
        
        modelfile = os.path.join(self.model_dir, modelname)
        if modelfile.endswith(".pkl"):
            modelfile = modelfile[:-4]
            
        model = joblib.load(modelfile + ".pkl")

        description = {"name": modelname, "source": modelfile + ".pkl"}
        if os.path.exists(modelfile + ".yaml"):
            description.update(yaml.load(file(modelfile + ".yaml")))
            
        self.model_cache[modelname] = (model, description)
        return (model, description)
        
    def predict(self, classifier, testfeatures):
        print("Start predicting of %d instances with %d features."
              % (len(testfeatures), len(testfeatures[0])))
        predict = classifier.predict_proba(testfeatures)
        print("Done predicting of %d instances." % len(predict))

        return predict    

    def apply_learning(self, settings, links, keep_features):
        if len(links) == 0:
            return links
            
        modelname = settings["learning"]
        (model, description) = self.load_model(modelname)
        print("Loaded classifier from %s" % description["source"])

        if "language" in description:
            assert settings["langcode"] == description["language"], \
                "Language of model and data do not match."
        
        features = sorted(links[0]["features"].keys())
        
        if "features" in description:
            missing_features = set(description["features"]) - set(features)
            if(len(missing_features)):
                warn = RuntimeWarning("Missing %d features for model %s: %s "
                                      % (len(missing_features), 
                                         description["name"],
                                         ", ".join(missing_features)))
                
                if "missing" in settings:
                    warnings.warn(warn)
                else:
                    raise warn

            features = sorted(description["features"])
        
        if model.n_features_ != len(features):
            raise ValueError("Number of features of the model must "
                             " match the input. Model n_features is %s and "
                             " input n_features is %s "
                             % (model.n_features_, len(features)))

        testfeatures = []
        for link in links:
            linkfeatures = []
            for feature in features:
                if feature in link["features"]:
                    linkfeatures.append(link["features"][feature])
                else:
                    linkfeatures.append(None)
            testfeatures.append(linkfeatures)

        scores = self.predict(model, testfeatures)
        for link, score in zip(links, scores):
            link["learning_probability"] = score[1]
            if not keep_features:
                del link["features"]

        return links

# Old code for using a remote scikit server.
# 
#     data = ""
#     for link in links:
#         data += "-1 qid:0"
#         for index, feature in enumerate(features):
#             data += " %d:%f" % (index, link["features"][feature])
#         data += "\n"
# 
#     import urllib2
#     url = self.scikit_url + "/predict/" + model
#     request = urllib2.urlopen(urllib2.Request(url, data, {"Content-Type": "text/plain"}))
#     scores = request.read().split('\n')
#     for link, score in zip(links, scores):
#         if len(score) == 0 or " " not in score:
#             score = "0 0"
#         link["learning_probability"] = float(score.split()[1])
#         if not keep_features:
#             del link["features"]
