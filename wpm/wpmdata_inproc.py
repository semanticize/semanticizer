from wpm.base import Data
from collections import defaultdict
from wpm.wpmutil import normalize
from wpm.wpmutil import check_dump_path
from wpm.wpmutil import dump_filenames
import codecs


class WpmDataInProc(Data):

    def __init__(self, langcode, language=None, path=None):
        """load data"""
        self.path = check_dump_path(path)
        self.langname = language
        self.langcode = langcode
        self.translation_langs = ['en', 'nl', 'fr', 'es']
        self.labels = {}
        self.normalized = defaultdict(list)
        self.load_labels(self.path + dump_filenames["labels"])
        self.translation = {}
        self.load_translations(self.path + dump_filenames["translations"])
        self.page_title = {}
        self.title_page = {}
        self.load_page_titles(self.path + dump_filenames["pages"])
        self.ngram_in_title = {}
        self.load_ngram_in_title()

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
        print 'Loading labels...'
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                stats_part, senses_part = line.split(',v{')
                senses = senses_part[:-1].split('s')[1:]
                stats = stats_part[1:].split(',')
                text = stats[0]
                label = [[int(x) for x in stats[1:]]]
                label.append({})
                for sense_text in senses:
                    sense_parts = sense_text[1:-1].split(',')
                    sense_parts[4] = sense_parts[4][0]
                    sid = int(sense_parts[0])
                    label[-1][sid] = [int(x) for x in sense_parts[1:3]] + \
                                     [sense_parts[3] == 'T',
                                     sense_parts[4] == 'T']

                self.labels[text] = label

                normalized = normalize(text)
                self.normalized[normalized].append(text)
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue

    def load_translations(self, filename):
        print 'Loading translations...'
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                id_str, translation_part = line.strip()[:-1].split(",m{'")
                sid = int(id_str)
                parts = translation_part.split(",'")
                self.translation[sid] = {}
                for i in range(0, len(parts), 2):
                    lang = parts[i]
                    if lang in self.translation_langs:
                        self.translation[sid][parts[i]] = parts[i + 1]
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue

    def load_page_titles(self, filename):
        print 'Loading page titles...'
        linenr = 0
        for line in codecs.open(filename, "r", "utf-8"):
            linenr += 1
            try:
                splits = line.split(',')
                sid = int(splits[0])
                title = splits[1][1:]
                self.page_title[sid] = title
                self.title_page[title] = sid
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue

        print '%d pages loaded.' % len(self.page_title)

    def load_ngram_in_title(self):
        print "Loading ngram in title..."
        for title in self.title_page:
            words = title.split()
            for n in range(1, len(words) + 1):
                for i in range(0, len(words) - n):
                    ngram = " ".join(words[i:i + n])
                    self.ngram_in_title.setdefault(ngram, 0)
                    self.ngram_in_title[ngram] += 1
        print "done"

    def entity_exists(self, entity):
        return entity in self.labels

    def normalized_entity_exists(self, normalized_entity):
        return normalized_entity in self.normalized

    def get_all_entities(self, normalized_entity):
        return self.normalized[normalized_entity]

    def get_entity_data(self, entity):
        return {'cntlinkocc': int(self.labels[entity][0][0]),
                'cntlinkdoc': int(self.labels[entity][0][1]),
                'cnttextocc': int(self.labels[entity][0][2]),
                'cnttextdoc': int(self.labels[entity][0][3]),
                'senses': self.labels[entity][1].keys()}

    def get_sense_data(self, entity, sense):
        return {'cntlinkocc': int(self.labels[entity][1][int(sense)][0]),
                'cntlinkdoc': int(self.labels[entity][1][int(sense)][1]),
                'from_title': self.labels[entity][1][int(sense)][2],
                'from_redir': self.labels[entity][1][int(sense)][3]}

    def get_sense_title(self, sid):
        return self.page_title[int(sid)]

    def get_title_id(self, title):
        try:
            return self.title_page[title]
        except KeyError:
            return None

    def sense_has_trnsl(self, sid):
        return int(sid) in self.translation

    def get_trnsl_langs(self, sid):
        return self.translation[int(sid)]

    def get_sense_trnsl(self, sid, lang):
        return self.translation[int(sid)][lang]

    def get_wikipedia_name(self):
        if self.path[-1] == '/':
            return self.path.split('/')[-2]
        return self.path.split('/')[-1]

    def get_data_path(self):
        return self.path

    def get_lang_name(self):
        return self.langname

    def get_title_ngram_score(self, title):
        try:
            return self.ngram_in_title[title]
        except KeyError:
            return None
