#! /usr/bin/python
# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor
from logging import INFO, DEBUG, Formatter, StreamHandler, FileHandler, getLogger
from argparse import ArgumentParser

import sys

from cache_manager import CacheManager
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

parser = ArgumentParser()
parser.add_argument('--once', help='debug')
parser.add_argument('--start', help='Start fetch from the uid specified in the parameter.')


def main():
    setting = SettingManager()
    args = parser.parse_args()
    if args.once:
        __once(setting.users[0], setting.common, args.once)
        return
    cache = CacheManager()
    user_count = len(setting.users)
    if user_count > 1:
        with ThreadPoolExecutor(user_count) as executor:
            futures = []
            try:
                for user in setting.users:
                    futures.append(executor.submit(__parallel_process, user, setting.common, args.start, cache))
                executor.shutdown()
            except KeyboardInterrupt:
                LOGGER.warning('shutdown')
    else:
        __parallel_process(setting.users[0], setting.common, args.start, cache)


def __parallel_process(user, common, start_uid, cache):
    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], user['distribute'])
    MailWatcher.watcher(user, client, start_uid, cache)


def __once(user, common, uid):
    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], user['distribute'])
    MailWatcher.once(user, client, uid)


if __name__ == '__main__':
    LOGGER.info('*** 開始 ***')
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        LOGGER.warning("*** 異常 ***: {}".format(e))
    finally:
        LOGGER.info('*** 終了 ***')
