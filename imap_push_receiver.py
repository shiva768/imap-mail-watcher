import imaplib
from logging import getLogger

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('receiver')
""" /logger setting """


class PushReceiver:
    def __init__(self, callback):
        self.callback = callback
        self.__connect()

    def __connect(self):
        self.imap = imaplib.IMAP4_SSL('exchange1.hoge.co.jp')
        self.imap.login('hoge@hoge.co.jp', 'hoge123')
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
                seq_no = strip_line.split(b' ')[1].decode()
                LOGGER.info("message id: {}".format(seq_no))
                self.callback(seq_no)
            elif strip_line.find(b'BYE') >= 0:
                self.__connect()
            else:
                if strip_line.endswith(b'RECENT'):
                    LOGGER.info("RECENT: {}".format(strip_line.split(b' ')[1].decode()))

        except KeyboardInterrupt as k:
            self.__del__
            raise k
