class MailModel:

    def __init__(self, uid, date, from_, to_, cc_, bcc_, subject, body, attachments, origin):
        self.uid_ = uid
        self.date_ = date
        self.from_ = from_
        self.to_ = to_
        self.cc_ = cc_
        self.bcc_ = bcc_
        self.subject_ = subject
        self.body_ = body
        self.attachments_ = attachments
        self.origin_from_ = origin

    def get_property(self, key):
        if key in ['from_', 'to_', 'cc_', 'bcc_']:
            return getattr(self, key)
        return [getattr(self, key)]

    def get_all_property(self):
        return [self.get_property(key) for key in self.excludes_keys()]

    def excludes_keys(self):
        keys = self.__dict__.keys()
        return list(filter(lambda k: k not in ['uid_', 'attachments_', 'origin_from_'], keys))
