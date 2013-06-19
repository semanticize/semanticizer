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
The Processor wrapping Semanticizer
"""
from processors.core import LinksProcessor
from processors.semanticize import Semanticizer

from nltk.tokenize.punkt import PunktSentenceTokenizer


class SemanticizeProcessor(LinksProcessor):
    """Processor handling the semanticizing"""

    def __init__(self):
        """Set the class variables"""
        self.langcodes = []
        self.semanticizers = {}

    def load_languages(self, langcodes):
        """Save the languages and load the semanticizer"""
        self.langcodes = langcodes
        for langcode in langcodes:
            self.semanticizers[langcode] = Semanticizer(langcode, None)

    def preprocess(self, links, text, settings):
        """
        Semanticize the given text and return the links, text, and
        settings.
        """
        links = []
        if "langcode" in settings and settings["langcode"] in self.semanticizers:
            translations = "translations" in settings
            normalize_dash = not("normalize" in settings and \
                                 not "dash" in settings["normalize"])
            normalize_accents = not("normalize" in settings and \
                                    not "accents" in settings["normalize"])
            normalize_lower = "normalize" in settings and \
                              "lower" in settings["normalize"]

            if "split_sentences" in settings:
                sentences = PunktSentenceTokenizer().tokenize(text)
            else:
                sentences = [text]

            sem = self.semanticizers[settings["langcode"]]
            for sentence in sentences:
                results = sem.semanticize(sentence, counts=True,
                                          normalize_dash=normalize_dash,
                                          normalize_accents=normalize_accents,
                                          normalize_lower=normalize_lower,
                                          translations=translations,
                                          sense_probability_threshold=-1)

                links.extend(results["links"])

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
        return {self.__class__.__name__: self.langcodes}
