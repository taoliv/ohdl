import os
from datetime import datetime
from typing import Optional

class ShaCache:
    def __init__(self) -> None:
        self.cache = {}

    @staticmethod
    def path_from_oh_dir(oh_dir: str) -> str:
        return os.path.join(oh_dir, '.sha_cache')

    @staticmethod
    def entry_from_date(since: datetime | None, until: datetime | None) -> str:
        return f'{since} to {until}'

    def load(self, path: str, entry: str) -> None:
        if os.path.exists(path) and os.path.isfile(path):
            self.cache = eval(open(path, 'r').read())
        if entry not in self.cache:
            self.cache[entry] = {}

    def save(self, path: str) -> None:
        open(path, 'w').write(str(self.cache))

    def get(self, entry: str, project: str) -> Optional[str]:
        if project in self.cache[entry]:
            return self.cache[entry][project]['sha']
        else:
            return None

    def add(self, sha: str, entry: str, project_name: str, project_path: str) -> None:
        self.cache[entry][project_name] = {
            'path': project_path,
            'sha': sha
        }
