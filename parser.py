import re
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from logging import getLogger
from typing import List

from dateutil.parser import parse as date_parse
from html2text import HTML2Text

from mail_model import MailModel

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('parser')
""" /logger setting """
html2text = HTML2Text()
html2text.ignore_links = False


class MailParser:

    def __init__(self, uid, origin):
        self.content = None
        self.attachments = []
        self.uid = uid
        self.origin = origin
        self.converted = False

    def mail_parse(self):
        try:
            return self.__mail_parse()
        except Exception as e:
            LOGGER.error('parse error', e)
            raise e

    def __mail_parse(self):
        _mail = message_from_bytes(self.origin)  # type: EmailMessage
        uid = self.uid.decode('utf-8')
        date_ = date_parse(_mail['Date'])
        origin_from_ = self.__decode_header(_mail, 'From')
        from_ = self.__decode_header_addresses(_mail, 'From')
        to_ = self.__decode_header_addresses(_mail, 'To')
        cc_ = self.__decode_header_addresses(_mail, 'Cc')
        bcc_ = self.__decode_header_addresses(_mail, 'Bcc')
        subject_ = self.__decode_header(_mail, 'Subject', uid)
        LOGGER.info("{0}::{1}::{2}".format(uid, subject_, _mail.get_content_type()))
        self.__parse_body(_mail)
        LOGGER.debug("date:{0}".format(date_))
        LOGGER.debug("from:{0}".format(from_))
        LOGGER.debug("to:{0}".format(to_))
        LOGGER.debug("cc:{0}".format(cc_))
        LOGGER.debug("bcc:{0}".format(bcc_))
        LOGGER.debug("subject:{0}".format(subject_))
        LOGGER.debug("body:{0}".format(self.content))
        LOGGER.debug("attachments: {}".format(', '.join([attachment['name'] for attachment in self.attachments])))
        if self.converted:
            subject_ += ' \n(converted)'
        return MailModel(uid, date_, from_, to_, cc_, bcc_, subject_, self.content, self.attachments, origin_from_)

    @staticmethod
    def __decode_header(mail, target, uid=None):
        header = mail[target]
        try:
            return str(make_header(decode_header(header)))
        except UnicodeDecodeError:
            decoded = decode_header(header)
            try:
                return "{} decode error {}".format(target, decoded[1][0].decode('utf-8'))
            except:
                return "{} decode error {}".format(target, uid)

    @staticmethod
    def __decode_header_addresses(mail, target) -> List[str]:
        header = mail[target]
        return re.findall('<([^<>]+)>', MailParser.__decode_header(mail, target)) if header is not None else ['']

    def __parse_body(self, email_message: EmailMessage):
        if not email_message.is_multipart():
            self.__parse_body_content(email_message)
        else:
            self.__multipart(email_message)

    def __extract_file(self, email_message: EmailMessage):
        filename_header = make_header(decode_header(email_message.get_filename()))
        filename = filename_header._chunks[0][0] if len(filename_header._chunks[0]) > 0 and len(filename_header._chunks[0][0]) > 0 else email_message.get_filename() + '(decode failed)'
        self.attachments.append({
            "name": filename,
            "data": email_message.get_payload(decode=True)
        })

    def __multipart(self, email_message: EmailMessage):
        for part in email_message.walk():  # type: EmailMessage
            if part.is_multipart():
                continue
            elif 'Content-Disposition' in part and part['Content-Disposition'] != 'inline':
                self.__extract_file(part)
                continue
            elif self.content is None:
                self.__parse_body_content(part)

    def __parse_body_content(self, email_message):
        msg_encoding = email_message.get_content_charset()

        if msg_encoding is not None:
            self.content = self.__parse(email_message.get_payload(decode=True), msg_encoding)
            if email_message['Content-Type'].split(';')[0].find('text/html') >= 0:
                self.content = html2text.handle(self.content)
                self.converted = True
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
