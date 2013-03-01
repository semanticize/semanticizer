from sklearn.externals import joblib

pickle_cache = {}
def pickle_load(filename):
    if pickle_cache.has_key(filename):
        return pickle_cache[filename]
    object = joblib.load(filename)
    pickle_cache[filename] = object
    return object

def predict(classifier, testfeatures):
    clf = pickle_load("pickles/" + classifier)
    print("Loaded classifier pickle from %s" % classifier)
        
    print("Start predicting of %d instances with %d features." % (len(testfeatures), len(testfeatures[0])))
    predict = clf.predict_proba(testfeatures)
    print("Done predicting of %d instances." % len(predict))

    return predict
