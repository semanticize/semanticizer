import os, sys
import lxml
import codecs
import xml2json
from lxml import objectify
import json

filename = sys.argv[1]

raw = codecs.open(filename, 'r').read()
rawasci = unicode(raw, 'utf-8', 'ignore').encode('ascii', 'ignore')
obj = objectify.fromstring(rawasci)

jsonob = xml2json.objectJSONEncoder()
for d in obj['vespaadd']['document']:
    #print d.newsdocid#, len(json.loads(unicode(jsonob.encode(d), 'utf-8', 'ignore').encode('ascii', 'ignore')))
    jsonrep = json.loads(jsonob.encode(d))
    #print sorted(jsonrep.keys())
    print jsonrep['body']
