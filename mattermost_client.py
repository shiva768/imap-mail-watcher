from enum import Enum
from logging import getLogger

from mattermostdriver import Driver

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('mattermost')
""" /logger setting """


class MattermostClient:
    def __init__(self, mattermost_setting, token, distribute):
        self.driver = Driver({
            'url': mattermost_setting['url'],
            'token': token,
            'scheme': mattermost_setting['scheme'],
            'port': mattermost_setting['port'],
            'basepath': mattermost_setting['basepath'],
            'timeout': mattermost_setting['timeout']
        })
        self.driver.login()
        self.distribute = distribute

    def post(self, mail):
        channel = self.__distributing(mail)
        LOGGER.info("{}, {}".format(channel, mail))

    def __distributing(self, mail):
        if 'drops' in self.distribute:
            for _filter in self.distribute['drops']:
                if self.__common_distributing(mail, _filter):
                    return 'drops'

        if 'catches' in self.distribute:
            for _filter_set in self.distribute['catches']:
                channel_name = _filter_set['channel_name']
                for _filter in _filter_set['rule']:
                    if self.__common_distributing(mail, _filter):
                        return channel_name

    def __common_distributing(self, mail, _filter):
        pattern = self.Pattern(_filter['pattern']) if 'pattern' in _filter else self.Pattern.MATCH
        conditions = _filter['condition']
        for key in conditions:
            if pattern.match(conditions[key], self.__get_property(mail, key)):
                return True
        return False

    def __get_property(self, mail, name):
        _name = 'mail_' + name if name in ['to', 'from'] else name
        if _name == 'any':
            return list(mail.__dict__.values())
        return [getattr(mail, _name)]

    class Pattern(Enum):
        MATCH = 'match'
        SEARCH = 'search'

        def match(self, condtion: str, values: list):
            if self == self.MATCH:
                return condtion in values
            return [v.find(condtion) for v in values] > 0

    # def api_process(yml):
    #     MATTERMOST_DRIVER.login()
    #     create_channel(yml.get('channels').keys())
    #
    # def create_channel(channels: dict):
    #     LOGGER.info(channels)
    #     exist_channels = MATTERMOST_DRIVER.channels.get_public_channels(TEAM_ID)
    #     for channel in channels:
    #         found = False
    #         for exist_channel in exist_channels:
    #             if exist_channel['name'] == channel:
    #                 found = True
    #         if not found:
    #             ret = MATTERMOST_DRIVER.channels.create_channel(options={
    #                 'team_id': TEAM_ID,
    #                 'name': channel,
    #                 'display_name': channel,
    #                 'type': 'O'
    #             })
    #             LOGGER.info(ret)
    #
    #     MATTERMOST_DRIVER.channels.create_channel()
