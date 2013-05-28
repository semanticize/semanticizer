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
