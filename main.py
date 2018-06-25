#! /usr/bin/python
# -*- coding: utf-8 -*-

import imaplib
import email
from email.header import decode_header, make_header
from logging import getLogger, StreamHandler, DEBUG, Formatter
from dateutil.parser import parse as date_parse
import yaml
import codecs
from mattermostdriver import Driver
from mattermostdriver.endpoints.channels import Channels

""" mail setting """
DECODE_POSSIBLE_LIST = ['text/plain', 'multipart/alternative']
""" / mail setting """

""" logger setting """
LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)
handler = StreamHandler()
handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
LOGGER.addHandler(handler)
""" /logger setting """

""" imap server setting """
SERVER = "imap.hoge"
USER = "hogesama"
PASSWORD = "hogehoge123"
""" / imap server setting """

""" mattermost server setting """
TEAM_NAME = 'mail'
TEAM_ID = '89rhgujknjdajndm3jgxbrfjqa'
MATTERMOST_DRIVER = Driver({
    'url': '192.168.1.198',
    'token': '3dfot5at5jdn9ft5f481qm8imc',
    'scheme': 'http',
    'port': 80,
    'basepath': '/api/v4',
    'timeout': 30
})

""" / mattermost server setting """


def main():
    try:
        mails = []
        imap = imaplib.IMAP4_SSL(SERVER)
        imap.login(USER, PASSWORD)
        try:
            imap.select()
            typ, data = imap.search(None, 'ON 25-Jun-2018')
            mail_parse(data, imap, mails)
        finally:
            LOGGER.info("finally")
            imap.close()
            imap.logout()
        yml = load_yaml()
        api_process(yml)
    except Exception as ee:
        LOGGER.error("*** error ***")
        LOGGER.error(str(ee))


def mail_parse(data, imap, mails):
    for num in data[0].split():
        typ, data = imap.fetch(num, '(RFC822)')
        email_message = email.message_from_bytes(data[0][1])
        #
        date = date_parse(email_message['Date'])
        mail_from = _decode_header(email_message['From'])
        mail_to = _decode_header(email_message['To'])
        subject = _decode_header(email_message['Subject'])
        body = parse_body(email_message, subject)
        LOGGER.debug("date:{0}".format(date))
        LOGGER.debug("from:{0}".format(mail_from))
        LOGGER.debug("to:{0}".format(mail_to))
        LOGGER.debug("subject:{0}".format(subject))
        LOGGER.debug("body:{0}".format(body))
        mails.append(MailModel(date, mail_from, mail_to, subject, body))


def _decode_header(header):
    return str(make_header(decode_header(header)))


def parse_body(email_message, subject):
    msg_encoding = email_message.get_content_charset()
    if msg_encoding is None:
        msg_encoding = 'utf-8'
    LOGGER.info("{0}:::::{1}".format(email_message.get_content_type(), subject))
    if not email_message.is_multipart():  # シングルパート
        body = single_part(email_message, msg_encoding)
    else:  # マルチパート
        body = multipart(email_message)
    return body


def multipart(email_message):
    for pr in email_message.get_payload():
        msg_encoding = pr.get_content_charset()
        _message_byte = pr.get_payload(decode=True)
        if _message_byte is None:
            continue
        return parse(_message_byte, msg_encoding)


def single_part(email_message, msg_encoding):
    return parse(email_message.get_payload(decode=True), email_message.get_content_charset())


def parse(_byte, encoding):
    return _byte.decode(encoding=encoding, errors='replace')


def load_yaml():
    yml = yaml.load(codecs.open('setting.yml', 'r', 'utf-8'))
    return yml


def api_process(yml):
    MATTERMOST_DRIVER.login()
    create_channel(yml.get('channels').keys())


def create_channel(channels: dict):
    LOGGER.info(channels)
    exist_channels = MATTERMOST_DRIVER.channels.get_public_channels(TEAM_ID)
    for channel in channels:
        found = False
        for exist_channel in exist_channels:
            if exist_channel['name'] == channel:
                found = True
        if not found:
            ret = MATTERMOST_DRIVER.channels.create_channel(options={
                'team_id': TEAM_ID,
                'name': channel,
                'display_name': channel,
                'type': 'O'
            })
            LOGGER.info(ret)

    MATTERMOST_DRIVER.channels.create_channel()


def post():
    pass




class MailModel:
    def __init__(self, date, mail_from, mail_to, subject, body):
        self.date = date
        self.mail_from = mail_from
        self.mail_to = mail_to
        self.subject = subject
        self.body = body


if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')
    main()
    LOGGER.info('*** 終了 ***')
