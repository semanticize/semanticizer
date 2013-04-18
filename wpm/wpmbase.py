import abc


class WpmData(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def entity_exists(self, entity):
        return

    @abc.abstractmethod
    def normalized_entity_exists(self, normalized_entity):
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
