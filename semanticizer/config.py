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

"""
This module is responsible for loading all possible configuration params and
their defaults, overwriting the defaults by reading values from a given config
file, then overwriting these values to whatever's been passed as argument.
"""
import yaml
import sys
import argparse
import traceback

def load_config(path='conf/semanticizer.yml'):
    
    #add command line args
    parser = argparse.ArgumentParser(description="""
            Run sematicizer.""")
       
    parser.add_argument("-p", "--port", help="Port number ")
    parser.add_argument("-v", "--verbose", help="Verbose ")
    parser.add_argument("-s", "--host", help="Host ip address ")
    parser.add_argument("-c", "--config", help="Config file ")
     
    args = parser.parse_args()
    
    if args.config != None:
        path = args.config
    
    configYaml = yaml.load(file(path))
    
    if args.port != None:
        configYaml["server"]["port"] = int(args.port)
        
    if args.verbose != None:
        configYaml["logging"]["verbose"] = str2bool(args.verbose)
    
    if args.host != None:
        configYaml["server"]["host"] = args.host
    
    return configYaml
    
def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def config_get(keys=(), default=None, config=None):
    """
    Allows user to access configuration variables and arguments. The function
    takes the variable name as its input, and returns the value or None is it
    isn't set.

    @param keys: The name of the configuration parameter to fetch. (Optional)
    @param default: The default value to return if the key is not found.
    @param config: dictionary to represent config. If None, load_config is
                   called.
    @return: The value for the given parameter if name was set and valid, \
             the default value if invalid or None if no default value was set.
    """
    if config is None:
        config = load_config()

    if isinstance(keys, basestring):
        keys = [keys]
    
    pointer = config
    for key in keys:
        if not key in pointer:
            if default is not None:
                return default
            else:
                raise KeyError('Could not find %s in configuration' % key)
        pointer = pointer[key]
        
    index = 0
    return pointer
