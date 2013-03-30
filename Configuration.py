'''
Created on 27 Mar 2013

@author: evert
'''

from ConfigParser import SafeConfigParser
from optparse import OptionParser
from optparse import OptionGroup

class Conf:

    USAGE = "Usage: %prog [options]"

    ARGS = {"generic":  [{"name":    "--verbose",
                          "misc":    {"help":    "Set high verbosity",
                                      "action":  "store_true"}},
                         
                         {"name":    "--threads",
                          "misc":    {"help":    "Number of threads to use (default: %default)",
                                      "metavar": "NUM",
                                      "type":    "int",
                                      "default":  16}},
        
                         {"name":    "--log",
                          "misc":    {"help":    "Log file location (default: %default)",
                                      "default": "log.txt",
                                      "metavar": "FILE"}}],
            
            "service":  [{"name":    "--port",
                          "misc":    {"help":    "Port number to start services (counting upwards) (default: %default)",
                                      "metavar": "NUM",
                                      "type":    "int",
                                      "default":  5000}}],
            
            "language": [{"name":    "--lm",
                          "misc":    {"help":    "language model root (default: %default)",
                                      "metavar": "DIR",
                                      "default": "LM.lrej2011"}},
        
                         {"name":    "--langloc",
                          "misc":    {"help":    "Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump (default: english en /zfs/ilps-plexer/wikipediaminer/enwiki-20111007/)",
                                      "nargs":   3,
                                      "action":  "append",
                                      "metavar": "LANG LANGCODE LOC"}},
        
                         {"name":    "--stopword",
                          "misc":    {"help":    "Location of the stopword dir (default: %default)",
                                      "metavar": "DIR",
                                      "default": "SW"}},
        
                         {"name":    "--article",
                          "misc":    {"help":    "Location article webservices (default: %default)",
                                      "metavar": "URL",
                                      "default":  "http://zookst13.science.uva.nl:8080/dutchsemcor/article"}}],
            
            "learning": [{"name":    "--features",
                          "misc":    {"help":    "Include features",
                                      "action":  "store_true"}},
                         
                         {"name":    "--scikit",
                          "misc":    {"help":    "Run own version of scikit",
                                      "action":  "store_true"}},
                         
                         {"name":    "--learn",
                          "misc":    {"help":    "Location scikit-learn webservices (default: %default)",
                                      "metavar": "URL",
                                      "default":  "http://fietstas.science.uva.nl:5001"}}],
            
            "commands": [{"name":    "--listlang",
                          "misc":    {"help":    "List languages that can be recognized",
                                      "action":  "store_true"}}]
            }
    
    def __init__(self, conffile='conf/semanticizer.cfg'):
        self.conffile = conffile
        
    def get_conf(self):
        config = SafeConfigParser()
        config.read(self.conffile)
        parser = OptionParser(usage=self.USAGE)
        for groupname in self.ARGS:
            group = OptionGroup(parser, groupname)
            for arg in self.ARGS[groupname]:
                if config.has_section(groupname) and config.get(groupname, arg['name'].lstrip('-')):
                    if 'nargs' in arg['misc']:
                        arg['misc']['default'] = [ config.get(groupname, arg['name'].lstrip('-')).split() ]
                    else:
                        arg['misc']['default'] = config.get(groupname, arg['name'].lstrip('-'))
                group.add_option(arg['name'], **arg['misc'])
            parser.add_option_group(group)
            
        return parser
