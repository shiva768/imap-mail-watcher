from enum import Enum
from logging import getLogger

from mail_model import MailModel

""" logger setting """
LOGGER = getLogger('imap-mail-watcher').getChild('channel_select')
""" /logger setting """


class MattermostChannelSelect:

    def __init__(self, distributes: dict):
        self.distributes = distributes

    def select_channel(self, mail: MailModel):
        channel_name = self.__select(mail)
        LOGGER.info("{}::{}::{}".format(mail.uid_, channel_name, mail.subject_))
        return channel_name

    def __select(self, mail):
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

    def __match(self, mail, rule):
        if type(rule['conditions']) is list:
            return all([ConditionSet(condition_set).match(mail) for condition_set in rule['conditions']])
        return ConditionSet(rule['conditions']).match(mail)


class ConditionSet:
    def __init__(self, condition_set_):
        self.pattern = Pattern(condition_set_['pattern']) if 'pattern' in condition_set_ else Pattern.MATCH
        self.targets = self.filter_dict(lambda k, v: k != 'pattern', condition_set_)
        self.match_case = condition_set_['case'] if 'case' in condition_set_ else False

    def match(self, mail):
        return all([
            self.pattern.match(self.targets[key].lower(), self.__lower_convert(self.__get_property(mail, key)))
            for key in self.targets
        ])

    def __lower_convert(self, values: list):
        if not self.match_case:
            return list(map(lambda v: str(v).lower() if v is not None else v, values))
        return values

    def __get_property(self, mail, name):
        if name == 'any':
            return mail.get_all_property()
        return [mail.get_property(name + '_')]

    def filter_dict(self, f, d):
        return {k: v for k, v in d.items() if f(k, v)}


class Pattern(Enum):
    MATCH = 'match'
    SEARCH = 'search'

    def match(self, condition: str, values: list):
        if self == self.MATCH:
            return condition in values
        return any([condition in str(v) for v in values])
