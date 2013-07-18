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

def load_config(path='conf/semanticizer.yml'):
    print "get config"
    return yaml.load(file(path))

def config_get(keys=(), default=None, config=load_config()):
    """
    Allows user to access configuration variables and arguments. The function
    takes the variable name as its input, and returns the value or None is it
    isn't set.

    @param keys: The name of the configuration parameter to fetch. (Optional)
    @param default: The default value to return if the key is not found.
    @param config: dictionary to represent config
    @return: The value for the given parameter if name was set and valid, \
             the default value if invalid or None if no default value was set.
    """
    if type(keys) == str:
        keys = [keys]
    
    pointer = config
    for key in keys:
        if not key in pointer:
            if default != None:
                return default
            else:
                raise KeyError('Could not find %s in configuration' % key)
        pointer = pointer[key]
    return pointer
