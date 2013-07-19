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

class LinksProcessor:
    '''A LinksProcessor takes a set of links, a text and a language code to 
       produce or process links. Processing is done in two steps, a preprocessing
       step and a processing step. '''
       
    def preprocess(self, links, text, settings):
        return (links, text, settings)
        
    def process(self, links, text, settings):
        return (links, text, settings)

    def postprocess(self, links, text, settings):
        return (links, text, settings)
        
    def inspect(self):
        return {}

class SettingsProcessor(LinksProcessor):
    def __init__(self, settings):
        self.settings = settings
        
    def preprocess(self, links, text, settings):
        if "settings" in settings and settings["settings"] in self.settings:
            for k, v in self.settings[settings["settings"]].iteritems():
                if k not in settings:
                    settings[k] = v
            del settings["settings"]
        return (links, text, settings)
    def inspect(self):
        return {self.__class__.__name__: self.settings}

class FilterProcessor(LinksProcessor):
    def __init__(self):
        self.context_links = {}

    def preprocess(self, links, text, settings):
        if settings.has_key("prefilter"):
            links = self.filter_links(settings["prefilter"].split(","), links, settings)

        return (links, text, settings)

    def postprocess(self, links, text, settings):
        if "filter" in settings:
            links = self.filter_links(settings["filter"].split(","),
                                      links, settings)

        return (links, text, settings)

    def filter_links(self, filters, links, settings):
        filters_gte = [fltr.split(">=") for fltr in filters if ">=" in fltr]
        filters_gt = [fltr.split(">") for fltr in filters \
                      if ">" in fltr and not ">=" in fltr]

        filter_unique = ("unique" in filters) and "context" in settings

        if len(filters_gte) == 0 and len(filters_gt) == 0 \
                                 and not filter_unique:
            return links

        filtered_links = []
        # Q: why do we not apply the gt filter if a gte filter fails?
        for link in links:
            skip = False
            for fltr in filters_gte:
                if not link[fltr[0]] >= float(fltr[1]):
                    skip = True
                    break
            else:
                for fltr in filters_gt:
                    if not link[fltr[0]] > float(fltr[1]):
                        skip = True
                        break

            if filter_unique:
                self.context_links.setdefault(settings["context"], {})
                if link["title"] in self.context_links[settings["context"]]:
                    skip = True

            if not skip:
                filtered_links.append(link)

                if filter_unique:
                    self.context_links[settings["context"]][link["title"]] = link

        print "Filtered %d links to %d" % (len(links), len(filtered_links))
    
        return filtered_links

    def inspect(self):
        return {self.__class__.__name__: self.context_links}