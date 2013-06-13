import redis
import codecs
from wpm.base import Data
from wpm.wpmutil import normalize
from wpm.wpmutil import check_dump_path
from wpm.wpmutil import dump_filenames


class WpmDataRedis(Data):
    def __init__(self, langcode, host='localhost', port=6379):
        """
        <langcode>:name = language name
        <langcode>:path = wpminer path
        <langcode>:txt:<text> = set(prob, prob, prob, prob [, senseid...])
        <langcode>:txt:<text>:<senseid> = set(prob, prob, bool, bool)
        <langcode>:norm:<text> = list([text, ...])
        <langcode>:trnsl = set([senseid, ...])
        <langcode>:trnsl:<senseid> = list([langcode, ...])
        <langcode>:trnsl:<senseid>:<langcode> = translated title
        <langcode>:titles:<pageid> = title
        <langcode>:ids:<pagetitle> = id
        <langcode>:<n>grms = zset([words{score}, [...]])
        """
        self.conn = redis.StrictRedis(host=host, port=port,
                                      db=0, decode_responses=True)
        self.separator = ':'
        self.ns_name = '%s%sname' % (langcode, self.separator)
        self.ns_path = '%s%spath' % (langcode, self.separator)
        self.ns_txt = '%s%stxt' % (langcode, self.separator)
        self.ns_norm = '%s%snorm' % (langcode, self.separator)
        self.ns_trnsl = '%s%strnsl' % (langcode, self.separator)
        self.ns_titles = '%s%stitles' % (langcode, self.separator)
        self.ns_ids = '%s%sids' % (langcode, self.separator)
        self.ns_ngrms = '%s%s' % (langcode, self.separator) + '%sgrms'

    def ns_txt_txt(self, txt):
        return self.ns_txt + self.separator + txt

    def ns_txt_txt_sid(self, txt, sid):
        return self.ns_txt + self.separator + txt + self.separator + sid

    def ns_norm_ntxt(self, ntxt):
        return self.ns_norm + self.separator + ntxt

    def ns_trnsl_sid(self, sid):
        return self.ns_trnsl + self.separator + sid

    def ns_trnsl_sid_lang(self, sid, langcode):
        return self.ns_trnsl + self.separator + sid + self.separator + langcode

    def ns_titles_pid(self, pid):
        return self.ns_titles + self.separator + pid

    def ns_ngrms_n(self, n):
        return self.ns_ngrms % n

    def ns_ids_title(self, title):
        return self.ns_ids + self.separator + title

    def entity_exists(self, entity):
        return self.conn.exists(self.ns_txt_txt(entity))

    def normalized_entity_exists(self, normalized_entity):
        return self.conn.exists(self.ns_norm_ntxt(normalized_entity))

    def get_all_entities(self, normalized_entity):
        return self.conn.smembers(self.ns_norm_ntxt(normalized_entity))

    def get_entity_data(self, entity):
        entity_data = self.conn.lrange(self.ns_txt_txt(entity), 0, -1)
        senses = []
        if len(entity_data) > 4:
            senses = entity_data[4:]
        return {'cntlinkocc': int(entity_data[0]),
                'cntlinkdoc': int(entity_data[1]),
                'cnttextocc': int(entity_data[2]),
                'cnttextdoc': int(entity_data[3]),
                'senses': senses}

    def get_sense_data(self, entity, sense):
        sense_data = self.conn.lrange(self.ns_txt_txt_sid(entity, sense),
                                      0, -1)
        return {'cntlinkocc': int(sense_data[0]),
                'cntlinkdoc': int(sense_data[1]),
                'from_title': sense_data[2],
                'from_redir': sense_data[3]}

    def get_sense_title(self, sid):
        return self.conn.get(self.ns_titles_pid(sid))

    def get_title_id(self, title):
        return self.conn.get(self.ns_ids_title(title))

    def sense_has_trnsl(self, sid):
        return self.conn.sismember(self.ns_trnsl, sid)

    def get_trnsl_langs(self, sid):
        return self.conn.lrange(self.ns_trnsl_sid(sid), 0, -1)

    def get_sense_trnsl(self, sid, lang):
        return self.conn.get(self.ns_trnsl_sid_lang(sid, lang))

    def get_wikipedia_name(self):
        path = self.conn.get(self.ns_path)
        if path[-1] == '/':
            return path.split('/')[-2]
        return path.split('/')[-1]

    def get_data_path(self):
        return self.conn.get(self.ns_path)

    def get_lang_name(self):
        return self.conn.get(self.ns_name)

    def get_title_ngram_score(self, title):
        nr_of_tokens = len(title.split())
        return self.conn.zscore(self.ns_ngrms_n(str(nr_of_tokens)),
                                title)


class WpmLoader:

    def __init__(self):
        self.translation_langs = ['en', 'nl', 'fr', 'es']
        self.wpm = None

    def load_wpminer_dump(self, langname, langcode, path):
        """
        <langcode>:name = language name
        <langcode>:path = wpminer path
        <langcode>:txt:<text> = set(prob, prob, prob, prob [, senseid...])
        <langcode>:txt:<text>:<senseid> = set(prob, prob, bool, bool)
        <langcode>:norm:<text> = list([text, ...])
        <langcode>:trnsl = set([senseid, ...])
        <langcode>:trnsl:<senseid> = list([langcode, ...])
        <langcode>:trnsl:<senseid>:<langcode> = translated title
        <langcode>:titles:<pageid> = title
        <langcode>:ids:<pagetitle> = id
        """
        path = check_dump_path(path)
        self.wpm = WpmDataRedis(langcode)
        rds = self.wpm.conn
        rds.set(langcode + ":name", langname)
        rds.set(langcode + ":path", path)
        self.load_labels(path + dump_filenames["labels"])
        self.load_translations(path + dump_filenames["translations"])
        self.load_page_titles(path + dump_filenames["pages"])

    def load_labels(self, filename):
        print 'Loading labels into redis...'
        rds = self.wpm.conn
        pipe = rds.pipeline()
        linenr = 0
        labels_file = codecs.open(filename, "r", "utf-8")
        for line in labels_file:
            linenr += 1
            try:
                stats_part, senses_part = line.split(',v{')
                senses = senses_part[:-1].split('s')[1:]
                stats = stats_part[1:].split(',')
                text = stats[0]
                txtkey = self.wpm.ns_txt_txt(text)
                pipe.rpush(txtkey, *[st for st in stats[1:]])
                for sense_text in senses:
                    sense_parts = sense_text[1:-1].split(',')
                    sense_parts[-1] = sense_parts[-1][0]
                    pipe.rpush(txtkey, sense_parts[0])
                    pipe.rpush(self.wpm.ns_txt_txt_sid(text, sense_parts[0]),
                               *sense_parts[1:])
                normalized = normalize(text)
                pipe.sadd(self.wpm.ns_norm_ntxt(normalized), text)
                pipe.execute()
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
        print 'Done loading labels'
        labels_file.close()

    def load_translations(self, filename):
        print 'Loading translations into redis...'
        rds = self.wpm.conn
        pipe = rds.pipeline()
        linenr = 0
        trnsl_file = codecs.open(filename, "r", "utf-8")
        for line in trnsl_file:
            linenr += 1
            try:
                tr_id_str, translation_part = line.strip()[:-1].split(",m{'")
                tr_id = tr_id_str
                parts = translation_part.split(",'")
                pipe.sadd(self.wpm.ns_trnsl, tr_id)
                #self.translation[tr_id] = {}
                for i in range(0, len(parts), 2):
                    lang = parts[i]
                    if lang in self.translation_langs:
                        pipe.rpush(self.wpm.ns_trnsl_sid(tr_id), lang)
                        pipe.set(self.wpm.ns_trnsl_sid_lang(tr_id, lang),
                                  parts[i + 1])
                pipe.execute()
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
        trnsl_file.close()
        print 'Done loading translations'

    def load_page_titles(self, filename):
        print 'Loading page titles...'
        rds = self.wpm.conn
        pipe = rds.pipeline()
        linenr = 0
        titles_file = codecs.open(filename, "r", "utf-8")
        for line in titles_file:
            linenr += 1
            try:
                splits = line.split(',')
                pageid = splits[0]
                title = splits[1][1:]
                pipe.set(self.wpm.ns_titles_pid(pageid), title)
                pipe.set(self.wpm.ns_ids_title(title), pageid)
                self.store_title_as_ngram(title, pipe)
                pipe.execute()
            except:
                print "Error loading on line " + str(linenr) + ": " + line
                continue
        titles_file.close()
        print 'Done loading pages (%d pages loaded)' % linenr

    def store_title_as_ngram(self, title, pipeline):
        words = title.split()
        for n in range(1, len(words) + 1):
            for i in range(0, len(words) - n):
                ngram = " ".join(words[i:i + n])
                pipeline.zincrby(self.wpm.ns_ngrms_n(str(n - i)), ngram, 1)
