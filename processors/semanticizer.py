from core import LinksProcessor

from semanticize import Semanticizer
                
class SemanticizeProcessor(LinksProcessor):
    def __init__(self):
        self.languages = {}
        self.semanticizers = {}

    def load_languages(self, languages):
        for lang, langcode, loc in languages:
            self.languages[langcode] = (lang, loc)
            self.semanticizers[langcode] = Semanticizer(langcode, loc)
            
    def preprocess(self, links, text, settings):
        links = []
        if settings.has_key("langcode"): 
            if self.semanticizers.has_key(settings["langcode"]): 
                translations = settings.has_key("translations")
                results = self.semanticizers[settings["langcode"]] \
                            .semanticize(text, counts=True, \
                                         translations=translations, \
                                         senseprobthreshold=-1)
                links = results["links"]
            else:
                links = []
            
        return (links, text, settings)

    def inspect(self):
        return {self.__class__.__name__: self.languages}