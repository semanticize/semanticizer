import urllib, urllib2
from lxml import etree as ElementTree

class ILPSSemanticizer:
    def __init__(self, langcode, wikipediaminer_root):
        self.SEMANTICIZE_URL = "http://zookst13.science.uva.nl:8080/dutchsemcor/commonness"
        self.WIKIPEDIA_ID = wikipediaminer_root.split('/')[-2]
        self.WIKIPEDIA_URL_TEMPLATE = "http://%s.wikipedia.org/wiki/%s"
        self.langcode = langcode
        self.wikipediminer_root = wikipediaminer_root

    def semanticize(self, text):
        results = {"links": []}
    
        url = self.SEMANTICIZE_URL + "?"
        url += urllib.urlencode({"wikipedia": self.WIKIPEDIA_ID, 
                                 "verbose": "true", "normalise": "true",
                                 "input": text})
    
        try:
            request = urllib2.urlopen(url)
            encoding = request.headers['content-type'].split('charset=')[-1]
            #resultDoc = unicode(request.read(), encoding)
            resultDoc = request.read()
        except urllib2.HTTPError:
            return results        
    
        result = ElementTree.fromstring(resultDoc).find("Response")
        
        for sense in result.findall("Sense"):
            for ngram in sense.findall("Ngram"):
                link = {
                    "id": int(sense.attrib["id"]),
                    "title": sense.attrib["title"],
                    "url": self.WIKIPEDIA_URL_TEMPLATE % (langcode, urllib.quote(sense.attrib["title"].encode('utf-8'))),
                    "label": ngram.attrib["text"],
                    "occCount": int(ngram.attrib["occCount"]),
                    "docCount": int(ngram.attrib["docCount"]),
                    "linkOccCount": int(ngram.attrib["linkOccCount"]),
                    "linkDocCount": int(ngram.attrib["linkDocCount"]),
                    "commonness": float(ngram.attrib["score"]),
                    "prior_probability": float(ngram.attrib["linkOccCount"])/float(ngram.attrib["occCount"]),
                    "sense_probability": 
                        float(ngram.attrib["score"])*float(ngram.attrib["linkOccCount"])/float(ngram.attrib["occCount"]),
                }
                results["links"].append(link)
    #             
    #             "fromRedirect": false, 
    #             "url": "http://nl.wikipedia.org/wiki/Franse%20presidentsverkiezingen%20%282002%29", 
    #             "fromTitle": false, 
        return results    
