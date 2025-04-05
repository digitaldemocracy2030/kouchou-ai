import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

Environment = Literal["development", "production"]
StorageType = Literal["local", "azure_blob"]


class Settings(BaseSettings):
    ADMIN_API_KEY: str = Field(env="ADMIN_API_KEY")
    PUBLIC_API_KEY: str = Field(env="PUBLIC_API_KEY")
    OPENAI_API_KEY: str = Field(env="OPENAI_API_KEY")
    ENVIRONMENT: Environment = Field(env="ENVIRONMENT", default="production")
    BASE_DIR: Path = Path(__file__).parent.parent
    TOOL_DIR: Path = BASE_DIR / "broadlistening"
    REPORT_DIR: Path = TOOL_DIR / "pipeline" / "outputs"
    CONFIG_DIR: Path = TOOL_DIR / "pipeline" / "configs"
    INPUT_DIR: Path = TOOL_DIR / "pipeline" / "inputs"
    DATA_DIR: Path = BASE_DIR / "data"

    # ストレージ設定
    STORAGE_TYPE: StorageType = Field(env="STORAGE_TYPE", default="local")
    AZURE_BLOB_STORAGE_ACCOUNT_NAME: str | None = Field(env="AZURE_BLOB_STORAGE_ACCOUNT_NAME", default=None)
    AZURE_BLOB_STORAGE_CONTAINER_NAME: str | None = Field(env="AZURE_BLOB_STORAGE_CONTAINER_NAME", default=None)

    @property
    def azure_blob_storage_account_url(self) -> str:
        return f"https://{self.AZURE_BLOB_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

    class Config:
        env_file = ".env"


settings = Settings()
# レポート出力ツール側でOpenAI APIを利用できるように、環境変数にセットする
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
