#! /usr/bin/python
# -*- coding: utf-8 -*-

from concurrent.futures import ProcessPoolExecutor
from logging import INFO, DEBUG, Formatter, StreamHandler, FileHandler, getLogger

import sys

from mail_watcher import MailWatcher
from mattermost_client import MattermostClient
from setting_manager import SettingManager

""" logger setting """
LOGGER = getLogger('imap-mail-watcher')
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER.setLevel(INFO)
stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)
# file_handler = FileHandler(filename='/var/log/')
LOGGER.addHandler(stream_handler)
""" /logger setting """


def main():
    args = sys.argv
    setting = SettingManager()
    start_uid = None
    if len(args) > 1:
        start_uid = args[1]

    with ProcessPoolExecutor(len(setting.users)) as executor:
        for i in range(0,2):
            for user in setting.users:
                executor.submit(__parallel_process, user, setting.common, start_uid)


def __parallel_process(user, common, start_uid):
    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], user['distribute'])
    watcher = MailWatcher(user, client, start_uid)
    watcher.watch()


if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')
    try:
        main()
    except:
        LOGGER.warning('*** 異常 ***')
    finally:
        LOGGER.info('*** 終了 ***')
