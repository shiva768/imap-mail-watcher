import yaml


class SettingManager:

    def __init__(self):
        _settings = self.__file_load()
        self.common = _settings['app']['common']
        self.users = _settings['app']['users']

    def __file_load(self) -> dict:
        with open('setting.yml', encoding='utf-8') as f:
            _settings = yaml.load(f)
        return _settings
