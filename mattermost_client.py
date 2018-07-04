from logging import getLogger

from mattermostdriver import Driver

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('mattermost')
""" /logger setting """


class MattermostClient:
    def __init__(self, mattermost_setting, token):
        self.driver = Driver({
            'url': mattermost_setting['url'],
            'token': token,
            'scheme': mattermost_setting['scheme'],
            'port': mattermost_setting['port'],
            'basepath': mattermost_setting['basepath'],
            'timeout': mattermost_setting['timeout']
        })

    def post(self, mail):
        LOGGER.info(mail)

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
