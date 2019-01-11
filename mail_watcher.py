import imaplib
import re
from logging import getLogger
from queue import Queue

from mail_receiver import PushReceiver
from _parser import MailParser

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('watcher')
""" /logger setting """

UID_REGEX = re.compile(b'UID ([0-9]+)')
SEQ_REGEX = re.compile(b'messages ([0-9]+)')

class MailWatcher:

    def __init__(self, user, mattermost, start_uid):
        self.imap_setting = user['imap']
        seq_no = self.__connect()
        self.mattermost = mattermost
        self.current_uid = self.__fetch_uid(seq_no)
        self.receiver = None
        self.queue = Queue(20)
        if start_uid is not None:
            LOGGER.info("initialize fetch. start uid:{}".format(start_uid))
            self.__initialize_fetch(start_uid)

    def __connect(self):
        self.imap = imaplib.IMAP4_SSL(self.imap_setting['host'])
        self.imap.login(self.imap_setting['user'], self.imap_setting['password'])
        status, seq_no = self.imap.select()
        if status != 'OK':
            raise Exception('response error')
        return seq_no[0]

    def __initialize_fetch(self, start_uid: str):
        status, data = self.imap.uid('fetch', "{}:*".format(start_uid), '(RFC822)')
        LOGGER.debug("initialize fetch status: {}, data: {}".format(status, data))
        if status == 'NO':
            return
        self.__extract(data)
        if self.current_uid != self.__fetch_uid(self.__get_latest_seq_no()):
            self.__initialize_fetch(self.current_uid.decode('utf-8'))

    def __fetch_uid(self, sequence_no):
        status, response = self.imap.fetch(sequence_no, 'uid')
        if status == 'OK':
            uid = self.__extract_uid_by_response(response)
            if uid is not None:
                LOGGER.info("fetched uid: {}".format(uid))
                return uid
        raise Exception('response error')

    @staticmethod
    def __extract_uid_by_response(response):
        for message in response:
            LOGGER.debug("fetched uid message: {}".format(message))
            return MailWatcher.__extract_uid_by_string(message)
        return None

    @staticmethod
    def __extract_uid_by_string(message):
        LOGGER.debug("extract uid message: {}".format(message))
        matcher = UID_REGEX.search(message)
        if matcher is not None:
            return matcher.group(1)
        return None

    def watch(self):
        def callback():
            try:
                LOGGER.debug("current uid:{}".format(self.current_uid))
                status, data = self.imap.uid('fetch', "{}:*".format(self.current_uid.decode('utf-8')), 'BODY.PEEK[]')
                LOGGER.debug("fetch status: {}, data: {}".format(status, data))
                if status == 'NO':
                    return
                self.__extract(data)
            except TimeoutError:
                LOGGER.info('watcher timeout. reconnect')
                self.__reconnect()
                callback()
            except imaplib.IMAP4.abort:
                LOGGER.info('watcher timeout? reconnect')
                self.__reconnect()
                callback()

        self.receiver = PushReceiver(self.imap_setting, callback)
        try:
            self.__watch()
        except KeyboardInterrupt:
            LOGGER.info("interrupt")
            return

    def __extract(self, data):
        for idx, d in enumerate(data):
            if type(d) == bytes:
                uid = MailWatcher.__extract_uid_by_string(d)
                if uid is None or uid == self.current_uid:
                    continue
                self.current_uid = uid
                message = data[idx - 1]
                mail = MailParser(uid, message[1]).mail_parse()
                self.mattermost.post(mail)

    def __watch(self):
        while True:
            self.receiver.listen()

    def __get_latest_seq_no(self):
        status, seq_no = self.imap.status('inbox', 'messages')
        if status == 'OK':
            matcher = SEQ_REGEX.search(seq_no[0])
            if matcher is not None:
                return matcher.group(1)
        raise Exception('response error')

    def __del__(self):
        LOGGER.info("MailWatcher end")
        self.__close()

    def __close(self):
        try:
            self.imap.close()
            self.imap.logout()
        except:
            pass

    def __reconnect(self):
        self.__close()
        self.__connect()
