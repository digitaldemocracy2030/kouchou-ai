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
    GEMINI_API_KEY: str | None = Field(env="GEMINI_API_KEY", default=None)
    ENVIRONMENT: Environment = Field(env="ENVIRONMENT", default="production")

    # Next.jsのrevalidate API用の設定
    NEXT_PUBLIC_SITE_URL: str = Field(env="NEXT_PUBLIC_SITE_URL", default="http://localhost:3000")
    REVALIDATE_SECRET: str = Field(env="REVALIDATE_SECRET", default="revalidate-secret")
    REVALIDATE_URL: str = Field(env="REVALIDATE_URL", default="http://client:3000/api/revalidate")
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
        env_file_encoding = "utf-8"
        extra = "ignore"


env_file = os.environ.get("ENV_FILE", ".env")
settings = Settings(_env_file=env_file)
# レポート出力ツール側でOpenAI APIを利用できるように、環境変数にセットする
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
