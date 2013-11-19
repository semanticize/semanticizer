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

import abc


class Data(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def entity_exists(self, entity):
        return

    @abc.abstractmethod
    def normalized_entities_exist(self, normalized_entities):
        return

    @abc.abstractmethod
    def get_all_entities(self, normalized_entity):
        return

    @abc.abstractmethod
    def get_entity_data(self, entity):
        return

    @abc.abstractmethod
    def get_sense_data(self, entity, sense):
        return

    @abc.abstractmethod
    def get_sense_title(self, sid):
        return

    @abc.abstractmethod
    def get_title_id(self, title):
        return

    @abc.abstractmethod
    def sense_has_trnsl(self, sid):
        return

    @abc.abstractmethod
    def get_trnsl_langs(self, sid):
        return

    @abc.abstractmethod
    def get_sense_trnsl(self, sid, lang):
        return

    @abc.abstractmethod
    def get_wikipedia_name(self):
        return

    @abc.abstractmethod
    def get_data_path(self):
        return

    @abc.abstractmethod
    def get_lang_name(self):
        return

    @abc.abstractmethod
    def get_title_ngram_score(self, title):
        return
