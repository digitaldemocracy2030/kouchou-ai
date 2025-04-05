import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# テスト実行時にsrcディレクトリをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_config import TestSettings


@pytest.fixture
def test_settings():
    """テスト用の設定を提供するフィクスチャ"""
    settings = TestSettings()
    # 必要なディレクトリを作成
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    settings.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    settings.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture(autouse=True)
def use_test_settings():
    """すべてのテストでテスト用の設定を使用するフィクスチャ"""
    with patch("src.config.settings", TestSettings()):
        yield
