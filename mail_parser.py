import email
from email.header import decode_header, make_header
from logging import getLogger

from dateutil.parser import parse as date_parse

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('parser')
""" /logger setting """


def mail_parse(data):
    LOGGER.info(data)
    _mail = email.message_from_bytes(data)

    date = date_parse(_mail['Date'])
    mail_from = _decode_header(_mail['From'])
    mail_to = _decode_header(_mail['To'])
    subject = _decode_header(_mail['Subject'])
    LOGGER.info("{0}:::::{1}".format(_mail.get_content_type(), subject))
    body = parse_body(_mail)
    LOGGER.debug("date:{0}".format(date))
    LOGGER.debug("from:{0}".format(mail_from))
    LOGGER.debug("to:{0}".format(mail_to))
    LOGGER.debug("subject:{0}".format(subject))
    LOGGER.debug("body:{0}".format(body))
    return MailModel(date, mail_from, mail_to, subject, body)


def _decode_header(header):
    return str(make_header(decode_header(header)))


def parse_body(email_message):
    # TODO walkを使ったパースにして、ファイルも取得する
    if not email_message.is_multipart():  # シングルパート
        body = single_parse(email_message)
    else:  # マルチパート
        body = multipart(email_message)
    return body


def multipart(email_message):
    for pr in email_message.get_payload():
        if pr.is_multipart():
            return multipart(pr)
        return single_parse(pr)


def single_parse(email_message):
    msg_encoding = email_message.get_content_charset()
    if msg_encoding is None:
        try:
            return parse(email_message.get_payload(decode=True), 'utf-8', 'strict')
        except UnicodeDecodeError as e:
            LOGGER.warning("parse default encoding utf-8 error:{0}".format(e))
            try:
                return parse(email_message.get_payload(decode=True), 'sjis', 'strict')
            except UnicodeDecodeError as e2:
                LOGGER.error("parse encoding sjis error:{0}".format(e2))
                return "parse error"
    return parse(email_message.get_payload(decode=True), msg_encoding)


def parse(_byte, encoding, error_handle='replace'):
    return _byte.decode(encoding=encoding, errors=error_handle)


class MailModel:

    def __init__(self, date, mail_from, mail_to, subject, body):
        self.date = date
        self.mail_from = mail_from
        self.mail_to = mail_to
        self.subject = subject
        self.body = body
