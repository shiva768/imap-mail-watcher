from enum import Enum
from textwrap import dedent
from logging import getLogger

from mattermostdriver import Driver
from mattermostdriver.exceptions import ResourceNotFound

from mail_model import MailModel

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('mattermost')
""" /logger setting """
EXCLUDE_MAIL_PROPERTY = ['_uid', '_date', '_attachments']
MATTERMOST_POST_LIMIT_LENGTH = 16383


class MattermostClient:
    def __init__(self, mattermost_setting, username, mattermost_user_setting, distributes):
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
        self.distributes = distributes
        self.team_id = self.driver.teams.get_team_by_name(team_name)['id']

    def post(self, mail):
        try:
            channel_name = self.__distributing(mail)
            LOGGER.info("{}, {}".format(channel_name, mail))
            self.__api_process(channel_name, mail)
        except Exception as e:
            LOGGER.error(e)
            try:
                self.__simple_post(mail, 'error', e)
            except Exception as e2:
                LOGGER.error(e2)

    def __distributing(self, mail):
        if 'drops' in self.distributes:
            for _filter_set in self.distributes['drops']:
                result = self.__common_distributing(mail, _filter_set, 'drops')
                if result is not None:
                    LOGGER.debug("match rule {}".format(_filter_set))
                    return result

        if 'catches' in self.distributes:
            for _filter_set in self.distributes['catches']:
                channel_name = _filter_set['channel_name']
                result = self.__common_distributing(mail, _filter_set, channel_name)
                if result is not None:
                    LOGGER.debug("match rule {}".format(_filter_set))
                    return result
        return 'general'

    def __common_distributing(self, mail, _filter_set, channel_name):
        if 'rule' in _filter_set:
            for _rule in _filter_set['rule']:
                if self.__match(mail, _rule):
                    return channel_name
        elif self.__match(mail, _filter_set):
            return channel_name

    def __match(self, mail, _rule):
        pattern = self.Pattern(_rule['pattern']) if 'pattern' in _rule else self.Pattern.MATCH
        conditions = _rule['condition']
        if all([pattern.match(conditions[key], self.__get_property(mail, key)) for key in conditions]):
            return True
        return False

    def __get_property(self, mail, name):
        if name == 'any':
            return mail.get_all_property()
        return [mail.get_property('_' + name)]

    class Pattern(Enum):
        MATCH = 'match'
        SEARCH = 'search'

        def match(self, condition: str, values: list):
            if self == self.MATCH:
                return condition in values
            return any([condition in str(v) for v in values])

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
        self.__execute_post(channel_id, file_ids, message)

    def __execute_post(self, channel_id, file_ids, message):
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
        '''.format(mail._origin_from, mail._date, mail._subject.strip(), mail._uid)).strip() + '\n' + dedent(mail._body)

    def __check_if_upload_file(self, channel_id, mail: MailModel):
        if len(mail._attachments) <= 0:
            return []
        file_ids = []
        for attachment in mail._attachments:
            file_ids.append(self.__upload_file(channel_id, attachment['name'], attachment['data']))
        return file_ids

    def __upload_file(self, channel_id, name, data):
        return self.driver.files.upload_file(channel_id, {'files': (name, data)})['file_infos'][0]['id']

    def __simple_post(self, mail, channel_name, error=None):
        channel_id = self.__get_channel_id_if_create_channel(channel_name)
        message = dedent('''
                ```
                from: {}
                date: {}
                subject: {}
                uid: {}
                ```
                '''.format(mail._origin_from, mail._date, mail._subject.strip(), mail._uid)).strip()
        if error is not None:
            message += '\n' + dedent(error)
        self.__execute_post(channel_id, [], message)
