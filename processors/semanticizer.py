"""
The Processor wrapping Semanticizer
"""
from processors.core import LinksProcessor
from processors.semanticize import Semanticizer


class SemanticizeProcessor(LinksProcessor):
    """Processor handling the semanticizing"""

    def __init__(self):
        """Set the class variables"""
        self.languages = {}
        self.semanticizers = {}

    def load_languages(self, languages):
        """Save the languages and load the semanticizer"""
        for langcode in languages:
            self.languages[langcode] = (languages[langcode][0],
                                        languages[langcode][1])
            self.semanticizers[langcode] = Semanticizer(langcode,
                                                        languages[langcode][1],
                                                        None)

    def preprocess(self, links, text, settings):
        """Semanticize the given text and return the links, text, and
        settings"""
        links = []
        if "langcode" in settings:
            if settings["langcode"] in self.semanticizers:
                translations = "translations" in settings
                normalize_dash = not("normalize" in settings and \
                                     not "dash" in settings["normalize"])
                normalize_accents = not("normalize" in settings and \
                                        not "accents" in settings["normalize"])
                normalize_lower = "normalize" in settings and \
                                  "lower" in settings["normalize"]
                sense_probability_threshold = settings["sense_probability_threshold"] if "sense_probability_threshold" in settings else "0.0"
                try :
                    sense_probability_threshold = float(sense_probability_threshold)
                except ValueError:
                    sense_probability_threshold = 0.0

                print "sense_probability_threshold:",sense_probability_threshold
                results = self.semanticizers[settings["langcode"]] \
                            .semanticize(text, counts=True,
                                         normalize_dash=normalize_dash,
                                         normalize_accents=normalize_accents,
                                         normalize_lower=normalize_lower,
                                         translations=translations,
                                         sense_probability_threshold=sense_probability_threshold)
                links = results["links"]
            else:
                links = []

        return (links, text, settings)

    def postprocess(self, links, text, settings):
        """
        Remove counts from links
        @todo: why do this here? In Semanticizer.semanticize there's already \
               a check being done on whether counts should be included.
        """
        if not "counts" in settings:
            for link in links:
                for key in link.keys():
                    if key.endswith("Count"):
                        del link[key]

        return (links, text, settings)

    def inspect(self):
        """Return the loaded languages"""
        return {self.__class__.__name__: self.languages}
