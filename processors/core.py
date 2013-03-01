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
    def __init__(self):
        self.settings = {
            "vara": {
                "pre_filter": "unique,sense_probability>0.01",
                "learning": "coling-SP0.2-100.RandomForestClassifier-10-auto.pkl",
                "filter": "unique,learning_probability>=0.5"
            }}
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
        if settings.has_key("filter"):
            links = self.filter_links(settings["filter"].split(","), links, settings)

        return (links, text, settings)
    
    def filter_links(self, filters, links, settings):
        filters_gte = [filter.split(">=") for filter in filters if ">=" in filter]
        filters_gt = [filter.split(">") for filter in filters \
                      if ">" in filter and not ">=" in filter]
    
        filter_unique = ("unique" in filters) and settings.has_key("context")
    
        if len(filters_gte) == 0 and len(filters_gt) == 0 and not filter_unique: 
           return links
    
        filtered_links = []
        for link in links:
            skip = False
            for filter in filters_gte:
                if not link[filter[0]] >= float(filter[1]):
                    skip = True
                    break
            else:
                for filter in filters_gt:
                    if not link[filter[0]] > float(filter[1]):
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