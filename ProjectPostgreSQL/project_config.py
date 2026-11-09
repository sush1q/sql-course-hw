# Загрузка настроек проекта (в данном случае только настроек соединения с БД)
# из файла config.yaml.
import re

import yaml

class ProjectConfig:
    """Класс считывает базовые настройки из файла config.yaml"""

    def __init__(self):
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
            self.dbname = config['dbname']
            self.user = config['user']
            self.password = config['password']
            self.host = config['host']
            prefix = config['dbtableprefix']

        identifier = r"[A-Za-z_][A-Za-z0-9_$]*"
        if not isinstance(prefix, str) or not re.fullmatch(rf"(?:{identifier}\.)?(?:{identifier})?", prefix):
            raise ValueError("Некорректный dbtableprefix в config.yaml. Примеры: public., variant18., tbl_.")
        self.dbtableprefix = prefix

# Этот метод запускается только, если запускать
# данный файл, а не подключать его.
if __name__ == "__main__":
    x = ProjectConfig()
    print(x.dbfilepath)
