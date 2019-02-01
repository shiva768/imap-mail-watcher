from enum import Enum
from logging import getLogger
from os import environ
from textwrap import dedent

from mattermostdriver import Driver
from mattermostdriver.exceptions import ResourceNotFound

from channel_select import ChannelSelect
from mail_model import MailModel

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('mattermost')
""" /logger setting """
MATTERMOST_POST_LIMIT_LENGTH = 16383


class MattermostClient:

    def __init__(self, mattermost_setting, username, mattermost_user_setting, selector: ChannelSelect, once=False):
        self.driver = Driver({
            'url': mattermost_setting['url'],
            'token': mattermost_user_setting['token'],
            'scheme': mattermost_setting['scheme'],
            'port': mattermost_setting['port'],
            'basepath': mattermost_setting['basepath'],
            'timeout': mattermost_setting['timeout']
        })
        self.username = username
        team_name = mattermost_user_setting['team_name']
        self.driver.login()
        self.selector = selector
        self.team_id = self.driver.teams.get_team_by_name(team_name)['id']
        self.once = once

    def post(self, mail):
        try:
            channel_name = self.selector.select_channel(mail)
            if not bool(environ.get('DEBUG')) and not self.once:
                self.__api_process(channel_name, mail)
        except Exception as e:
            LOGGER.error(e)
            try:
                self.__simple_post(mail, 'error', e)
            except Exception as e2:
                LOGGER.error(e2)

    def error_post(self, text):
        self.__simple_post(None, 'error', text)

    def __api_process(self, channel_name, mail):
        if channel_name == 'drops':
            self.__simple_post(mail, 'drops')
            return
        channel_id = self.__get_channel_id_if_create_channel(channel_name)
        file_ids = self.__check_if_upload_file(channel_id, mail)
        self.__create_message(channel_id, mail, file_ids)

    def __get_channel_id_if_create_channel(self, channel_name):
        try:
            channel = self.driver.channels.get_channel_by_name(self.team_id, channel_name)
            return channel['id']
        except ResourceNotFound:
            LOGGER.info('channel does not exist and create channel')
            user_id = self.driver.users.get_user_by_username(self.username)['id']
            channel = self.driver.channels.create_channel(options={
                'team_id': self.team_id,
                'name': channel_name,
                'display_name': channel_name,
                'type': 'O'
            })
            channel_id = channel['id']
            self.driver.channels.add_user(channel_id, options={
                'user_id': user_id
            })
            return channel_id

    def __create_message(self, channel_id, mail, file_ids):
        message = self.__format_message(mail)
        if len(message) >= MATTERMOST_POST_LIMIT_LENGTH:
            file_ids.append(self.__upload_file(channel_id, 'full_body.txt', message.encode('utf-8')))
            message = message[:MATTERMOST_POST_LIMIT_LENGTH]
        self.__execute_post(channel_id, message, file_ids)

    def __execute_post(self, channel_id, message, file_ids=[]):
        self.driver.posts.create_post(options={
            'channel_id': channel_id,
            'message': message,
            'file_ids': file_ids
        })

    def __format_message(self, mail):
        return dedent('''
        ```
        from: {}
        date: {}
        subject: {}
        uid: {}
        ```
        '''.format(mail.origin_from_, mail.date_, mail.subject_.strip(), mail.uid_)).strip() + '\n' + dedent(mail.body_)

    def __check_if_upload_file(self, channel_id, mail: MailModel):
        if len(mail.attachments_) <= 0:
            return []
        file_ids = []
        for attachment in mail.attachments_:
            file_ids.append(self.__upload_file(channel_id, attachment['name'], attachment['data']))
        return file_ids

    def __upload_file(self, channel_id, name, data):
        return self.driver.files.upload_file(channel_id, {'files': (name, data)})['file_infos'][0]['id']

    def __simple_post(self, mail, channel_name, error=None, plain_text=None):
        channel_id = self.__get_channel_id_if_create_channel(channel_name)
        if mail is None:
            self.__execute_post(channel_id, plain_text)
            return
        message = dedent('''
                ```
                from: {}
                date: {}
                subject: {}
                uid: {}
                ```
                '''.format(mail.origin_from_, mail.date_, mail.subject_.strip(), mail.uid_)).strip()
        if error is not None:
            message += '\n' + dedent(error)
        self.__execute_post(channel_id, message)



