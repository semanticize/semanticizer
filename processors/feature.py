import shelve
import cPickle as pickle
from datetime import datetime, timedelta

from math import log
import re
from json import loads
import collections
import stringUtils
import os

# Als je het EDIT_DISTANCE feature wil gebruiken moet je een Python Levenshtein
# module installeren. Ik had deze gepakt:
# http://pypi.python.org/pypi/python-Levenshtein/0.10.2
import Levenshtein

class anchorFeatures:
    def __init__(self, langcode, wikipediaminer_root, pickledir, title_page=None):
        pickle_root = pickledir + '/' + langcode + '/'
        
        if not os.path.exists(pickle_root):
            os.makedirs(pickle_root)
        
        #   From Wikipedia miner CSV file:
        self.wikipediaArticleCount = 970139
        self.wikipediaCategoryCount = 63108
        # NEEDS TO BE CHANGED FOR OTHER LANGUAGES THAN NL
        if langcode != "nl": 
            print "WARNING: Statistics for features are incorrect"
            
        if title_page != None:
            self.title_page = title_page
            try:
                self.ngram_in_title = pickle.load(open(pickle_root + 'ngram_in_title.pickle', 'rb'))
                print "Loaded ngram in title from pickle"
            except IOError:
                self.ngram_in_title = {}
                self.load_ngram_in_title()
                pickle.dump(self.ngram_in_title, open(pickle_root + 'ngram_in_title.pickle', 'wb'))
        else:
            try:
                self.title_page = pickle.load(open(pickle_root + 'title_page.pickle', 'rb'))
                self.ngram_in_title = pickle.load(open(pickle_root + 'ngram_in_title.pickle', 'rb'))
                print "Loaded page titles from pickle"
            except IOError:
                self.title_page = {}
                self.ngram_in_title = {}
                self.load_page_titles(wikipediaminer_root + "page.csv")
                pickle.dump(self.title_page, open(pickle_root + 'title_page.pickle', 'wb'))
                pickle.dump(self.ngram_in_title, open(pickle_root + 'ngram_in_title.pickle', 'wb'))

    def load_page_titles(self, filename):
        print "Loading page titles...", 
        file = open(filename, 'r')
        for line in file:
            line = line.replace('\'', '')
            splits = line.split(',')
            id = int(splits[0])
            title = splits[1]
    #       page_title[id] = title
            self.title_page[title] = id
            
            words = title.split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def load_ngram_in_title(self):
        print "Loading ngram in title...", 
        for title in self.title_page:
            words = title.split()
            for n in range(1, len(words)+1):
                for i in range(0, len(words)-n):
                    ngram = " ".join(words[i:i+n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def feature_LEN(self, link):
        return len(re.findall(stringUtils.reTokenPattern, link["label"]))
    
    def feature_IDF_title(self, link):
        if self.ngram_in_title.has_key(link["label"]):
            in_title_count = self.ngram_in_title[link["label"]]
        else:
            in_title_count = 0
        return log(float(self.wikipediaArticleCount)/ \
                   (float(in_title_count)+0.00001) )
    
    def feature_IDF_anchor(self, link):
        return log(float(self.wikipediaArticleCount)/ \
                   (float(link["linkDocCount"])+0.00001))
    
    def feature_IDF_content(self, link):
        return log(float(self.wikipediaArticleCount)/ \
                   (float(link["docCount"])+0.00001))
    
    def feature_KEYPHRASENESS(self, link):
        return float(link["linkDocCount"])/(float(link["docCount"])+0.00001)
    
    def feature_LINKPROB(self, link):
        return float(link["linkOccCount"])/(float(link["occCount"])+0.00001)
    
    def feature_SNIL(self, link):
        SNIL = 0
            
        words = link["label"].split()
        for n in range(1, len(words)+1):
            for i in range(0, len(words)-n):
                ngram = " ".join(words[i:i+n])
                if ngram in self.title_page:
                    SNIL += 1
        return SNIL
    
    def feature_SNCL(self, link):
        SNCL = 0
            
        words = link["label"].split()
        for n in range(1, len(words)+1):
            for i in range(0, len(words)-n):
                ngram = " ".join(words[i:i+n])
                if ngram in self.ngram_in_title:
                    SNCL += self.ngram_in_title[ngram]
        return SNCL

    def feature_NORMALIZATION(self, link):
        edit = Levenshtein.distance(link["label"], link["text"])
        return float(edit)/len(link["text"])

    def compute_anchor_features(self, link):
        return {'LEN': self.feature_LEN(link),
                'IDF_title': self.feature_IDF_title(link),
                'IDF_anchor': self.feature_IDF_anchor(link),
                'IDF_content': self.feature_IDF_content(link),
                'KEYPHRASENESS': self.feature_KEYPHRASENESS(link),
                'LINKPROB': self.feature_LINKPROB(link),
                'SNIL': self.feature_SNIL(link),
                'SNCL': self.feature_SNCL(link),
                'NORMALIZATION': self.feature_NORMALIZATION(link)
                }
       
class articleFeatures:
    def __init__(self):
        self.re_non_word_chars = re.compile('(?u)\W+', re.UNICODE)

    def feature_INLINKS(self, link):
        if "InLinks" not in link: 
            return 0
        return len(link["InLinks"])
    
    def feature_OUTLINKS(self, link):
        if "OutLinks" not in link: 
            return 0
        return len(link["OutLinks"])

    def feature_REDIRECT(self, link):
        # Should be fromRedirect but bug in Wikipedia Miner
        if "fromTitle" in link and link["fromTitle"]:
            return 1
        return 0

    def feature_TF(self, link, re_label_text, features):
        aMatches = re.findall(re_label_text, link['title'])
        features["TF_title"] = float(len(aMatches))

        text = " "
        if "Definition" in link:
            if link["Definition"] and len(link["Definition"]):
                text = re.sub(r"<.*?>", "", link["Definition"])
                text = re.sub(r"^[|\- }]*", "", text)

        while len(text) and (text[0] == "."):
            text = text[1:].strip()

        # Very rarely articles do not have a Definition text (or a dummy one 
        # like "----") 
        if len(text) == 0:
            features["TF_sentence"] = 0
            features["TF_paragraph"] = 0
            features["POS_first_in_paragraph"] = 1
        else:
            # Sentence is first sentence                                    
            sentence = text.split('.')[0]

            aMatches = re.findall(re_label_text, sentence)
            features["TF_sentence"] = float(len(aMatches))

            aMatches = re.findall(re_label_text, text)
            features["TF_paragraph"] = float(len(aMatches))

            if len(aMatches):
                features["POS_first_in_paragraph"] = \
                               float(re.search(re_label_text, text).start())
            else:
                features["POS_first_in_paragraph"] = 1

    def feature_TITLE(self, link, re_label_text, features):
        label_text = unicode(link["label"])

        re_title = stringUtils.ngramToPattern(link['title'])
        article_title = unicode(link['title'])
        
        features["NCT"] = 0 if re.search(re_title, label_text) is None \
            else 1

        features["TCN"] = 0 \
            if re.search(re_label_text, article_title) is None else 1

        features["TEN"] = 1 if article_title == label_text else 0

        # Irritatingly enough, split() can give you empty values as last
        # element
        split_label = self.re_non_word_chars.split(label_text)
        if split_label[-1] == '':
            split_label.pop()
        split_title = self.re_non_word_chars.split(article_title)
        if split_title[-1] == '':
            split_title.pop()

        # I: True if the title of the candidate begins with the the query 
        # (e.g. "Cambridge, Massachusetts" and "Cambridge" ) 
        features["SUBSTRING_MATCH_1"] = 1 \
            if split_title[0] == split_label[0] else 0

        # II: True if the title of the candidate ends with the the query 
        # (e.g: "Venice-Simplon Orient Express" and "Orient Express") 
        features["SUBSTRING_MATCH_2"] = 1 \
            if split_title[-1] == split_label[-1] else 0

        # collections.Counter() converts an array to a dict of words
        # and their frequencies
        cSplitLabel = collections.Counter(split_label)
        cSplitTitle = collections.Counter(split_title)

        # Number of shared words between the title of the candidate and
        # the  query 
        features['WORD_MATCH'] = len(list(cSplitLabel & cSplitTitle))

        # Number of different words between the title of the candidate
        # and the query 
        features['WORD_MISS'] = len(split_label) + len(split_title) \
            - (2 * features['WORD_MATCH'])

        # Levenshtein distance between query and title of the candidate 
        features["EDIT_DISTANCE"] = Levenshtein.distance(label_text,
                                                         article_title)
    
    def feature_COMMONNESS(self, link, features):
        features["COMMONNESS"] = link["priorProbability"]
        
    def compute_article_features(self, link):
        features = {
            'INLINKS': self.feature_INLINKS(link),
            'OUTLINKS': self.feature_OUTLINKS(link),
            'REDIRECT': self.feature_REDIRECT(link)
        }        

        re_label_text = stringUtils.ngramToPattern(link["label"])
        
        self.feature_TF(link, re_label_text, features)
        self.feature_TITLE(link, re_label_text, features)
        self.feature_COMMONNESS(link, features)

        return features

        ### TK: Ik heb nog wat extra features gemaakt die kijken hoe vaak
        ### inlink anchors en inlink/outlink titels voorkomen in de
        ### referentietekst en de zogenaamde aposition in de titel
        ### ('actress' in 'Sue Johnson (actress)')
        ###
        ### 'NR_OF_MATCHING_INLINK_ANCHORS', 'NR_OF_MATCHING_INLINK_TITLES',
        ### 'NR_OF_MATCHING_OUTLINK_TITLES', 'APOSITION'
        ###
        ### Dat is er nu niet zo makkelijk in te bouwen omdat we hier geen
        ### toegang hebben tot de referentietekst. Maar die features van David
        ### gaan dat ook zeker nodig hebben!
        ###
        ### Maar goed, ik heb ze nu nog even weg gelaten...

if __name__ == "__main__":
    # Some settings
    langcode = "en"
    wikipediaminer_root = '/zfs/ilps-plexer/wikipediaminer/enwiki-20111007/'
    pickledir = "/Users/evertlammerts/semanticizer/pickles/"

    # Test data
    link = {"label":  "Alabama",
            "linkDocCount": 10, # Al deze waardes slaan nergens op natuurlijk,
            "docCount": 20,     # maar ok...
            "linkOccCount": 100,
            "occCount": 200,
            "commonness": 0.12345
            }

    # Article
    article_url = '' # Wordt niet gebruikt nu
    fh_article_xml = open("unitTest.article.xml", "r")
    article_xml = fh_article_xml.read()
    fh_article_xml.close()
    article = ElementTree.fromstring(article_xml).find("Response")
    
    # Initialize the objects
    print "Initializing anchor features"
    anchor_features = anchorFeatures(langcode, wikipediaminer_root, pickledir)
    print "Initializing concept features"
    concept_features = conceptFeatures(langcode, wikipediaminer_root,
                                       article_url)
    print "Initializing anchor/concept features"
    anchor_concept_features = anchorConceptFeatures()
    print "Initializing statistics features"
    statistics_features = statisticsFeatures(langcode)

    print "Start calculating"
    test_features = {
        "anchor": anchor_features.compute_anchor_features(link),
        "concept": concept_features.compute_concept_features(article),
        "anchor_concept": \
        anchor_concept_features.compute_anchor_concept_features(link, article),
        "statistics": statistics_features.compute_statistics_features(article),
        }

    print "%s" % test_features
