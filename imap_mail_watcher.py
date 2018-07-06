import imaplib
import re
from logging import getLogger
from queue import Queue

from imap_push_receiver import PushReceiver
from mail_parser import MailParser

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('watcher')
""" /logger setting """

UID_REGEX = re.compile(b'UID ([0-9]+)')


class MailWatcher:

    def __init__(self, user, mattermost, stop):
        self.imap_setting = user['imap']
        self.imap = imaplib.IMAP4_SSL(self.imap_setting['host'])
        self.imap.login(self.imap_setting['user'], self.imap_setting['password'])
        self.mattermost = mattermost
        status, seq_no = self.imap.select()
        if status != 'OK':
            raise Exception('response error')
        self.current_uid = self.__fetch_uid(seq_no[0])
        self.receiver = None
        self.queue = Queue(20)
        self.stop = stop

    def __fetch_uid(self, sequence_no):
        status, response = self.imap.fetch(sequence_no, 'uid')
        if status == 'NO':
            return None
        uid = self.__extract_uid_by_response(response)
        if uid is not None:
            LOGGER.info("fetched uid: {}".format(uid))
            return uid
        raise Exception('response error')

    def __extract_uid_by_response(self, response):
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
            LOGGER.debug("current uid:{}".format(self.current_uid))
            status, data = self.imap.uid('fetch', "{}:*".format(self.current_uid.decode('utf-8')), '(RFC822)')
            LOGGER.debug("fetch status: {}, data: {}".format(status, data))
            if status == 'NO':
                return
            for idx, d in enumerate(data):
                if type(d) == bytes:
                    uid = MailWatcher.__extract_uid_by_string(d)
                    if uid is None or uid == self.current_uid:
                        continue
                    self.current_uid = uid
                    message = data[idx - 1]
                    mail = mail_parse(message[1])
                    self.mattermost.post(mail)

        self.receiver = PushReceiver(self.imap_setting, callback)
        try:
            self.__watch()
        except KeyboardInterrupt:
            LOGGER.info("interrupt")
            self.stop()

    def __watch(self):
        while True:
            self.receiver.listen()

    def __del__(self):
        LOGGER.info("MailWatcher end")
        try:
            self.imap.close()
            self.imap.logout()
        except:
            pass
