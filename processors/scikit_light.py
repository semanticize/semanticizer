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

from sklearn.externals import joblib

pickle_cache = {}


def pickle_load(filename):
    if filename in pickle_cache:
        return pickle_cache[filename]
    obj = joblib.load(filename)
    pickle_cache[filename] = obj
    return obj


def predict(classifier, testfeatures):
    clf = pickle_load("pickles/" + classifier)
    print("Loaded classifier pickle from %s" % classifier)

    print("Start predicting of %d instances with %d features."
          % (len(testfeatures), len(testfeatures[0])))
    predict = clf.predict_proba(testfeatures)
    print("Done predicting of %d instances." % len(predict))

    return predict
