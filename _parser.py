from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from logging import getLogger

from dateutil.parser import parse as date_parse

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('parser')
""" /logger setting """


class MailParser():

    def __init__(self, uid, origin):
        self.content = None
        self.attachments = []
        self.uid = uid
        self.origin = origin

    def mail_parse(self):
        LOGGER.info("__parse: {}".format(self.origin))
        _mail = message_from_bytes(self.origin)  # type: EmailMessage

        date = date_parse(_mail['Date'])
        mail_from = self.__decode_header(_mail['From'])
        mail_to = self.__decode_header(_mail['To'])
        subject = self.__decode_header(_mail['Subject'])
        LOGGER.info("{0}:::::{1}".format(_mail.get_content_type(), subject))
        self.__parse_body(_mail)
        LOGGER.debug("date:{0}".format(date))
        LOGGER.debug("from:{0}".format(mail_from))
        LOGGER.debug("to:{0}".format(mail_to))
        LOGGER.debug("subject:{0}".format(subject))
        LOGGER.debug("body:{0}".format(self.content))
        return self.MailModel(self.uid, date, mail_from, mail_to, subject, self.content, self.attachments)

    @staticmethod
    def __decode_header(header):
        return str(make_header(decode_header(header)))

    def __parse_body(self, email_message: EmailMessage):
        if not email_message.is_multipart():
            self.__parse_body_content(email_message)
        else:
            self.__multipart(email_message)

    def __extract_file(self, email_message: EmailMessage):
        filename = email_message.get_filename()
        self.attachments.append({
            "name": filename,
            "data": email_message.get_payload(decode=True)
        })

    def __multipart(self, email_message: EmailMessage):
        for part in email_message.walk():  # type: EmailMessage
            if part.is_multipart():
                continue
            elif 'Content-Disposition' in part:
                self.__extract_file(part)
                continue
            elif self.content is None:
                self.__parse_body_content(part)

    def __parse_body_content(self, email_message):
        msg_encoding = email_message.get_content_charset()

        if msg_encoding is not None:
            self.content = self.__parse(email_message.get_payload(decode=True), msg_encoding)
            return
        try:
            self.content = self.__parse(email_message.get_payload(decode=True), 'utf-8', 'strict')
        except UnicodeDecodeError as e:
            LOGGER.warning("__parse default encoding utf-8 error:{0}".format(e))
            try:
                self.content = self.__parse(email_message.get_payload(decode=True), 'sjis', 'strict')
            except UnicodeDecodeError as e2:
                LOGGER.error("__parse encoding sjis error:{0}".format(e2))
                self.content = "__parse error"

    def __parse(self, _byte, encoding, error_handle='replace'):
        return _byte.decode(encoding=encoding, errors=error_handle)

    class MailModel:

        def __init__(self, uid, date, mail_from, mail_to, subject, body, attachments):
            self.uid = uid
            self.date = date
            self.mail_from = mail_from
            self.mail_to = mail_to
            self.subject = subject
            self.body = body
            self.attachments = attachments
