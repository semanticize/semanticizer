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
from util import ModelStore, compute_metrics

import warnings

from collections import defaultdict

class LearningProcessor(LinksProcessor):
    def __init__(self, model_dir):
        self.modelStore = ModelStore(model_dir)
        self.history = defaultdict(list)
        self.context_history = defaultdict(list)

    def predict(self, classifier, testfeatures):
        print("Start predicting of %d instances with %d features."
              % (len(testfeatures), len(testfeatures[0])))

        predict = None
        if hasattr(classifier, "predict_proba"):
            try:
                predict = classifier.predict_proba(testfeatures)
            except NotImplementedError:
                predictions = classifier.decision_function(testfeatures)
                predict = [[1-p,p] for p in predictions]

        if predict == None:
            predictions = classifier.predict(testfeatures)
            predict = [[0,1] if p else [1,0] for p in predictions]

        print("Done predicting of %d instances." % len(predict))

        return predict    

    def check_model(self, model, description, features, settings):
        if "language" in description:
            assert settings["langcode"] == description["language"], \
                "Language of model and data do not match."
        
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

        if hasattr(model, "n_features_"):
            model_features = model.n_features_
        elif hasattr(model, "coef_"):
            model_features = model.coef_.shape[1]
        else:
            model_features = None
            
        if model_features and model_features != len(features):
            raise ValueError("Number of features of the model must "
                             "match the input. Model n_features is %s and "
                             "input n_features is %s."
                             % (model.n_features_, len(features)))

        return features

    def process(self, links, text, settings):
        if not "learning" in settings or len(links) == 0:
            return (links, text, settings)
        
        modelname = settings["learning"]
        (model, description) = self.modelStore.load_model(modelname)
        print("Loaded classifier from %s" % description["source"])

        features = sorted(links[0]["features"].keys())        
        features = self.check_model(model, description, features, settings)

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

        return (links, text, settings)

    def postprocess(self, links, text, settings):
        if "save" in settings:
            history = self.history[settings["request_id"]]

        for link in links:
            if "context" in settings:
                link["context"] = settings["context"]
            if "save" in settings:
                history.append(link if "features" in settings else link.copy())
            if "learning" in settings and "features" not in settings:
                del link["features"]

        if "save" in settings and "context" in settings:
            context_history = self.context_history[settings["context"]]
            context_history.append(settings["request_id"])

        return (links, text, settings)

    def inspect(self):
        history = {"history": self.history,
                   "context_history": self.context_history}
        return {self.__class__.__name__: history}

    def feedback(self, request_id, context, feedback):
        if request_id != None:
            request_ids = [request_id]
            if context and request_id not in self.context_history[context]:
                raise ValueError("Request id %s not found in context %s." %
                                 (request_id, context))
        else:
            request_ids = self.context_history[context]
            if len(request_ids) == 0:
                raise ValueError("No requests found for context %s." % context)
        
        print("Received feedback for request_id %s in context %s: %s." %
                              (request_id, context, feedback))
                              
        def process_feedback(link, feedback):
            link["feedback"] = feedback
            print feedback, link["title"]

        for feedback_request_id in request_ids:
            if feedback_request_id not in self.history:
                raise ValueError("Request id %s not found in history." %
                                 request_id)
            for link in self.history[feedback_request_id]:
                for feedback_type in feedback.keys():
                    if feedback_type == "default": continue
                    if link["title"] in feedback.getlist(feedback_type):
                        process_feedback(link, feedback_type)
                        break
                else:
                    if "default" in feedback:
                        process_feedback(link, feedback["default"])

    def evaluate(self, context_path, settings):
        settings = dict(settings.iteritems())
        if not "target" in settings: settings["target"] = "positive"
        if not "heuristic" in settings and not "model" in settings:
            settings["heuristic"] = "senseProbability"
        if "threshold" in settings:
            settings["threshold"] = float(settings["threshold"])
        else:
            settings["threshold"] = 0.5
            
        if "model" in settings:
            (model, description) = self.modelStore.load_model(settings["model"])
            print "Evaluating classifier %s in context %s with threshold %f" %\
                  (description["source"], context_path, settings["threshold"])
        else:
            print "Evaluating context %s with threshold %s >= %f" % \
                   (context_path, settings["heuristic"], settings["threshold"])

        evaluation = defaultdict(int)
        evaluation["contexts"] = {}
        evaluation["feedback"] = defaultdict(int)
        for context in self.context_history.keys():
            if context.startswith(context_path):
                evaluation["contexts"][context] = defaultdict(int)
                evaluation["contexts"][context]["feedback"] = defaultdict(int)
    
        all_labels, all_scores, all_predictions = [], [], []
        for context, context_evaluation in evaluation["contexts"].iteritems():
            labels, scores, testfeatures = [], [], []
            for request_id in self.context_history[context]:
                assert request_id in self.history
                evaluation["request"] += 1
                context_evaluation["requests"] += 1
                for link in self.history[request_id]:
                    evaluation["links"] += 1
                    context_evaluation["links"] += 1
                    if "feedback" in link:
                        evaluation["feedback"][link["feedback"]] += 1
                        context_evaluation["feedback"][link["feedback"]] += 1
                        labels.append(link["feedback"] == settings["target"])
                        if "model" in settings:
                            assert "features" in link
                            features = sorted(link["features"].keys())
                            features = self.check_model(model, description, \
                                                        features, settings)
                            testfeatures.append([link["features"][feature] \
                                                 for feature in features])
                        else:
                            scores.append(link[settings["heuristic"]])
                    else:
                        evaluation["feedback"]["missing"] += 1
                        context_evaluation["feedback"]["missing"] += 1

            if len(labels):
                if "model" in settings:
                    scores = [score[1] for score in \
                              self.predict(model, testfeatures)]
                context_evaluation["metrics"] = \
                    compute_metrics(labels, scores, settings["threshold"])
                all_labels.extend(labels)
                all_scores.extend(scores)

        if len(all_labels):
            evaluation["micro_metrics"] = \
                compute_metrics(all_labels, all_scores, settings["threshold"])
            evaluation["macro_metrics"] = defaultdict(float)            
            for context, context_evaluation in evaluation["contexts"].iteritems():
                if not "metrics" in context_evaluation: continue
                evaluation["macro_metrics"]["count"] += 1
                for metric, value in context_evaluation["metrics"].iteritems():
                    evaluation["macro_metrics"][metric] += value
            for metric, value in evaluation["macro_metrics"].iteritems():
                if metric == "count": continue
                evaluation["macro_metrics"][metric] /= \
                    evaluation["macro_metrics"]["count"]
    
        return evaluation
                        
    def learn(self, name, settings):
        # Create metadata
        metadata = dict(settings)
        metadata.update({"requests": 0, "links": 0, 
                         "feedback": defaultdict(int)})
        # Set defaults
        if "target" not in metadata: metadata["target"] = "positive"

        # Find request ids
        if "context" in settings:
            request_ids = []
            for context in self.context_history.keys():
                if context.startswith(settings["context"]):
                    request_ids.extend(self.context_history[context])
        else:
            request_ids = self.history.keys()
        
        print "Learning a classifier named %s" % name,
        if "context" in settings: print "in context", settings["context"],
        print "based on %d requests." % len(request_ids)
        
        if not "classifier" in settings:
            (model, metadata) = self.modelStore.load_model(name)
            assert hasattr(model, "partial_fit")
        else:
            # Create learner
            skip_settings = ["target", "context"]
            model = self.modelStore.create_model(settings, skip_settings)
            metadata["model"] = {model.__class__.__name__: model.get_params(deep=True)}

        # Create training data and labels
        data, targets = [], []
        for request_id in request_ids:
            assert request_id in self.history
            metadata["requests"] += 1
            for link in self.history[request_id]:
                assert "features" in link
                metadata["links"] += 1
        
                if not "features" in metadata:
                    metadata["features"] = sorted(link["features"].keys())
                assert metadata["features"] == sorted(link["features"].keys())
            
                # print request_id, len(link["features"]), 
                # print link["feedback"] if "feedback" in link else ""
                if "feedback" in link:
                    metadata["feedback"][link["feedback"]] += 1
                    targets.append(link["feedback"] == metadata["target"])
                else:
                    targets.append(None)
                data.append([])
                for feature in sorted(link["features"].keys()):
                    data[-1].append(link["features"][feature])

        if "classifier" in settings:
            assert len(data) == metadata["links"]
            assert len(targets) == metadata["links"]
        if len(data): assert len(data[0]) == len(metadata["features"])
        
        # Do learning
        print metadata
        
        if len(data):
            if not "classifier" in settings:
                model.partial_fit(data, targets, (True, False))
                print "Partially",
            else:
                model.fit(data, targets)
            print "Fitted %s model to %d training samples." % \
                  (model.__class__.__name__, len(data))
            
        self.modelStore.save_model(model, name, metadata)
