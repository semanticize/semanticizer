from collections import defaultdict
import sys
import os
import urllib
import codecs
from nltk import regexp_tokenize
from nltk.util import ngrams as nltk_ngrams

import unicodedata

#PICKLE_ROOT = './enwiki-20111007-pickles/'
#DEFAULT_LANGUAGE_CODE = 'en'
#WIKIPEDIAMINER_ROOT = '/zfs/ilps-plexer/wikipediaminer/enwiki-20111007/'
#SENSEPRO0THRESHOLD = 0.01
#TRANSLATION_LANGS = ['en', 'nl', 'fr', 'es']


def tokenize(text):
    """"""
    return regexp_tokenize(text, r'\w+([.,\']\w+)*|[^\w\s]+')


class Semanticizer:
    """"""

    def __init__(self, language_code, wikipediaminer_root,
                 sense_probability_threshold,
                 translation_langs=['en', 'nl', 'fr', 'es']):
        """"""
        self.translation = {}
        self.page_title = {}
        self.title_page = {}
        self.labels = {}
        self.normalized = defaultdict(list)
        self.category_parents = {}
        self.category_title = {}
        self.article_parents = {}
        self.language_code = language_code
        self.wikipediaminer_root = wikipediaminer_root
        self.sense_probability_threshold = sense_probability_threshold
        self.translation_langs = translation_langs
        self.wikipedia_url_template = 'http://%s.wikipedia.org/wiki/%s'

        #self.load_sentiment_lexicon('./sentiment_lexicon_nl.txt')

        self.load_translations(os.path.join(self.wikipediaminer_root,
                                            'translations.csv'))
        self.load_labels(os.path.join(self.wikipediaminer_root, 'label.csv'))
        self.load_page_titles(os.path.join(self.wikipediaminer_root,
                                           'page.csv'))

    def semanticize(self, sentence, normalize_dash=True,
                    normalize_accents=True, normalize_lower=False,
                    translations=True, counts=False,
                    sense_probability_threshold=None):
        """"""
        if sense_probability_threshold == None:
            sense_probability_threshold = self.sense_probability_threshold
        #result = {"sentiment_clues": {}, "links": []}
        result = {"links": []}
        ngrams = set()
        #tokens = [wordpunct_tokenize(sentence)]
        tokens = [tokenize(sentence),
                  tokenize(sentence.replace('-', ' ')),
                  tokenize(sentence.replace('.', ' ')),
                  tokenize(sentence.replace('.', ''))]

        # get all ngrams for this sentence
        for words in tokens:
            for n in range(1, len(words) + 1):
                for ngram in nltk_ngrams(words, n):
                    ngrams.add(' '.join(ngram))

        for ngram in ngrams:
            normal_ngram = self.normalize(ngram)
            if normal_ngram in self.normalized:
                normalized_ngram = self.normalize(ngram, normalize_dash,
                                                  normalize_accents,
                                                  normalize_lower)
                for anchor in self.normalized[normal_ngram]:
                    normalized_anchor = self.normalize(anchor, normalize_dash,
                                                       normalize_accents,
                                                       normalize_lower)
                    print normalized_ngram, normalized_anchor
                    if normalized_ngram == normalized_anchor:
                        assert anchor in self.labels
                        label = self.labels[anchor]
                        if len(label) < 5:
                            continue
                        for sense in label[4]:
                            if label[2] == 0:
                                link_probability = 0
                                sense_probability = 0
                            else:
                                link_probability = float(label[1]) / label[3]
                                # sense_probability is # of links to target
                                # with anchor text over # of times anchor text
                                # used
                                sense_probability = float(label[4][sense][1]) \
                                                    / label[3]
                            if sense_probability > sense_probability_threshold:
                                title = unicode(self.page_title[sense])
                                url = self.wikipedia_url_template \
                                      % (self.language_code,
                                         urllib.quote(title.encode('utf-8')))
                                if label[0] == 0:
                                    prior_probability = 0
                                else:
                                    prior_probability = float(
                                                          label[4][sense][0]
                                                        ) \
                                                        / label[0]
                                link = {
                                    "label": anchor,
                                    "text": ngram,
                                    "title": title,
                                    "id": sense,
                                    "url": url,
                                    "linkProbability": link_probability,
                                    "senseProbability": sense_probability,
                                    "priorProbability": prior_probability
                                }
                                if translations:
                                    link["translations"] = {self.language_code:
                                                            {"title": title,
                                                             "url": url}}
                                    if sense in self.translation:
                                        for lang in self.translation[sense]:
                                            link["translations"][lang] = {
                                                'title': unicode(self.translation[sense][lang]),
                                                'url': self.wikipedia_url_template % (lang, urllib.quote(unicode(self.translation[sense][lang]).encode('utf-8')))
                                            }
                                if counts:
                                    link["occCount"] = label[2]
                                    link["docCount"] = label[3]
                                    link["linkOccCount"] = label[0]
                                    link["linkDocCount"] = label[1]
                                    link["senseOccCount"] = label[4][sense][0]
                                    link["senseDocCount"] = label[4][sense][1]
                                    link['fromTitle'] = label[4][sense][2]
                                    link['fromRedirect'] = label[4][sense][3]
                                result["links"].append(link)

        return result

    def load_translations(self, filename):
        """"""
        print 'Loading translations...'
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                tr_id_str, translation_part = line.strip()[:-1].split(",m{'")
                tr_id = int(tr_id_str)
                parts = translation_part.split(",'")
                self.translation[tr_id] = {}
                for i in range(0, len(parts), 2):
                    lang = parts[i]
                    if lang in self.translation_langs:
                        self.translation[tr_id][parts[i]] = parts[i + 1]
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue

    def normalize(self, raw, dash=True, accents=True, lower=True):
        """"""
        text = raw
        if dash:
            text = text.replace('-', ' ')
        if accents:
            text = self.remove_accents(text)
        if lower:
            text = text.lower()
        text = text.strip()
        return text if len(text) else raw

    def remove_accents(self, input_str):
        """"""
        if type(input_str) is str:
            input_unicode = unicode(input_str, errors="ignore")
        else:
            input_unicode = input_str
        nkfd_form = unicodedata.normalize('NFKD', input_unicode)
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def load_page_titles(self, filename):
        """"""
        print 'Loading page titles...'
        linenr = 0
        titles_file = codecs.open(filename, "r", "utf-8")
        for line in titles_file:
            linenr += 1
            try:
                splits = line.split(',')
                pageid = int(splits[0])
                title = splits[1][1:]
                self.page_title[pageid] = title
                self.title_page[title] = pageid
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
        titles_file.close()
        print '%d pages loaded.' % len(self.page_title)

    # See Wikipedia Miner documentation at:
    # http://wikipedia-miner.cms.waikato.ac.nz/wiki/
    # (The CSV summary files)
    # http://wikipedia-miner.cms.waikato.ac.nz/doc/
    #
    # DbLabel(long LinkOccCount, long LinkDocCount,
    #         long TextOccCount, long TextDocCount,
    #         java.util.ArrayList<DbSenseForLabel> Senses)
    #
    # DbSenseForLabel(int Id, long LinkOccCount, long LinkDocCount,
    #                 boolean FromTitle, boolean FromRedirect)
    def load_labels(self, filename):
        """"""
        print 'Loading labels...'
        linenr = 0
        labels_file = codecs.open(filename, "r", "utf-8")
        for line in labels_file:
            linenr += 1
            try:
                stats_part, senses_part = line.split(',v{')
                senses = senses_part[:-1].split('s')[1:]
                stats = stats_part[1:].split(',')
                text = stats[0]
                label = [int(x) for x in stats[1:]]
                label.append({})
                for sense_text in senses:
                    sense_parts = sense_text[1:-1].split(',')
                    label[-1][int(sense_parts[0])] = \
                        [int(x) for x in sense_parts[1:3]] \
                        + [sense_parts[3] == 'T', sense_parts[4] == 'T']

                self.labels[text] = label

                normalized = self.normalize(text)
                self.normalized[normalized].append(text)
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
        labels_file.close()

    def load_category_parents(self, filename):
        """"""
        print 'Loading category parents...'
        linenr = 0
        cat_file = codecs.open(filename, "r", "utf-8")
        for line in cat_file:
            linenr += 1
            try:
                line = line.replace('v{', '').replace('}\n', '')
                ids = line.split(',')
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
            category_id = int(ids[0])
            self.category_parents[category_id] = []
            for parent_id in ids[1:]:
                self.category_parents[category_id].append(int(parent_id))
        cat_file.close()
        print '%d category parents loaded.' % len(self.category_parents)

    def load_category_titles(self, filename):
        """"""
        print 'Loading category titles...'
        cat_file = codecs.open(filename, "r", "utf-8")
        for line in cat_file:
            if not line.startswith('INSERT INTO `category` VALUES'):
                continue
            splits = line[31:-3].split('),(')
            for split in splits:
                data = split.split(',')
                self.category_title[int(data[0])] = ','.join(data[1:-4])[1:-1]
        cat_file.close()
        print '%d category titles loaded.' % len(self.category_title)

    def load_article_parents(self, filename):
        """"""
        print 'Loading article parents...'
        parents_file = codecs.open(filename, "r", "utf-8")
        for line in parents_file:
            line = line.replace('v{', '').replace('}\n', '')
            ids = line.split(',')
            article_id = int(ids[0])
            if article_id == 44731:
                print line
            self.article_parents[article_id] = []
            for parent_id in ids[1:]:
                self.article_parents[article_id].append(int(parent_id))
        parents_file.close()
        print '%d article parents loaded.' % len(self.article_parents)

if __name__ == '__main__':
    from nltk import sent_tokenize

    semanticizer = Semanticizer()
    print 'Loading text...'
    text_stdin = sys.stdin.read()
    sentences = sent_tokenize(text_stdin)
    for sntnc in sentences:
        print sntnc
        print semanticizer.semanticize(sntnc)
