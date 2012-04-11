import sys, os, urllib, codecs
from nltk import sent_tokenize, word_tokenize

#PICKLE_ROOT = './enwiki-20111007-pickles/'
DEFAULT_LANGUAGE_CODE = 'en'
WIKIPEDIAMINER_ROOT = '/zfs/ilps-plexer/wikipediaminer/enwiki-20111007/'
SENSEPRO0THRESHOLD = 0.01
WIKIPEDIA_URL_TEMPLATE = 'http://%s.wikipedia.org/wiki/%s'
TRANSLATION_LANGS = ['en', 'nl', 'fr', 'es']

class Semanticizer:
    def __init__(self, language_code=None, wikipediaminer_root=None, senseprobthreshold=None, translation_langs=None):
        if not language_code:
            self.language_code = DEFAULT_LANGUAGE_CODE
        else:
            self.language_code = language_code
        if not wikipediaminer_root:
            self.wikipediaminer_root = WIKIPEDIAMINER_ROOT
        else:
            self.wikipediaminer_root = wikipediaminer_root
        if not senseprobthreshold:
            self.senseprobthreshold = SENSEPRO0THRESHOLD
        else:
            self.senseprobthreshold = senseprobthreshold
        if not translation_langs:
            self.translation_langs = TRANSLATION_LANGS
        else:
            self.translation_langs = translation_langs

        #self.load_sentiment_lexicon('./sentiment_lexicon_nl.txt')
        
        self.load_translations(os.path.join(self.wikipediaminer_root, 'translations.csv'))
        self.load_labels(os.path.join(self.wikipediaminer_root, 'label.csv'))
        self.load_page_titles(os.path.join(self.wikipediaminer_root, 'page.csv'))

    def semanticize(self, sentence):
    #    result = {"sentiment_clues": {}, "links": []}
        result = {"links": []}
        words = word_tokenize(sentence.replace('-', ' '))
        for n in range(1,len(words)+1):
            for i in range(len(words)-n+1):
                word = ' '.join(words[i:i+n])
    #           if semanticizer.sentiment_lexicon.has_key(word):
    #               sentiment = semanticizer.sentiment_lexicon[word]
    #               result["sentiment_clues"][word] = sentiment
                if word in self.labels:
                    label = self.labels[word]
                    if len(label) < 5:
                        continue
                    for sense in label[4]:
                        if label[2] == 0:
                            continue
                        prior_probability = float(label[0])/label[2]
                        # Senseprob is # of links to target with anchor text
                        # over # of times anchor text used
                        senseprob = float(label[4][sense][0])/label[2]
                        if senseprob > self.senseprobthreshold:
                            title = unicode(self.page_title[sense])
                            commonness = float(label[4][sense][0])/label[0]
                            if sense in self.translation:
                                translations = {}
                                for lang in self.translation[sense]:
                                    translations[lang] = {
                                        'title': unicode(self.translation[sense][lang]),
                                        'url' : WIKIPEDIA_URL_TEMPLATE % (lang, urllib.quote(unicode(self.translation[sense][lang]).encode('utf-8')))
                                    }
                            else:
                                translations = []
                            result["links"].append({
                                "label": word,
                                "title": title,
                                "id": sense,
                                "translations": translations,
                                "url": WIKIPEDIA_URL_TEMPLATE % (self.language_code, urllib.quote(title.encode('utf-8'))),
                                "prior_probability": prior_probability,
                                "sense_probability": senseprob,
                                "commonness": commonness
                            })
        return result

    def load_translations(self, filename):
        print 'Loading translations...'
        self.translation = {}
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                id_str, translation_part = line.strip()[:-1].split(",m{'")
                id = int(id_str)
                parts = translation_part.split(",'")
                self.translation[id] = {}
                for i in range(0, len(parts), 2):
                    lang = parts[i]
                    if lang in self.translation_langs:
                        self.translation[id][parts[i]] = parts[i+1]
            except:
                print "Error loading on line " + str(linenr )+ ": " + line
                continue

    def load_page_titles(self, filename):
        print 'Loading page titles...'
        self.page_title = {}
        self.title_page = {}
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                splits = line.split(',')
                id = int(splits[0])
                title = splits[1][1:]
                self.page_title[id] = title
                self.title_page[title] = id
            except:
                print "Error loading on line " + str(linenr )+ ": " + line
                continue

        print '%d pages loaded.' % len(self.page_title)

    def load_labels(self, filename):
        self.labels = {}
        print 'Loading labels...'
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                stats_part, senses_part = line.split(',v{')
                senses = senses_part[:-1].split('s')[1:]
                stats = stats_part[1:].split(',')
                text = stats[0]
                label = map(int, stats[1:])
                label.append({})
                for sense_text in senses:
                    sense_parts = sense_text[1:-1].split(',')
                    id = int(sense_parts[0])
                    label[-1][id] = map(int, sense_parts[1:3]) + [sense_parts[3] == 'T', sense_parts[4] == 'T']

                self.labels[text] = label
            except:
                print "Error loading on line " + str(linenr )+ ": " + line
                continue

    def load_category_parents(self, filename):
        print 'Loading category parents...'
        self.category_parents = {}
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                line = line.replace('v{', '').replace('}\n', '')
                ids = line.split(',')
            except:
                print "Error loading on line " + str(linenr )+ ": " + line
                continue
            category_id = int(ids[0])
            self.category_parents[category_id] = []
            for parent_id in ids[1:]:
                self.category_parents[category_id].append(int(parent_id))

        print '%d category parents loaded.' % len(self.category_parents)

    def load_category_titles(self, filename):
        print 'Loading category titles...'
        self.category_title = {}
        for line in codecs.open(filename, "r", "utf-8"):
            if not line.startswith('INSERT INTO `category` VALUES'):
                continue
            splits = line[31:-3].split('),(')
            for split in splits:
                data = split.split(',')
                self.category_title[int(data[0])] = ','.join(data[1:-4])[1:-1]

        print '%d category titles loaded.' % len(self.category_title)

    def load_article_parents(self, filename):
        print 'Loading article parents...'
        self.article_parents = {}
        for line in codecs.open(filename, "r", "utf-8"):
            line = line.replace('v{', '').replace('}\n', '')
            ids = line.split(',')
            article_id = int(ids[0])
            if article_id == 44731:
                print line
            self.article_parents[article_id] = []
            for parent_id in ids[1:]:
                self.article_parents[article_id].append(int(parent_id))

        print '%d article parents loaded.' % len(self.article_parents)

#    def senses(self, text):
#        raw_label = self.labels[text]
#        label = {'LinkOccCount': raw_label[0],
#         'LinkDocCount': raw_label[1],
#         'TextOccCount': raw_label[2],
#         'TextDocCount': raw_label[3],
#         'Senses': {}}
#        for id, raw_sense in raw_label[4].iteritems():
#            sense = {'LinkOccCount': raw_sense[0],
#             'LinkDocCount': raw_sense[1],
#             'FromTitle': raw_sense[2],
#             'FromRedirect': raw_sense[3]}
#            label['Senses'][self.page_title[id]] = sense
#
#        return label

#    def load_sentiment_lexicon(self, filename):
#        print 'Loading sentiment lexicon...'
#        self.sentiment_lexicon = {}
#        file = open(filename, 'r')
#        for line in file:
#            words = line.strip().split('\t')
#            self.sentiment_lexicon[words[0]] = words[1]
#
#        print '%d sentiment words loaded.' % len(self.sentiment_lexicon)
        
if __name__ == '__main__':
    semanticizer = Semanticizer()
    print 'Loading text...'
    text = sys.stdin.read()
    sentences = sent_tokenize(text)
    for sentence in sentences:
        print sentence
        print semanticizer.semanticize(sentence)
