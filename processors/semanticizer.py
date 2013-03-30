from core import LinksProcessor

from semanticize import Semanticizer
                
class SemanticizeProcessor(LinksProcessor):
    def __init__(self):
        self.languages = {}
        self.semanticizers = {}

    def load_languages(self, languages):
        for langcode in languages:
            self.languages[langcode] = (languages[langcode][0], languages[langcode][1])
            self.semanticizers[langcode] = Semanticizer(languages[langcode][0], languages[langcode][1])
            
    def preprocess(self, links, text, settings):
        links = []
        if settings.has_key("langcode"): 
            if self.semanticizers.has_key(settings["langcode"]): 
                translations = settings.has_key("translations")
                normalize_dash = not("normalize" in settings and not "dash" in settings["normalize"])
                normalize_accents = not("normalize" in settings and not "accents" in settings["normalize"])
                normalize_lower = "normalize" in settings and "lower" in settings["normalize"]
                results = self.semanticizers[settings["langcode"]] \
                            .semanticize(text, counts=True, \
                                         normalize_dash=normalize_dash, \
                                         normalize_accents=normalize_accents, \
                                         normalize_lower=normalize_lower, \
                                         translations=translations, \
                                         sense_probability_threshold=-1)
                links = results["links"]
            else:
                links = []
            
        return (links, text, settings)
        
    def postprocess(self, links, text, settings):
        if not "counts" in settings:
            for link in links:
                for key in link.keys():
                    if key.endswith("Count"):
                        del link[key]

        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.languages}