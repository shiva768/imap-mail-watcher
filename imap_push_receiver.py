import imaplib
from logging import getLogger

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('receiver')
""" /logger setting """


class PushReceiver:
    def __init__(self, imap_setting, callback):
        self.imap_setting = imap_setting
        self.callback = callback
        self.__connect()

    def __connect(self):
        self.imap = imaplib.IMAP4_SSL(self.imap_setting['host'])
        self.imap.login(self.imap_setting['user'], self.imap_setting['password'])
        self.imap.select()
        self.imap.send(("{0} IDLE\r\n".format(self.imap._new_tag())).encode('utf-8'))
        line = self.imap.readline()
        if line != b'+ IDLE accepted, awaiting DONE command.\r\n':
            raise Exception('connection error')
        LOGGER.info('ready')

    def __del__(self):
        LOGGER.info('PushReceiver end')
        self.imap.logout()

    def listen(self):
        try:
            line = self.imap.readline()
            strip_line = line.strip()
            LOGGER.info(strip_line)
            if strip_line.endswith(b'EXISTS'):
                self.callback()
            elif strip_line.find(b'BYE') >= 0:
                self.__connect()

        except KeyboardInterrupt as k:
            # self.__del__ # 多分呼ばなくて呼ばれるはず
            raise k
