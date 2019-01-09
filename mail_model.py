class MailModel:

    def __init__(self, uid, date, _from, _to, _cc, _bcc, subject, body, attachments, origin):
        self._uid = uid
        self._date = date
        self._from = _from
        self._to = _to
        self._cc = _cc
        self._bcc = _bcc
        self._subject = subject
        self._body = body
        self._attachments = attachments
        self._origin_from = origin

    def get_property(self, key):
        if key in ['_from', '_to', '_cc', '_bcc']:
            return getattr(self, key)
        return [getattr(self, key)]

    def get_all_property(self):
        return [self.get_property(key) for key in self.excludes_keys()]

    def excludes_keys(self):
        keys = self.__dict__.keys()
        return list(filter(lambda k: k not in ['_uid', '_attachments', '_origin_from'], keys))
