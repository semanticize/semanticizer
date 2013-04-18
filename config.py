"""
This module is responsible for loading all possible configuration params and
their defaults, overwriting the defaults by reading values from a given config
file, then overwriting these values to whatever's been passed as argument.
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
    Checks whether a path exists and raises an error if it doesn't.

    @param value: The pathname to check
    @return: The absolute path denoted by path
    @raise ArgumentTypeError: If the path doesn't exist or isn't readbale
    """
    path = ''
    pathlist = [os.path.abspath(value),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), value)
                ]
    for path in pathlist:
        if os.path.exists(path) and bool(os.stat(path).st_mode & stat.S_IRUSR):
            return path
    raise ArgumentTypeError("path doesn't exist or isn't readable: %s" % path)


def _writable_file(value):
    """
    Checks whether a given file is writable, and if it doesn't exist, whether
    it can be created. Returns the full path to the file.

    @param value: The path to the file
    @return: The absolute path denoted by value
    @raise ArgumentTypeError: If the file doesn't exist or cannot be created \
                              (parent dir must exist)
    """
    path = ''
    pathlist = [os.path.abspath(value),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), value)
                ]
    for path in pathlist:
        if not os.path.exists(path):
            parent = os.path.dirname(path)
            if os.path.exists(parent) and \
               bool(os.stat(parent).st_mode & stat.S_IWUSR):
                return path
        elif bool(os.stat(path).st_mode & stat.S_IWUSR):
            return path
    raise ArgumentTypeError("file doesn't exist or isn't writeable (parent \
                             must exist and be writable): %s" % path)


def _valid_absolute_url(value):
    """
    Checks whether a given URL is valid, and throws an ArgumentTypeError if it
    isn't. Otherwise returns the given URL.

    @param value: The URL to check
    @return: The same value
    @raise ArgumentTypeError: If URL isn't deemed valid by the urlparse module
    """
    url = urlparse(value)
    if url.scheme and url.netloc:
        return value
    raise ArgumentTypeError("URL isn't valid: %s" % value)


class ValidateWpmData(Action):
    """
    A custum Action to check whether a valid langloc was given

    @see: argparse.Action
    """
    def __call__(self, parser, namespace, values, option_string=None):
        """
        Checks whether a valid --langloc was given.

        @param parser: The current ArgumentParser
        @param namespace: The current namespace object
        @param values: The list of langloc values
        @param option_string: The name of the option (in this case, \
                              just --langloc)
        @todo: Make this action available for langloc, stopword, and \
               lm arguments
        """
        values[2] = _readable_path(values[2])
        langloc = {}
        if hasattr(namespace, self.dest) and getattr(namespace, self.dest):
            langloc = getattr(namespace, self.dest)
        langloc[values[1]] = [values[0], values[2]]
        setattr(namespace, self.dest, langloc)

USAGE = "%(prog)s --wpmdata LANG LANGCODE LOC [other options]"

ARGS = {"logging":  [
           {"name":     "--verbose",
            "opts":    {"help":     "Switch verbose mode on",
                        "action":   "store_true"}},

           {"name":     "--log",
            "opts":    {"help":     "Path to log file (default: %(default)s)",
                        "default":  "log.txt",
                        "metavar":  "FILE",
                        "type":     _writable_file}},

           {"name":     "--logformat",
            "opts":    {"help":     "Set custom format for the logs \
                                     (optional)",
                        "metavar":  "STR",
                        "default":  "[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s",
                        "type":     str}}],

        "service":  [
           {"name":     "--port",
            "opts":    {"help":     "Port number to start services \
                                     (default: %(default)s)",
                        "metavar":  "NUM",
                        "type":     int,
                        "default":  5000}},

           {"name":     "--host",
            "opts":    {"help":     "Host to start services \
                                     (default: %(default)s)",
                        "metavar":  "HOST",
                        "type":     str,
                        "default":  "0.0.0.0"}}],

        "language": [
           {"name":     "--wpmdata",
            "opts":    {"help":     "Data on a Wikipediaminer dump: the \
                                     language, language code, and path to the \
                                     dump.",
                        "nargs":    3,
                        "action":   ValidateWpmData,
                        "metavar":  ("LANG", "LANGCODE", "LOC")}},

           {"name":     "--wpmdatasource",
            "opts":    {"help":     "Class to fetch data with \
                                     (default: %(default)s)",
                        "default":  "wpm.wpmdata_inproc.WpmDataInProc",
                        "metavar":  'CLASS',
                        "type":     str}},

           {"name":     "--langcodes",
            "opts":    {"help":     "Supported language codes (must have \
                                     their wikipediaminer dumps loaded)",
                        "default":  "",
                        "metavar":  'LANGCODE[,LANGCODE[, ...]]'}},

           {"name":     "--lmpath",
            "opts":    {"help":     "Path to language model files \
                                     (default: %(default)s)",
                        "metavar":  "DIR",
                        "default":  "LM.lrej2011",
                        "type":     _readable_path}}],

        "learning": [
           {"name":     "--features",
            "opts":    {"help":     "Include features",
                        "action":   "store_true"}},

           {"name":     "--scikiturl",
            "opts":    {"help":     "Location of scikit-learn webservices \
                                     (default: use internal scikit_light)",
                        "metavar":  "URL",
                        "type":     _valid_absolute_url}},

           {"name":     "--wpmurl",
            "opts":    {"help":     "Location article webservices \
                                     (default: %(default)s)",
                        "metavar":  "URL",
                        "default":  "http://zookst13.science.uva.nl:8080/dutchsemcor/article",
                        "type":     _valid_absolute_url}},

           {"name":     "--wpmthreads",
            "opts":    {"help":     "Number of threads for Wikipedia miner \
                                     (default: %(default)s)",
                        "metavar":  "NUM",
                        "type":     int,
                        "default":  16}},

           {"name":     "--cachedir",
            "opts":    {"help":     "Directory to store pickles in"
                                    + "(default: $TEMPDIR)",
                        "metavar":  "DIR",
                        "type":     _writable_file}}]
        }


def _get_conf_vals(path='conf/semanticizer.cfg'):
    """
    Returns all configuration keys and values in a list.
    @param path: Path to the configuration file
    @return: A list of configured parameters
    """
    config = SafeConfigParser(allow_no_value=True)
    config.read(path)
    confvars = list()
    for section in config.sections():
        items = config.items(section, raw=True)
        for key, value in items:
            if value:
                nargs = get_conf_prop(key, "nargs")
                if nargs is not None and int(nargs) > 1:
                    val = value.split()
                else:
                    val = [value]
                confvars += ["--" + key] + val
            else:
                confvars += ["--" + key]
    return confvars


def _get_arg_parser():
    """
    Initialize and return an ArgumentParser based on the ARGS structure as
    laid-out above.

    @return: a configured instance of ArgumentParser
    """
    parser = ArgumentParser(usage=USAGE)
    for groupname, groupdata in ARGS.iteritems():
        group = parser.add_argument_group(groupname)
        for arg in groupdata:
            group.add_argument(arg['name'], **arg['opts'])
        parser.add_argument_group(group)
    return parser


def _set_conf():
    """
    Read argument list and defaults, read configuration and overwrite defaults
    where necessary, read the program arguments and return the parser
    """
    global __options
    parser = _get_arg_parser()
    conf_vals = _get_conf_vals()
    args = vars(parser.parse_args(conf_vals))
    args_argv = vars(parser.parse_args(_data))
    for k in _data:
        if not k.startswith("-"):
            continue
        key = k.lstrip("-")
        if key in args_argv and args_argv[key] is not args[key] \
                            and args_argv[key] is not None:
            args.update({key: args_argv[key]})

    __options = args


def set_data(data):
    """
    Set the data that should be loaded by this configuration. Default is
    sys.argv[1:]. Only effective if called before the first call to conf_get().

    @param data: A list of arguments
    """
    global _data
    if type(data) is list:
        _data = data


def conf_get(name=None):
    """
    Allows user to access configuration variables and arguments. The function
    takes the variable name as its input, and returns the value or None is it
    isn't set.

    @param name: The name of the configuration parameter to fetch. (Optional)
    @return: The value for the given parameter if name was set and valid, \
             None if name was invalid, or the full list of configuration \
             params if name==None
    """
    if not __options:
        _set_conf()
    if name == None:
        return __options
    if name in __options:
        return __options[name]
    return None


def get_conf_prop(name, propname):
    """
    Allows user to get a property for given name. Returns the value of the \
    property, or None if none is found.

    @param name: The argument we want to fetch the property of
    @param propname: The name of the property to fetch
    @return: The value of the property, or None if none is found.
    """
    name = "--" + name
    for groupdata in ARGS.itervalues():
        for arg in groupdata:
            if arg["name"] == name:
                if propname in arg["opts"]:
                    return arg["opts"][propname]
                return None
    return None
