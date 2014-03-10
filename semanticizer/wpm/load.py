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

import codecs
import json
import glob

from .namespace import WpmNS
from .utils import normalize, check_dump_path, dump_filenames, generate_markup_definition, cli_progress

class WpmLoader:
    def __init__(self, db, langcode, settings, langname=None, path=None, translation_languages=None, progress=False, **kwargs):
        print "db", db
        print "langcode", langcode
        
        # TODO: This is ugly; skipping data should be in the yml file [DG]
        skip_files = []
        if not translation_languages:
            skip_files.append("translations")
        else:
          print "Translation languages:", translation_languages
        if settings.get("include_categories", False):
            skip_files.append("pageCategories")
        if settings.get("include_definitions", False):
            skip_files.append("pages-articles") 
          
        path = check_dump_path(path, skip_files)
        
        #show progress in CLI when execting insert, not for in memory
        self.progress = progress
        
        #ammount of requests before sending pipe to server
        self.pipechunk = 250
        
        #generate unique version, so that existing db can exist while new one is imported, use simpel integer to prevent long key (reduce memory)
        try:
            self.version = str(int(db.get(":".join((langcode, "db", "version")))) + 1)
        except:
            self.version = "0"
        
        #which translation languages to include in results 
        self.translation_langs = translation_languages if translation_languages is not None else []
        
        #load db key name class manager
        self.ns = WpmNS(db, langcode, version=self.version)  
        
        #set general database values
        self.db = db
        self.db.set(self.ns.wiki_language_name(), langname) 
        self.db.set(self.ns.wiki_path(), path) 
        
        #start loading the new data
        # TODO: This is ugly too, skip_files <-> load data should be smoother [DG]
        for filetype in skip_files:
            print "Skipping " + filetype
        print "Loading new db: ", self.version
        self.load_stats(path + dump_filenames["stats"])
        self.load_labels(path + dump_filenames["labels"])
        self.load_links(path + dump_filenames["inlinks"])
        self.load_links(path + dump_filenames["outlinks"], inlinks = False)
        if "translations" not in skip_files:
            self.load_translations(path + dump_filenames["translations"])
        self.load_page_titles(path + dump_filenames["pages"])
        self.load_page_labels(path + dump_filenames["pageLabels"])
        if "pageCategories" not in skip_files:
            self.load_page_categories(path + dump_filenames["pageCategories"])
        if "pages-articles" not in skip_files:
            self.load_definitions(glob.glob(path + '*-pages-articles.xml')[0])

        #make new dataset active and remove old dataset
        self.cleanup(langcode)
        
            
    def cleanup(self, langcode):
        print '\nStart cleanup...'
        #get old version identifier
        oldversion = self.db.get(self.ns.db_version())
        
        print '--set new db version active'
        #make new version active
        self.db.set(self.ns.db_version(), self.version) 
        
        #delete old version and data if it exists (in batches for performance)
        print '--delete old db version'
        if oldversion:
            oldkeys = self.db.keys(langcode+":"+oldversion+"*")
            step = 1000
            total = len(oldkeys)
            for idx in xrange(0, total, step):
                if self.progress:
                    cli_progress(idx+step, total)
                chunk = oldkeys[idx:idx+step]
                self.db.delete(*chunk)
        print '\nDone cleanup...'
            
    def load_stats(self, filename):
        """
        line = 'articleCount,1978981  
        {stattext},{statvalue}
        """
        print '\nLoading Wiki stats...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                statName, statValue = line.split(",")
                # remove "'" from string
                statName = statName[1:]
                pipe.set(self.ns.wiki_stats(statName), statValue)
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line
                print str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading Wiki stats (%d stats loaded)' % (linenr+1)
    
    def load_labels(self, filename):
        """
        line = 'Activiteitscoefficient,0,0,0,0,v{s{248591,0,0,F,T}}
        {text},{LinkOccCount},{LinkDocCount},{TextOccCount},{TextDocCount}[{sense}, {sense}, ...]
        ---- 
        sense = s{248591,0,0,F,T}
        [{pageid}, {sLinkOccCount}, {sLinkDocCount}, {FromTitle}, {FromRedirect}]
        """
        print '\nLoading labels ...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
        
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                stats_part, senses_part = line.split(',v{')
                senses = senses_part[:-1].split('s')[1:]
                stats = stats_part[1:].split(',')
                text = stats[0]
                txtkey = self.ns.label(text)
                pipe.rpush(txtkey, *stats[1:])
                for sense_text in senses:
                    sense_parts = sense_text[1:-1].split(',')
                    sense_parts[-1] = sense_parts[-1][0]
                    pipe.rpush(txtkey, sense_parts[0])
                    pipe.rpush(self.ns.label_sense(text, sense_parts[0]), *sense_parts[1:])
                normalized = normalize(text)
                pipe.sadd(self.ns.normalized(normalized), text)
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line
                print str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading labels (%d labels loaded)' % (linenr+1)
    
    def load_links(self, filename, inlinks = True):
        """
        line = 1,v{ s{83,v{402,557}}, s{755,v{45}}, s{756,v{1017} }
        {pageid},[{article},{article}, ...]
        ---- 
        article = s{83,v{402,557}}
        [{pageid}, [{sentence}, {sentence}, ...]
        """
        if inlinks:
            print "\nLoading inlinks ..."
        else:
            print "\nLoading outlinks ..."
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        
        if inlinks:
            ns_function = self.ns.page_inlinks
        else:
            ns_function = self.ns.page_outlinks
        
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                page_id, links = line.split(',v{s{')
                page_id_key = ns_function(page_id)
                for link in links.split('s{'):
                    id = link.split(',')[0]
                    pipe.rpush(page_id_key, id)
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1), str(e)# + ": " + line
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading links'

    
    def load_translations(self, filename):
        """
        line = 1311,m{'de,'Protokoll,'en,'Transcript (law),'it,'Registro di protocollo,'pt,'Registro de protocolo}
        {pageid},[{langcode}, {pagetitle}, {langcode}, {pagetitle}...]
        """
        print '\nLoading translations...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                tr_id_str, translation_part = line.strip()[:-1].split(",m{'")
                tr_id = tr_id_str
                parts = translation_part.split(",'")
                for i in range(0, len(parts), 2):
                    lang = parts[i]
                    if lang in self.translation_langs:
                        pipe.rpush(self.ns.translation_sense(tr_id), lang)
                        pipe.set(self.ns.translation_sense_language(tr_id, lang), parts[i + 1])
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line, str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading translations'
    
    def load_page_titles(self, filename):
        """
        line = 1,'Albert Speer,0,5
        {pageid},{text},{type},{depth}
        """
        print '\nLoading page titles...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                splits = line.split(',')
                pageid = splits[0]
                title = splits[1][1:]
                pipe.set(self.ns.page_title(pageid), title)
                pipe.set(self.ns.page_id(title), pageid)
                
                ##store_title_as_ngram
                words = title.split()
                for n in range(1, len(words) + 1):
                    for i in range(0, len(words) - n):
                        ngram = " ".join(words[i:i + n])
                        pipe.zincrby(self.ns.ngramscore(str(n - i)), ngram, 1)
                      
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line, str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading pages (%d pages loaded)' % (linenr+1)
    
    def load_page_labels(self, filename):
        """
        line = 1,v{s{'Albert Speer,118,111,F,T,T},s{'Speer,5,5,F,F,T}}
        {pageid},[{label}, {label}, ...]
        """
        print '\nLoading page labels...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                pageid, labels_part = line.split(",v{s{")
                labels = labels_part[:-1].split(",s{")
                results = []
                total = 0
                for label in labels: 
                    data = label[:-1].split(",")
                    total += int(data[1])
                    result = [
                        data[0][1:],                        #title
                        int(data[1]),                       #occurances
                        True if data[3] is "T" else False,  #fromRedirect
                        True if data[4] is "T" else False,  #fromTitle
                        True if data[5] is "T" else False   #isPrimary
                    ] #use list for memory optimisations in db storage
                    results.append(result)

                for i, label in enumerate(results):
                    result = results[i]
                    result.append( 0.0 if result[1] is 0 or total is 0 else float(result[1])/float(total) ) #proportion
                    pipe.rpush(self.ns.page_labels(pageid), json.dumps(result))
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line, str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading page labels'
            
            
    def load_page_categories(self, filename):
        """
        line = 1,v{71598,128543,835917,1041431,1809466}
        {pageid},[{categoryid}, {categoryid}, ...]
        """
        print '\nLoading page categories...'
        
        if self.progress:
            num_lines = sum(1 for line in open(filename)) 
            
        pipe = self.db.pipeline(transaction=False)
        file = codecs.open(filename, "r", "utf-8")
        for linenr, line in enumerate(file):
            if self.progress and linenr % 10 is 0:
                cli_progress(linenr+1, num_lines)
            try:
                pageid, categories_part = line.split(",v{")
                categories = categories_part[:-1].split(",")
                categorykey = self.ns.page_categories(pageid)
                pipe.rpush(categorykey, *categories)
                if len(pipe) >= self.pipechunk:
                    pipe.execute()
            except Exception,e:
                print "Error loading on line " + str(linenr+1) + ": " + line
                print str(e)
                continue
        pipe.execute()
        file.close()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading page categories'

        
    def load_definitions(self, filename):
        print '\nLoading page definitions...'
        try:
            import lxml.etree as ET # ElementTree API using libxml2
            print "Using 'lxml.etree' parser"
        except ImportError:
            try:
                import cElementTree as ET # effbot's C module
                print "Using 'cElementTree' parser"
            except ImportError:
                print "Using 'xml.etree' parser"
                import xml.etree.ElementTree as ET
        if self.progress:
            num_lines = sum(1 for line in open(filename) if '<page' in line) 
        elementnr = 1
        pipe = self.db.pipeline(transaction=False)
        for event, element in ET.iterparse(filename):
            if element.xpath('local-name()') == 'page':
                elementnr += 1
                if self.progress and linenr % 10 is 0:
                    cli_progress(elementnr, num_lines)
                try:
                    namespace = element.tag[1:element.tag.index('}')] or ""
                    id     = element.find('.//n:id', namespaces={'n': namespace})
                    markup = element.find('.//n:revision/n:text', namespaces={'n': namespace})

                    if markup is not None and markup.text:
                        definition = generate_markup_definition(markup.text)
                    else:
                        definition = ""
                    pipe.set(self.ns.page_definition(id.text), definition)
                    element.clear()
                    del element # for extra insurance 
                    
                    if len(pipe) >= 100:
                        pipe.execute()                    
                except Exception, e:
                    print "Error loading on element: ", elementnr, str(e)
                    continue
        pipe.execute()
        if self.progress:
            cli_progress(linenr, num_lines)
        print '\nDone loading page definitions'
