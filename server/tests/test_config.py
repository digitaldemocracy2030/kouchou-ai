import tempfile
from pathlib import Path

from src.config import Environment, Settings, StorageType


class TestSettings(Settings):
    """テスト用の設定クラス"""

    ADMIN_API_KEY: str = "test-admin-api-key"
    PUBLIC_API_KEY: str = "test-public-api-key"
    OPENAI_API_KEY: str = "test-openai-api-key"
    ENVIRONMENT: Environment = "development"

    # テスト用の一時ディレクトリを使用
    BASE_DIR: Path = Path(tempfile.gettempdir()) / "test_shotokutaishi"

    # ストレージ設定
    STORAGE_TYPE: StorageType = "local"
    AZURE_BLOB_STORAGE_ACCOUNT_NAME: str = "testaccount"
    AZURE_BLOB_STORAGE_CONTAINER_NAME: str = "testcontainer"

    class Config:
        env_file = None
