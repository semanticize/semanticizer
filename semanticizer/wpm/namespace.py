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

class WpmNS:
    def __init__(self, db, langcode, version=None):
        self.sep = ':'
        self.lc  = langcode
        self.db  = db
        self.manual_version = version
   
    def version (self):
        if self.manual_version:
            return self.manual_version
        version = self.db.get(self.db_version())
        if not version:
            raise Exception("No database version") 
        return version
    
    def db_version(self):
        """
        key
            <langcode>:db:version
        value
            string(cache version)
        """
        return self.sep.join( (self.lc, "db", "version") ) 
    
    def wiki_language_name(self):
        """
        key
            <langcode>:<version>:wiki:lname
        value
            string(wiki name)
        """
        return self.sep.join( (self.lc, self.version(), "wiki", "lname") )
        
    def wiki_path(self):
        """
        key
            <langcode>:<version>:wiki:path
        value
            string(wiki path)
        """
        return self.sep.join( (self.lc, self.version(), "wiki", "path") )
    
    def wiki_stats(self, statName):
        """
        key
            <langcode>:<version>:wiki:stats:<statName>
        value
            string(stats)
        """
        return self.sep.join( (self.lc, self.version(), "wiki", "stats", statName) )
    
    def label(self, name):
        """
        key
            <langcode>:<version>:label:<name>
        value
            list( LinkOccCount, LinkDocCount, TextOccCount, TextDocCount, SenseId, SenseId, ..)
        """
        return self.sep.join( (self.lc, self.version(), "label", name) )

    def label_sense(self, name, senseid):
        """
        key
            <langcode>:<version>:label:<name>:<senseid>
        value
            list( sLinkDocCount, sLinkOccCount, FromTitle, FromRedirect)
        """
        return self.sep.join( (self.lc, self.version(), "label", name, senseid) )

    def normalized(self, name):
        """
        key
            <langcode>:<version>:norm:<name>
        value
            set( name, name, ... )
        """
        return self.sep.join( (self.lc, self.version(), "norm", name) )

    def translation_sense(self, senseid):
        """
        key
            <langcode>:<version>:trnsl:<senseid>
        value
            list( langcode, langcode, ... )
        """
        return self.sep.join( (self.lc, self.version(), "trnsl", senseid) )

    def translation_sense_language(self, senseid, langcode):
        """
        key
            <langcode>:<version>:trnsl:<senseid>:<langcode>
        value
            string(name)
        """
        return self.sep.join( (self.lc, self.version(), "trnsl", senseid, langcode) )

    def page_id(self, name):
        """
        key
            <langcode>:<version>:page:id<name>
        value
            string(id)
        """
        return self.sep.join( (self.lc, self.version(), "page", "id", name) )
    
    def page_title(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:name
        value
            string(name)
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "name") )
    
    def page_labels(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:labels
        value
            list( json([title, occurances, fromRedirect, fromTitle isPrimary, proportion]), ...)
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "labels") )
 
    def page_definition(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:definition
        value
            string(synopsis)
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "definition") )
 
    def page_inlinks(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:inlinks
        value
            list( pageid, pageid, ... )
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "inlinks") )
 
 
    def page_outlinks(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:outlinks
        value
            list( pageid, pageid, ... )
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "outlinks") )

    def page_categories(self, pageid):
        """
        key
            <langcode>:<version>:page:<pageid>:categories
        value
            list( category, category, ... )
        """
        return self.sep.join( (self.lc, self.version(), "page", pageid, "categories") )


    def ngramscore(self, n):
        """
        key
            <langcode>:<version>:<n>grms
        value
            zset([words{score}, [...]])translation_sense
        """
        return self.sep.join( (self.lc, self.version(), "%sgrms" % n) )
    