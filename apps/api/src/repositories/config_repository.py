import json

from src.config import settings
from src.core.exceptions import ConfigFileNotFound, ConfigJSONParseError
from src.schemas.report_config import ReportConfig, ReportConfigUpdate
from src.utils.logger import setup_logger

slogger = setup_logger()


class ConfigRepository:
    def __init__(self, slug: str):
        self.slug = slug
        self.config_path = settings.CONFIG_DIR / f"{slug}.json"

    def read_from_json(self) -> ReportConfig:
        """中間ファイル（CSVファイル）からクラスタのラベル・説明を読み込む"""

        if not self.config_path.exists():
            raise ConfigFileNotFound(f"File not found: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as jsonfile:
                config = json.load(jsonfile)
            return ReportConfig(**config)
        except Exception as e:
            slogger.error(f"Error reading JSON file: {e}")
            raise ConfigJSONParseError(f"Error reading JSON file: {e}") from e

    def update_json(self, updated_config: ReportConfigUpdate) -> bool:
        """中間ファイル（CSVファイル）を更新する"""
        try:
            # 現在のクラスタ情報を読み込む
            current_config = self.read_from_json()
            current_config = current_config.model_dump()

            for key, value in updated_config.model_dump().items():
                if value is not None:
                    current_config[key] = value

            with open(self.config_path, mode="w", encoding="utf-8") as jsonfile:
                json.dump(current_config, jsonfile, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            slogger.error(f"Error writing JSON file: {e}")
            return False
