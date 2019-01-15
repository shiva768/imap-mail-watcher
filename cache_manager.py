from threading import Lock

import yaml


class CacheManager:
    def __init__(self):
        self.cache = {}
        self.__load_cache()
        self._lock = Lock()

    def write_cache(self, username, uid) -> None:
        self._lock.acquire()
        self.cache[username] = uid.decode('utf-8')
        with open('.cache', 'w') as f:
            f.write(yaml.dump(self.cache))
            f.flush()
        self._lock.release()

    def __load_cache(self):
        from os.path import exists
        if not exists('.cache'):
            return
        with open('.cache', 'r+', encoding='utf-8') as f:
            tmp = yaml.load(f)
            if tmp is not None:
                self.cache = tmp

    def get(self, username):
        return self.cache.get(username)
