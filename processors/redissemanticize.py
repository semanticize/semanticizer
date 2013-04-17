from util.wpmutil import WpmUtil
from nltk import regexp_tokenize
from nltk.util import ngrams as nltk_ngrams
import sys
import urllib
import codecs
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
                 sense_probability_threshold):
        """"""
        self.category_parents = {}
        self.category_title = {}
        self.article_parents = {}
        self.language_code = language_code
        self.wikipediaminer_root = wikipediaminer_root
        self.sense_probability_threshold = sense_probability_threshold
        self.wikipedia_url_template = 'http://%s.wikipedia.org/wiki/%s'
        self.wpm = WpmUtil(language_code)

        #self.load_sentiment_lexicon('./sentiment_lexicon_nl.txt')

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
            if self.wpm.normalized_entity_exists(normal_ngram):
                normalized_ngram = self.normalize(ngram, normalize_dash,
                                                  normalize_accents,
                                                  normalize_lower)
                anchors = self.wpm.get_all_entities(normal_ngram)
                for anchor in anchors:
                    normalized_anchor = self.normalize(anchor, normalize_dash,
                                                       normalize_accents,
                                                       normalize_lower)
                    print normalized_ngram, normalized_anchor
                    if normalized_ngram == normalized_anchor:
                        if not self.wpm.entity_exists(anchor):
                            raise LookupError("Data corrupted, cannot "
                                              + "find %s in the database" \
                                              % anchor)
                        entity = self.wpm.get_entity_data(anchor)
                        for sense in entity['senses']:
                            sense_str = str(sense)
                            sense_data = self.wpm.get_sense_data(anchor,
                                                                 sense_str)
                            if entity['cnttextocc'] == 0:
                                link_probability = 0
                                sense_probability = 0
                            else:
                                link_probability = float(entity['cntlinkdoc']) / entity['cnttextdoc']
                                sense_probability = float(sense_data['cntlinkdoc']) / entity['cnttextdoc']
                            if sense_probability > sense_probability_threshold:
                                title = unicode(self.wpm.get_sense_title(sense_str))
                                url = self.wikipedia_url_template \
                                      % (self.language_code,
                                         urllib.quote(title.encode('utf-8')))
                                if entity['cntlinkocc'] == 0:
                                    prior_probability = 0
                                else:
                                    prior_probability = float(sense_data['cntlinkocc']) / entity['cntlinkocc']
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
                                    if self.wpm.sense_has_trnsl(sense_str):
                                        for lang in self.wpm.get_trnsl_langs(sense_str):
                                            trnsl = self.wpm.get_sense_trnsl(sense_str, lang)
                                            link["translations"][lang] = {
                                                'title': unicode(trnsl),
                                                'url': self.wikipedia_url_template % (lang, urllib.quote(unicode(trnsl).encode('utf-8')))
                                            }
                                if counts:
                                    link["occCount"] = entity['cnttextocc']
                                    link["docCount"] = entity['cnttextdoc']
                                    link["linkOccCount"] = entity['cntlinkocc']
                                    link["linkDocCount"] = entity['cntlinkdoc']
                                    link["senseOccCount"] = int(sense_data['cntlinkocc'])
                                    link["senseDocCount"] = int(sense_data['cntlinkdoc'])
                                    link['fromTitle'] = sense_data['from_title']
                                    link['fromRedirect'] = sense_data['from_redir']
                                result["links"].append(link)

        return result

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
