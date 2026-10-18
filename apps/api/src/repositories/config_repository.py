import json

from src.config import settings
from src.core.exceptions import ConfigFileNotFound, ConfigJSONParseError
from src.schemas.report_config import ReportConfig, ReportConfigUpdate
from src.services.analysis_config import prune_config_for_mode
from src.utils.logger import setup_logger

slogger = setup_logger()


class ConfigRepository:
    def __init__(self, slug: str):
        self.slug = slug
        self.config_path = settings.CONFIG_DIR / f"{slug}.json"

    def read_from_json(self) -> ReportConfig:
        """中間ファイル（CSVファイル）からクラスタのラベル・説明を読み込む"""

        if not self.config_path.exists():
            # Backward compatibility:
            # Some legacy reports may not have configs/<slug>.json but embed config in hierarchical_result.json.
            result_path = settings.REPORT_DIR / self.slug / "hierarchical_result.json"
            if not result_path.exists():
                raise ConfigFileNotFound(f"File not found: {self.config_path}")
            try:
                with open(result_path, encoding="utf-8") as jsonfile:
                    result = json.load(jsonfile)
                embedded_config = result.get("config")
                if not isinstance(embedded_config, dict):
                    raise ConfigJSONParseError(f"Embedded config is missing or invalid: {result_path}")
                return ReportConfig(**embedded_config)
            except ConfigJSONParseError:
                raise
            except Exception as e:
                slogger.error(f"Error reading embedded config from report result: {e}")
                raise ConfigJSONParseError(f"Error reading embedded config from report result: {e}") from e

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
            # 現在の設定を読み込む。configs/<slug>.json がある場合は生の dict をそのまま使い、
            # ReportConfig に定義のないキー（enable_source_link・embedding など）を落とさない。
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as jsonfile:
                    current_config = json.load(jsonfile)
            else:
                # 旧レポート（config が hierarchical_result.json に埋め込まれているもの）
                current_config = self.read_from_json().model_dump()

            for key, value in updated_config.model_dump().items():
                if value is not None:
                    current_config[key] = value

            # ReportConfig.model_dump() は analysis_mode 非該当セクション（hierarchical では
            # llm_grouping:null、旧 report では analysis_mode:null 等）を含めて出力するため、
            # そのまま書き戻すと後続の analysis-core 実行が raw config 検証で落ちる。モードに
            # 属すセクションだけ残して書き戻す。
            current_config = prune_config_for_mode(current_config)

            with open(self.config_path, mode="w", encoding="utf-8") as jsonfile:
                json.dump(current_config, jsonfile, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            slogger.error(f"Error writing JSON file: {e}")
            return False
