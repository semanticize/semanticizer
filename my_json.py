import sys

try:
    import ujson as json
    print >> sys.stderr, "json is ujson"
except ImportError:
    try:
        import simplejson as json
        print >> sys.stderr, "json is simplejson"
    except ImportError:
        import json
        print >> sys.stderr, "json is json"
