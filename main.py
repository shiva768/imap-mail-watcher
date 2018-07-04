#! /usr/bin/python
# -*- coding: utf-8 -*-

from asyncio import get_event_loop
from logging import DEBUG, Formatter, StreamHandler, getLogger

from imap_mail_watcher import MailWatcher
from mattermost_client import MattermostClient
from setting_manager import SettingManager

""" logger setting """
LOGGER = getLogger('imap-mail-watcher')
LOGGER.setLevel(DEBUG)
handler = StreamHandler()
handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
LOGGER.addHandler(handler)
""" /logger setting """



def main():
    setting = SettingManager()
    loop = get_event_loop()

    def stop():
        loop.stop()

    for user in setting.users:
        loop.run_until_complete(parallel_process(user, setting.common, stop))


async def parallel_process(user, common, stop):
    client = MattermostClient(common['mattermost'], user['mattermost']['token'])
    watcher = MailWatcher(user, client, stop)
    watcher.watch()

if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')

    main()
    LOGGER.info('*** 終了 ***')
