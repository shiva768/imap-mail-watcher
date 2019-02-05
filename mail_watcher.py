import imaplib
import socket
from logging import getLogger
from types import FunctionType


""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('watcher')
""" /logger setting """


class MailWatcher:
    def __init__(self, imap_setting, fetch_function: FunctionType):
        self.imap_setting = imap_setting
        self.fetch_function = fetch_function
        self.__connect()
        self.connect_try_count = 0

    def __connect(self):
        LOGGER.debug('connecting')
        self.imap = imaplib.IMAP4_SSL(self.imap_setting['host'])
        self.imap.login(self.imap_setting['user'], self.imap_setting['password'])
        self.imap.select()
        self.imap.send(("{0} IDLE\r\n".format(self.imap._new_tag())).encode('utf-8'))
        line = self.imap.readline()
        if line != b'+ IDLE accepted, awaiting DONE command.\r\n':
            raise Exception('connection error')
        LOGGER.info('ready')

    def __del__(self):
        LOGGER.info('MailWatcher end')
        self.__close()

    def listen(self):
        while True:
            try:
                self.__listen()
                self.connect_try_count = 0
            except socket.error as e:
                self.connect_try_count += 1
                import time
                if self.connect_try_count <= 10:
                    time.sleep(60)
                else:
                    raise e


    def __listen(self):
        try:
            line = self.imap.readline()
            strip_line = line.strip()
            LOGGER.debug(strip_line)
            if strip_line.endswith(b'EXISTS'):
                self.fetch_function()
            elif strip_line.find(b'BYE') >= 0:
                LOGGER.info('reconnect')
                self.__reconnect()
        except TimeoutError:
            LOGGER.info('watcher timeout. reconnect')
            self.__reconnect()
        except ConnectionResetError:
            LOGGER.info('watcher connection reset. reconnect')
            self.__reconnect()
        # except KeyboardInterrupt as k:
        #     # self.__del__ # 多分呼ばなくて呼ばれるはず
        #     raise k

    def __close(self):
        LOGGER.debug('close connection')
        try:
            self.imap.close()
            self.imap.logout()
        except:
            pass

    def __reconnect(self):
        self.__close()
        self.__connect()
