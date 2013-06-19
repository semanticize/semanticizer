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

import cPickle as pickle

from math import log
import wpm.wpmutil as wpmutil
import re
import collections
import processors.stringUtils as stringUtils
import os

import Levenshtein


class anchorFeatures:
    def __init__(self, langcode):
        '''pickle_root = pickledir + '/' + langcode + '/'

        if not os.path.exists(pickle_root):
            os.makedirs(pickle_root)'''
        self.wpm = wpmutil.wpm_dumps[langcode]
        #   From Wikipedia miner CSV file:
        self.wikipediaArticleCount = 970139
        self.wikipediaCategoryCount = 63108
        # NEEDS TO BE CHANGED FOR OTHER LANGUAGES THAN NL
        if langcode != "nl":
            print "WARNING: Statistics for features are incorrect"

        '''        if title_page != None:
            self.title_page = title_page
            try:
                self.ngram_in_title = pickle.load(open(pickle_root +
                                                       'ngram_in_title.pickle',
                                                       'rb'))
                print "Loaded ngram in title from pickle"
            except IOError:
                self.ngram_in_title = {}
                self.load_ngram_in_title()
                pickle.dump(self.ngram_in_title, open(pickle_root +
                                                      'ngram_in_title.pickle',
                                                      'wb'))
        else:
            try:
                self.title_page = pickle.load(open(pickle_root +
                                                   'title_page.pickle',
                                                   'rb'))
                self.ngram_in_title = pickle.load(open(pickle_root +
                                                       'ngram_in_title.pickle',
                                                       'rb'))
                print "Loaded page titles from pickle"
            except IOError:
                self.title_page = {}
                self.ngram_in_title = {}
                pickle.dump(self.title_page, open(pickle_root +
                                                  'title_page.pickle',
                                                  'wb'))
                pickle.dump(self.ngram_in_title, open(pickle_root +
                                                      'ngram_in_title.pickle',
                                                      'wb'))'''

    '''    def load_page_titles(self, filename):
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
            for n in range(1, len(words) + 1):
                for i in range(0, len(words) - n):
                    ngram = " ".join(words[i:i + n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def load_ngram_in_title(self):
        print "Loading ngram in title..."
        for title in self.title_page:
            words = title.split()
            for n in range(1, len(words) + 1):
                for i in range(0, len(words) - n):
                    ngram = " ".join(words[i:i + n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"'''

    def feature_LEN(self, lnk):
        return len(re.findall(stringUtils.reTokenPattern, lnk["label"]))

    def feature_IDF_title(self, lnk):
        score = self.wpm.get_title_ngram_score(lnk["label"])
        if not score == None:
            in_title_count = int(score)
        else:
            in_title_count = 0
        return log(float(self.wikipediaArticleCount) / \
                   (float(in_title_count) + 0.00001))

    def feature_IDF_anchor(self, lnk):
        return log(float(self.wikipediaArticleCount) / \
                   (float(lnk["linkDocCount"]) + 0.00001))

    def feature_IDF_content(self, lnk):
        return log(float(self.wikipediaArticleCount) / \
                   (float(lnk["docCount"]) + 0.00001))

    def feature_KEYPHRASENESS(self, lnk):
        return float(lnk["linkDocCount"]) / (float(lnk["docCount"]) + 0.00001)

    def feature_LINKPROB(self, lnk):
        return float(lnk["linkOccCount"]) / (float(lnk["occCount"]) + 0.00001)

    def feature_SNIL(self, lnk):
        SNIL = 0

        words = lnk["label"].split()
        for n in range(1, len(words) + 1):
            for i in range(0, len(words) - n):
                ngram = " ".join(words[i:i + n])
                if not self.wpm.get_title_id(ngram) == None:
                    SNIL += 1
        return SNIL

    def feature_SNCL(self, lnk):
        SNCL = 0

        words = lnk["label"].split()
        for n in range(1, len(words) + 1):
            for i in range(0, len(words) - n):
                ngram = " ".join(words[i:i + n])
                score = self.wpm.get_title_ngram_score(ngram)
                if not score == None:
                    SNCL += int(score)
        return SNCL

    def feature_NORMALIZATION(self, lnk):
        edit = Levenshtein.distance(lnk["label"], lnk["text"])
        return float(edit) / len(lnk["text"])

    def compute_anchor_features(self, lnk):
        return {'LEN': self.feature_LEN(lnk),
                'IDF_title': self.feature_IDF_title(lnk),
                'IDF_anchor': self.feature_IDF_anchor(lnk),
                'IDF_content': self.feature_IDF_content(lnk),
                'KEYPHRASENESS': self.feature_KEYPHRASENESS(lnk),
                'LINKPROB': self.feature_LINKPROB(lnk),
                'SNIL': self.feature_SNIL(lnk),
                'SNCL': self.feature_SNCL(lnk),
                'NORMALIZATION': self.feature_NORMALIZATION(lnk)
                }


class articleFeatures:
    def __init__(self):
        self.re_non_word_chars = re.compile(r'(?u)\W+', re.UNICODE)

    def feature_INLINKS(self, lnk):
        if "InLinks" not in lnk:
            return 0
        return len(lnk["InLinks"])

    def feature_OUTLINKS(self, lnk):
        if "OutLinks" not in lnk:
            return 0
        return len(lnk["OutLinks"])

    def feature_REDIRECT(self, lnk):
        # Should be fromRedirect but bug in Wikipedia Miner
        if "fromTitle" in lnk and lnk["fromTitle"]:
            return 1
        return 0

    def feature_TF(self, lnk, re_label_text, features):
        aMatches = re.findall(re_label_text, lnk['title'])
        features["TF_title"] = float(len(aMatches))

        text = " "
        if "Definition" in lnk:
            if lnk["Definition"] and len(lnk["Definition"]):
                text = re.sub(r"<.*?>", "", lnk["Definition"])
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

    def feature_TITLE(self, lnk, re_label_text, features):
        label_text = unicode(lnk["label"])

        re_title = stringUtils.ngramToPattern(lnk['title'])
        article_title = unicode(lnk['title'])

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

    def feature_COMMONNESS(self, lnk, features):
        features["COMMONNESS"] = lnk["priorProbability"]

    def compute_article_features(self, lnk):
        features = {
            'INLINKS': self.feature_INLINKS(lnk),
            'OUTLINKS': self.feature_OUTLINKS(lnk),
            'REDIRECT': self.feature_REDIRECT(lnk)
        }

        re_label_text = stringUtils.ngramToPattern(lnk["label"])

        self.feature_TF(lnk, re_label_text, features)
        self.feature_TITLE(lnk, re_label_text, features)
        self.feature_COMMONNESS(lnk, features)

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
            "linkDocCount": 10,  # Al deze waardes slaan nergens op natuurlijk,
            "docCount": 20,     # maar ok...
            "linkOccCount": 100,
            "occCount": 200,
            "commonness": 0.12345
            }

    # Article
    article_url = ''  # Wordt niet gebruikt nu
    fh_article_xml = open("unitTest.article.xml", "r")
    article_xml = fh_article_xml.read()
    fh_article_xml.close()
    article = ElementTree.fromstring(article_xml).find("Response")

    # Initialize the objects
    print "Initializing anchor features"
    anchor_features = anchorFeatures(langcode)
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
