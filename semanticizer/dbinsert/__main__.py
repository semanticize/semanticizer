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

import yaml
import sys
import getopt

from ..wpm.load import WpmLoader
from ..config import config_get

def load_wpm_data(datasource, langcode, **kwargs):
    if datasource == "redis":
        from ..wpm.db.redisdb import RedisDB
        db = RedisDB(**kwargs)
        WpmLoader(db, langcode, **kwargs)
    elif datasource == "mongo":
        from ..wpm.db.mongodb import MongoDB
        db = MongoDB(**kwargs)
        WpmLoader(db, langcode, **kwargs)
    else:
        raise ValueError("No %s backend for language %s" % (datasource, langcode))



##
## usage
## python -m semanticizer.dbinsert --language=<languagecode> --output=/tmp/redisinsert.log
if __name__ == '__main__':
    configYaml = yaml.load(file('conf/semanticizer.yml'))
    wpm_languages = config_get(('wpm', 'languages'), None, configYaml)
    settings = config_get("settings", {}, configYaml)
    try:
       opts, args = getopt.getopt(sys.argv[1:], 'l:o:', ['language=', 'output='])
    except getopt.GetoptError:
       usage()
       sys.exit(2)

    showprogress = True
    output = None
    language = None

    for opt, arg in opts:
        if opt in ('-l', '--language'):
            language = arg
        elif opt in ('-o', '--output'):
            output = arg

    if output:
        f = open(output, "w+")
        sys.stdout = f
        showprogress = False

    #if language code is specified only import that language
    if language and wpm_languages[language]:
        load_wpm_data(wpm_languages[language]['source'], language, settings, progress=showprogress, **wpm_languages[language]['initparams'])
    #else important all languages in the config file
    else:
        for langcode, langconfig in wpm_languages.iteritems():
            load_wpm_data(langconfig['source'], langcode, settings, progress=showprogress, **langconfig['initparams'])

