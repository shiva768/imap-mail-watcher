#! /usr/bin/python
# -*- coding: utf-8 -*-

import codecs
import email
import email.parser
import imaplib
import traceback
from email.header import decode_header, make_header
from logging import DEBUG, Formatter, StreamHandler, getLogger

import yaml
from dateutil.parser import parse as date_parse
from mattermostdriver import Driver

from imap_push_receiver import PushReceiver

""" logger setting """
LOGGER = getLogger('imap-mail-watcher')
LOGGER.setLevel(DEBUG)
handler = StreamHandler()
handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
LOGGER.addHandler(handler)
""" /logger setting """

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
        imap = imaplib.IMAP4_SSL('')
        imap.login('', '')
        try:
            _status, _seq_no = imap.select()
            if _status != 'OK':
                raise Exception('response error')
            global current_uid
            current_uid = fetch_uid(_seq_no[0], imap)

            def callback(seq_no):
                global current_uid
                LOGGER.info("sequence no: {}".format(seq_no))
                _uid = fetch_uid(seq_no, imap)

                if _uid is None or current_uid >= _uid:
                    return
                current_uid = _uid
                status, data = imap.uid('fetch', _uid, '(RFC822)')
                LOGGER.info("fetch status: {}, data: {}".format(status, data))
                if status == 'NO':
                    return
                for idx, d in enumerate(data):
                    if type(d) == bytes and d.startswith(b' UID') and d.find(b'FLAGS') >= 0:
                        message = data[idx - 1]
                        mail_parse(message[1], mails)
                        break

            receiver = PushReceiver(callback)
            while True:
                receiver.listen()

        except KeyboardInterrupt:
            LOGGER.info("interrupt")
            pass
        finally:
            LOGGER.info("main process ending")
            imap.close()
            imap.logout()
        # yml = load_yaml()
        # api_process(yml)
    except Exception as ee:
        LOGGER.error("*** error ***")
        LOGGER.error(traceback.format_exc())


def fetch_uid(sequence_no, imap):
    status, message_list = imap.fetch(sequence_no, 'uid')
    # サーバからメールを削除するとsequence_noがどんどんずれていく問題 -> 接続しなおし？
    if status == 'NO':
        return None
    for message in message_list:
        LOGGER.debug("message: {}".format(message))
        if message.find(b'UID') >= 0:
            _uid = message.split()[2].replace(b')', b'')
            LOGGER.info("fetched uid: {}".format(_uid))
            return _uid
    raise Exception('response error')


def reconnect(imap):
    LOGGER.info('reconnect')
    imap.close()
    imap.logout()
    imap = imaplib.IMAP4_SSL('')
    imap.login('', '')


def mail_parse(data, mails):
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
    mails.append(MailModel(date, mail_from, mail_to, subject, body))


def _decode_header(header):
    return str(make_header(decode_header(header)))


def parse_body(email_message):
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

    # def __init__(self, data):
    #     message = email.message_from_bytes(data)
    #     self.title = _decode_header()
    #     self.date = date
    #     self.mail_from = mail_from
    #     self.mail_to = mail_to
    #     self.subject = subject
    #     self.body = body


if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')
    main()
    LOGGER.info('*** 終了 ***')
