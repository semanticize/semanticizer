import redis


class WpmUtil:

    def __init__(self, langcode):
        """
        <langcode>:name = language name
        <langcode>:path = wpminer path
        <langcode>:txt:<text> = set(prob, prob, prob, prob [, senseid...])
        <langcode>:txt:<text>:<senseid> = set(prob, prob, bool, bool)
        <langcode>:norm:<text> = list([text, ...])
        <langcode>:trnsl = set([senseid, ...])
        <langcode>:trnsl:<senseid> = list([langcode, ...])
        <langcode>:trnsl:<senseid>:<langcode> = translated title
        <langcode>:titles:<pageid> = title
        <langcode>:ids:<pagetitle> = id
        """
        self.conn = redis.StrictRedis(host='localhost', port=6379,
                                      db=0, decode_responses=True)
        self.separator = ':'
        self.ns_name = '%s%sname' % (langcode, self.separator)
        self.ns_path = '%s%spath' % (langcode, self.separator)
        self.ns_txt = '%s%stxt' % (langcode, self.separator)
        self.ns_norm = '%s%snorm' % (langcode, self.separator)
        self.ns_trnsl = '%s%strnsl' % (langcode, self.separator)
        self.ns_titles = '%s%stitles' % (langcode, self.separator)
        self.ns_ids = '%s%sids' % (langcode, self.separator)

    def ns_txt_txt(self, txt):
        return self.ns_txt + self.separator + txt

    def ns_txt_txt_sid(self, txt, sid):
        return self.ns_txt + self.separator + txt + self.separator + sid

    def ns_norm_ntxt(self, ntxt):
        return self.ns_norm + self.separator + ntxt

    def ns_trnsl_sid(self, sid):
        return self.ns_trnsl + self.separator + sid

    def ns_trnsl_sid_lang(self, sid, langcode):
        return self.ns_trnsl + self.separator + sid + self.separator + langcode

    def ns_titles_pid(self, pid):
        return self.ns_titles + self.separator + pid

    def ns_ids_title(self, title):
        return self.ns_ids + self.separator + title
