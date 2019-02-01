import imaplib
import re
from logging import getLogger, Logger

from cache_manager import CacheManager
from parser import MailParser

""" logger setting """
LOGGER: Logger = getLogger('imap-mail-watcher').getChild('fetcher')
""" /logger setting """

UID_REGEX = re.compile(b'UID ([0-9]+)')
SEQ_REGEX = re.compile(b'messages ([0-9]+)')
LOGIN_FAILED_LIMIT = 5


class MailFetcher:

    def __init__(self, user, store_functions: dict, cache: CacheManager = None):
        self.imap_setting = user['imap']
        self.username = user['name']
        self.store_functions = store_functions
        seq_no = self.__connect()
        self.current_uid = self.__fetch_uid(seq_no)
        self.receiver = None
        self.cache = cache
        self.login_failed_count = 0

    def initialize_fetch(self, start_uid):
        if start_uid is not None:
            LOGGER.info("initialize fetch. start uid:{}".format(start_uid))
            self.__initialize_fetch(start_uid)
        elif self.cache is not None and self.cache.get(self.username) is not None:
            cache_uid = int(self.cache.get(self.username)) + 1
            LOGGER.info("cached uid. fetch. start uid:{}".format(cache_uid))
            self.__initialize_fetch(str(cache_uid))

    def once_fetch(self, uid):
        status, data = self.imap.uid('fetch', "{}".format(uid), '(RFC822)')
        LOGGER.info("once fetch status: {}, data: {}".format(status, data))
        if status == 'NO':
            return
        self.__extract(data)

    def __connect(self):
        self.imap = imaplib.IMAP4_SSL(self.imap_setting['host'])
        self.__login()
        status, seq_no = self.imap.select()
        if status != 'OK':
            raise Exception('response error')
        return seq_no[0]

    def __login(self):
        try:
            self.imap.login(self.imap_setting['user'], self.imap_setting['password'])
            self.login_failed_count = 0
        except Exception as e:
            self.login_failed_count += 1
            LOGGER.error('login failed. and retry.', error=e, count=self.login_failed_count)
            if self.login_failed_count <= LOGIN_FAILED_LIMIT:
                self.__login()
                return
            self.store_functions['error']('login failed limit')
            raise e

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
            return MailFetcher.__extract_uid_by_string(message)
        return None

    @staticmethod
    def __extract_uid_by_string(message):
        LOGGER.debug("extract uid message: {}".format(message))
        matcher = UID_REGEX.search(message)
        if matcher is not None:
            return matcher.group(1)
        return None

    def fetch(self):
        try:
            LOGGER.info("current uid:{}".format(self.current_uid))
            status, data = self.imap.uid('fetch', "{}:*".format(self.current_uid.decode('utf-8')), 'BODY.PEEK[]')
            LOGGER.debug("fetch status: {}, data: {}".format(status, data))
            if status == 'NO':
                return
            self.__extract(data)
        except TimeoutError:
            LOGGER.info('fetcher timeout. reconnect')
            self.__reconnect()
            self.fetch()
        except ConnectionResetError:
            LOGGER.info('fetcher connection reset. reconnect')
            self.__reconnect()
            self.fetch()
        except imaplib.IMAP4.abort:
            LOGGER.info('fetcher timeout? reconnect')
            self.__reconnect()
            self.fetch()

    def __extract(self, data):
        for idx, d in enumerate(data):
            if type(d) == bytes:
                uid = MailFetcher.__extract_uid_by_string(d)
                if uid is None or uid == self.current_uid:
                    continue
                self.current_uid = uid
                message = data[idx - 1]
                mail = MailParser(uid, message[1]).mail_parse()
                self.store_functions['store'](mail)
                if self.cache is not None:
                    self.cache.write_cache(self.username, self.current_uid)

    def __get_latest_seq_no(self):
        status, seq_no = self.imap.status('inbox', 'messages')
        if status == 'OK':
            matcher = SEQ_REGEX.search(seq_no[0])
            if matcher is not None:
                return matcher.group(1)
        raise Exception('response error')

    def __del__(self):
        LOGGER.info("MailFetcher end")
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
