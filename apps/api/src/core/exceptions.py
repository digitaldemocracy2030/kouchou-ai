class ClusterRepoError(Exception):
    """ClusterRepository の基底例外"""


class ClusterFileNotFound(ClusterRepoError):
    """クラスタのCSVファイルが存在しないケース"""


class ClusterCSVParseError(ClusterRepoError):
    """クラスタのCSVファイルのパースに失敗したケース"""


class ConfigRepoError(Exception):
    """ConfigRepository の基底例外"""


class ConfigFileNotFound(ConfigRepoError):
    """設定ファイルが存在しないケース"""


class ConfigJSONParseError(ConfigRepoError):
    """設定ファイルのパースに失敗したケース"""
