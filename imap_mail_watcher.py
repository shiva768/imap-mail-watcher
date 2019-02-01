#! /usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from logging import INFO, Formatter, StreamHandler, getLogger
from os import environ

from cache_manager import CacheManager
from mail_fetcher import MailFetcher
from mail_model import MailModel
from mail_watcher import MailWatcher
from mattermost_channel_select import MattermostChannelSelect
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
parser.add_argument('--once', help='single fetch')
parser.add_argument('--dry', help='dry', action='store_true')
parser.add_argument('--start', help='Start fetch from the uid specified in the parameter.')


def main():
    setting = SettingManager()
    args = parser.parse_args()
    if args.dry:
        environ['DRY'] = True
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
    selector = MattermostChannelSelect(user['distribute'])
    if bool(environ.get('DRY')):
        def dummy_post(mail: MailModel):
            selector.select_channel(mail)

        def error_post(text: str):
            LOGGER.error(text)

        __parallel_process_execute(user, start_uid, None, dummy_post, error_post)
        return

    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], selector)
    __parallel_process_execute(user, start_uid, cache, client.post, client.error_post)


def __parallel_process_execute(user, start_uid, cache, store_function, error_function):
    fetcher = MailFetcher(user, {'store': store_function, 'error': error_function}, cache)
    fetcher.initialize_fetch(start_uid)
    watcher = MailWatcher(user['imap'], fetcher.fetch)
    watcher.listen()


def __once(user, common, uid):
    selector = MattermostChannelSelect(user['distribute'])
    if bool(environ.get('DRY')):
        def dummy_post(mail: MailModel):
            selector.select_channel(mail)

        def error_post(text: str):
            LOGGER.error(text)

        __once_execute(user, uid, dummy_post, error_post)
        return
    client = MattermostClient(common['mattermost'], user['name'], user['mattermost'], selector)
    __once_execute(user, uid, client.post, client.error_post)


def __once_execute(user, uid, store_function, error_function):
    fetcher = MailFetcher(user, {'store': store_function, 'error': error_function})
    fetcher.once_fetch(uid)


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
