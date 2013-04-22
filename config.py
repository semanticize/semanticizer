"""
This module is responsible for loading all possible configuration params and
their defaults, overwriting the defaults by reading values from a given config
file, then overwriting these values to whatever's been passed as argument.
"""
import yaml

path = 'conf/semanticizer.yml'


def conf_get(*keys):
    """
    Allows user to access configuration variables and arguments. The function
    takes the variable name as its input, and returns the value or None is it
    isn't set.

    @param name: The name of the configuration parameter to fetch. (Optional)
    @return: The value for the given parameter if name was set and valid, \
             None if name was invalid, or the full list of configuration \
             params if name==None
    """
    if 'data' not in conf_get.__dict__:
        conf_get.data = yaml.load(file(path))
    pntr = conf_get.data
    for key in keys:
        if not key in pntr:
            raise KeyError('Could not find %s in configuration' % key)
        pntr = pntr[key]
    return pntr
