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
import json

from .load import WpmLoader
from .namespace import WpmNS

wpm_dumps = {}

def init_datasource(wpm_languages, settings):
    """Set the datasource and init it"""
    for langcode, langconfig in wpm_languages.iteritems():
        load_wpm_data(langconfig['source'], langcode, settings, **langconfig['initparams'])

def load_wpm_data(datasource, langcode, settings, **kwargs):
    if datasource == "redis":
        from .db.redisdb import RedisDB
        db = RedisDB(**kwargs)
    elif datasource == "memory":
        from .db.inmemory import MemoryDB
        db = MemoryDB()
    elif datasource == "mongo":
        from .db.mongodb import MongoDB
        db = MongoDB()
        #load wpm data into memory
        WpmLoader(db, langcode, settings, **kwargs)
    else:
        raise ValueError("Unknown backend {}".format(datasource))
    wpm_dumps[langcode] = WpmData(db, langcode)
    
    
class WpmData:

    def __init__(self, db, langcode):
        
        #set database [memory or redis]
        self.db = db
        
        #get current db version
        self.version = self.db.get(langcode+":version")
        
        #load correct NameSpace
        self.ns = WpmNS(db, langcode, self.version) 
        
    def entity_exists(self, entity):
        return self.exists(self.ns.label(entity))

    def normalized_entities_exist(self, entities):
        with self.db.pipeline() as pipe:
            for e in entities:
                pipe.exists(self.ns.normalized(e))
            return pipe.execute()

    def get_all_entities(self, normalized_entity):
        return self.db.smembers(self.ns.normalized(normalized_entity))

    def get_entity_data(self, entity):
        entity_data = self.db.lrange(self.ns.label(entity) , 0, -1)
        senses = []
        if len(entity_data) > 4:
            senses = entity_data[4:]
        return {'cntlinkocc': int(entity_data[0]),
                'cntlinkdoc': int(entity_data[1]),
                'cnttextocc': int(entity_data[2]),
                'cnttextdoc': int(entity_data[3]),
                'senses': senses}
                
    def get_sense_data(self, entity, sense):
        sense_data = self.db.lrange(self.ns.label_sense(entity, sense), 0, -1)
        return {'cntlinkocc': int(sense_data[0]),
                'cntlinkdoc': int(sense_data[1]),
                'from_title': sense_data[2],
                'from_redir': sense_data[3]}

    def get_item_id(self, title):
        return self.db.get(self.ns.page_id(title))
    
    def get_item_ids(self, *titles):
        with self.db.pipeline() as pipe:
            for title in titles:
                pipe.get(self.ns.page_id(title))
            return pipe.execute()
    
    def get_item_title(self, pid):
        return self.db.get(self.ns.page_title(pid))
    
    def get_item_inlinks(self, pid):
        return self.db.lrange(self.ns.page_inlinks(pid), 0, -1)
    
    def get_item_outlinks(self, pid):
        return self.db.lrange(self.ns.page_outlinks(pid), 0, -1)
    
    def get_item_categories(self, pid):
        return self.db.get(self.ns.page_categories(pid))
    
    def get_item_definition(self, pid):
        return self.db.get(self.ns.page_definition(pid))
    
    def get_item_labels(self, pid):
        json_labels = self.db.lrange(self.ns.page_labels(pid), 0, -1)
        results = []
        for json_label in json_labels:
            label = json.loads(json_label)
            results.append({
                'title': label[0],
                'occurances': label[1],
                'fromRedirect': label[2],
                'fromTitle': label[3],
                'isPrimary': label[4],
                'proportion': label[5] 
            })
        return results
                
    def sense_has_trnsl(self, sid):
        return self.db.exists(self.ns.translation_sense(sid))

    def get_trnsl_langs(self, sid):
        return self.db.lrange(self.ns.translation_sense(sid), 0, -1)

    def get_sense_trnsl(self, sid, lang):
        return self.db.get(self.ns.translation_sense_language(sid, lang))

    def get_wikipedia_name(self):
        path = self.db.get(self.ns.wiki_path())
        if path[-1] == '/':
            return path.split('/')[-2]
        return path.split('/')[-1]

    def get_data_path(self):
        return self.db.get(self.ns.wiki_path())

    def get_lang_name(self):
        return self.db.get(self.ns.wiki_language_name())

    def get_title_ngram_score(self, title):
        nr_of_tokens = len(title.split())
        return self.db.zscore(self.ns.ngramscore(str(nr_of_tokens)), title)
    
    def get_stat(self, value):
        return self.db.get(self.ns.wiki_stats(value))
    
    def get_articles(self, *pids):
        pipe = self.db.pipeline()
        for pid in pids:
            pipe.lrange(self.ns.page_inlinks(pid), 0, -1)
            pipe.lrange(self.ns.page_outlinks(pid), 0, -1)
            pipe.lrange(self.ns.page_labels(pid), 0, -1)
        data = pipe.execute()
        
        results = []
        for i in xrange(0, len(data)-1, 3):
            labels = []
            json_labels = data[i+2]
            for json_label in json_labels:
                label = json.loads(json_label)
                labels.append({
                    'title': label[0],
                    'occurances': label[1],
                    'fromRedirect': label[2],
                    'fromTitle': label[3],
                    'isPrimary': label[4],
                    'proportion': label[5] 
                })
            result = {
                "InLinks":data[i],
                "OutLinks":data[i+1],
                "Labels":labels
            }
            results.append(result)
        return results