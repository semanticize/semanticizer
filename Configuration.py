"""
This module is responsible for loading all possible configuration params and their defaults,
overwriting the defaults by reading values from a given config file, then overwriting these
values to whatever's been passed as argument. 
"""

from ConfigParser import SafeConfigParser
from argparse import ArgumentParser
from argparse import ArgumentTypeError
from argparse import Action
from urlparse import urlparse
import os
import stat
from sys import argv

__options = None
_data = argv[1:]

def _readable_path(value):
    """
    Checks whether a path exists and raises an error if it doesn't
    """
    path = os.path.abspath(value)
    if os.path.exists(path) and bool(os.stat(path).st_mode & stat.S_IRUSR):
        return path
    raise ArgumentTypeError("path doesn't exist or isn't readable: %s" % path)
    
def _writable_file(value):
    """
    Checks whether a given file is writable, and if it doesn't exist, whether it can be
    created. Returns the full path to the file.
    """
    path = os.path.abspath(value)
    if not os.path.exists(path):
        parent = os.path.dirname(path)
        if os.path.exists(parent) and bool(os.stat(parent).st_mode & stat.S_IWUSR):
            return path
    elif bool(os.stat(path).st_mode & stat.S_IWUSR):
        return path
    raise ArgumentTypeError("file doesn't exist or isn't writeable (parent must exist and be writable): %s" % path)

def _valid_absolute_url(value):
    """
    Checks whether a given URL is valid, and throws an ArgumentTypeError if it isn't.
    Otherwise returns the given URL.
    """
    url = urlparse(value)
    if url.scheme and url.netloc:
        return value
    raise ArgumentTypeError("URL isn't valid: %s" % value)

class ValidateLangloc(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        """
        Checks whether a valid langloc path was given.
        """
        values[2] = _readable_path(values[2])
        langloc = [(values[0], values[1], values[2])]
        if hasattr(namespace, self.dest) and getattr(namespace, self.dest):
            langloc += getattr(namespace, self.dest)
        setattr(namespace, self.dest, langloc)

USAGE = "%(prog)s [options]"

ARGS = {"generic":  [{"name":     "--verbose",
                      "opts":    {"help":     "Set high verbosity",
                                  "action":   "store_true"}},
                         
                     {"name":     "--threads",
                      "opts":    {"help":     "Number of threads to use (default: %(default)s)",
                                  "metavar":  "NUM",
                                  "type":     int,
                                  "default":  16}},
                     
                     {"name":     "--tmpdir",
                      "opts":    {"help":     "Number of threads to use (default: %(default)s)",
                                  "metavar":  "DIR",
                                  "type":     _writable_file}},
        
                     {"name":     "--log",
                      "opts":    {"help":     "Log file location (default: %(default)s)",
                                  "default":  "log.txt",
                                  "metavar":  "FILE",
                                  "type":     _writable_file}}],
            
        "service":  [{"name":     "--port",
                      "opts":    {"help":     "Port number to start services (counting upwards) (default: %(default)s)",
                                  "metavar":  "NUM",
                                  "type":     int,
                                  "default":  5000}}],
            
        "language": [{"name":     "--lm",
                      "opts":    {"help":     "language model root (default: %(default)s)",
                                  "metavar":  "DIR",
                                  "default":  "LM.lrej2011",
                                  "type":     _readable_path}},
        
                     {"name":     "--langloc",
                      "opts":    {"help":     "Add accepted language (see --listlang), followed by 2 character wikipedia language code and the location for wikipediaminer dump (default: english en /zfs/ilps-plexer/wikipediaminer/enwiki-20111007/)",
                                  "nargs":    3,
                                  "action":   ValidateLangloc,
                                  "metavar":  ("LANG", "LANGCODE", "LOC")}},
        
                     {"name":     "--stopword",
                      "opts":    {"help":     "Location of the stopword dir (default: %(default)s)",
                                  "metavar":  "DIR",
                                  "default":  "SW",
                                  "type":     _readable_path}},
        
                     {"name":     "--article",
                      "opts":    {"help":     "Location article webservices (default: %(default)s)",
                                  "metavar":  "URL",
                                  "default":  "http://zookst13.science.uva.nl:8080/dutchsemcor/article",
                                  "type":     _valid_absolute_url}}],
            
        "learning": [{"name":     "--features",
                      "opts":    {"help":     "Include features",
                                  "action":   "store_true"}},
                         
                     {"name":     "--scikit",
                      "opts":    {"help":     "Run own version of scikit",
                                  "action":   "store_true"}},
                         
                     {"name":     "--learn",
                      "opts":    {"help":     "Location scikit-learn webservices (default: %(default)s)",
                                  "metavar":  "URL",
                                  "default":  "http://fietstas.science.uva.nl:5001",
                                  "type":     _valid_absolute_url}}],
            
        "commands": [{"name":     "--listlang",
                      "opts":    {"help":     "List languages that can be recognized",
                                  "action":   "store_true"}}]
        }

def _get_conf_vals(path='conf/semanticizer.cfg'):
    """
    Returns all configuration keys and values in a list.
    """
    config = SafeConfigParser(allow_no_value=True)
    config.read(path)
    confvars = list()
    for section in config.sections():
        items = config.items(section)
        for key, value in items:
            if value:
                val = value.split()
                confvars += ["--" + key] + val
            else:
                confvars += ["--" + key]
    return confvars

def _get_arg_parser():
    """
    Initialize and return an ArgumentParser based on the ARGS structure as laid-out above.
    """
    global _data
    parser = ArgumentParser(usage=USAGE)
    for groupname, groupdata in ARGS.iteritems():
        group = parser.add_argument_group(groupname)
        for arg in groupdata:
            group.add_argument(arg['name'], **arg['opts'])
        parser.add_argument_group(group)
    return parser
    
def _set_conf():
    """
    Read argument list and defaults, read configuration and overwrite defaults where necessary,
    read the program arguments and return the parser
    """
    global __options, _data
    parser = _get_arg_parser()
    conf_vals = _get_conf_vals()
    args = vars(parser.parse_args(conf_vals))
    args_argv = vars(parser.parse_args(_data))
    for k in _data:
        if not k.startswith("-"): continue
        key = k.lstrip("-")
        if key in args_argv and args_argv[key] is not args[key] and args_argv[key] is not None:
            args.update({key: args_argv[key]})
    
    __options = args

def set_data(data):
    """
    Set the data that should be loaded by this configuration. Default is sys.argv[1:]. Only effective
    if called before the first call to conf_get().
    """
    global _data
    if type(data) is list:
        _data = data

def conf_get(name):
    """
    Allows user to access configuration variables and arguments. The function takes the variable name
    as its input, and returns the value or None is it isn't set.
    """
    global __options
    if not __options:
        _set_conf()
    if name in __options:
        return __options[name]
    return None
