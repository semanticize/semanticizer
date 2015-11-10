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

from nltk.util import ngrams as nltk_ngrams
import re
import urllib

from ..wpm import utils as wpmutil
from ..wpm.data import wpm_dumps

tokenize = re.compile(r'\w+(?:[.,\']\w+)*|[^\w\s]+',
                      re.UNICODE | re.MULTILINE | re.DOTALL).findall


class Semanticizer:
    def __init__(self, language_code, sense_probability_threshold, 
                 max_ngram_length=None, debug=False):
        """constructor"""
        self.language_code = language_code
        self.sense_probability_threshold = sense_probability_threshold
        self.wikipedia_url_template = 'http://%s.wikipedia.org/wiki/%s'
        self.wpm = wpm_dumps[language_code]
        self.title_page = {} # This needs to be removed
        self.max_ngram_length = max_ngram_length
        self.debug = debug

    def semanticize(self, sentence, normalize_dash=True,
                    normalize_accents=True, normalize_lower=False,
                    translations=True, counts=False,
                    largest_matching=False,
                    sense_probability_threshold=None):
        if sense_probability_threshold == None:
            sense_probability_threshold = self.sense_probability_threshold
        result = {"links": []}
        ngrams = set()
        token_lists = [tokenize(sentence),
                       tokenize(sentence.replace('-', ' ')),
                       tokenize(sentence.replace('.', ' ')),
                       tokenize(sentence.replace('.', ''))]

        # get all ngrams for this sentence, limit to max_ngram_length
        # if applicable
        for token_list in token_lists:
            max_len = len(token_list) + 1
            if self.max_ngram_length is not None:
                max_len = min(max_len, self.max_ngram_length)

            for n in range(1, max_len):
                for ngram in nltk_ngrams(token_list, n):
                    ngrams.add(' '.join(ngram))

        normal_ngrams = map(wpmutil.normalize, ngrams)
        exist = self.wpm.normalized_entities_exist(normal_ngrams)

        for i, (ngram, normal_ngram) in enumerate(zip(ngrams, normal_ngrams)):
            if exist[i]:
                normalized_ngram = wpmutil.normalize(ngram, normalize_dash,
                                                     normalize_accents,
                                                     normalize_lower)
                anchors = self.wpm.get_all_entities(normal_ngram)
                for anchor in anchors:
                    normalized_anchor = wpmutil.normalize(anchor, normalize_dash,
                                                          normalize_accents,
                                                          normalize_lower)
                    if normalized_ngram == normalized_anchor:
                        if self.debug and not self.wpm.entity_exists(anchor):
                            raise LookupError("Data corrupted, cannot "
                                              + "find %s in the database" \
                                              % anchor)
                        entity = self.wpm.get_entity_data(anchor)
                        senses = [(sense, self.wpm.get_sense_data(anchor, str(sense))) for sense in entity['senses']]
                        if largest_matching: senses = sorted(senses, key=lambda (_, d): -d['cntlinkdoc'])[:1]
                        for sense, sense_data in senses:
                            if sense_data:
                                if entity['cnttextocc'] == 0:
                                    link_probability = 0
                                    sense_probability = 0
                                else:
                                    link_probability = float(entity['cntlinkdoc']) / entity['cnttextdoc']
                                    sense_probability = float(sense_data['cntlinkdoc']) / entity['cnttextdoc']
                                if sense_probability > sense_probability_threshold:
                                    title = unicode(self.wpm.get_item_title(str(sense)))
                                    url = self.wikipedia_url_template \
                                          % (self.language_code,
                                             urllib.quote(title.encode('utf-8')))
                                    if entity['cntlinkocc'] == 0:
                                        prior_probability = 0
                                    else:
                                        prior_probability = float(sense_data['cntlinkocc']) / entity['cntlinkocc']
                                    link = {
                                        "label": anchor,
                                        "text": ngram,
                                        "title": title,
                                        "id": sense,
                                        "url": url,
                                        "linkProbability": link_probability,
                                        "senseProbability": sense_probability,
                                        "priorProbability": prior_probability
                                    }
                                    if translations:
                                        link["translations"] = {self.language_code:
                                                                {"title": title,
                                                                 "url": url}}
                                        if self.wpm.sense_has_trnsl(str(sense)):
                                            for lang in self.wpm.get_trnsl_langs(str(sense)):
                                                trnsl = self.wpm.get_sense_trnsl(str(sense), lang)
                                                link["translations"][lang] = {
                                                    'title': unicode(trnsl),
                                                    'url': self.wikipedia_url_template % (lang, urllib.quote(unicode(trnsl).encode('utf-8')))
                                                }
                                    if counts:
                                        link["occCount"] = entity['cnttextocc']
                                        link["docCount"] = entity['cnttextdoc']
                                        link["linkOccCount"] = entity['cntlinkocc']
                                        link["linkDocCount"] = entity['cntlinkdoc']
                                        link["senseOccCount"] = int(sense_data['cntlinkocc'])
                                        link["senseDocCount"] = int(sense_data['cntlinkdoc'])
                                        link['fromTitle'] = sense_data['from_title']
                                        link['fromRedirect'] = sense_data['from_redir']
                                    result["links"].append(link)

        if largest_matching:
            available_text = wpmutil.normalize(sentence, normalize_dash, normalize_accents, normalize_lower)
            for link in sorted(result["links"], key=lambda link: -link["priorProbability"]/2-len(link["label"])):
                normalized_label = wpmutil.normalize(link["label"], normalize_dash, normalize_accents, normalize_lower)
                if normalized_label in available_text: 
                    available_text = available_text.replace(normalized_label, "")
                else: result["links"].remove(link)
        return result
