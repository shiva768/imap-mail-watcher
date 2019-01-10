#! /usr/bin/python
# -*- coding: utf-8 -*-

from asyncio import get_event_loop
from logging import DEBUG, Formatter, StreamHandler, FileHandler, getLogger

import sys

from mail_watcher import MailWatcher
from mattermost_client import MattermostClient
from setting_manager import SettingManager

""" logger setting """
LOGGER = getLogger('imap-mail-watcher')
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER.setLevel(DEBUG)
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
    loop = get_event_loop()

    def stop():
        loop.stop()

    for user in setting.users:
        loop.run_until_complete(parallel_process(user, setting.common, stop, start_uid))


async def parallel_process(user, common, stop, start_uid):
    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], user['distribute'])
    watcher = MailWatcher(user, client, stop, start_uid)
    watcher.watch()


if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')
    main()
    LOGGER.info('*** 終了 ***')
