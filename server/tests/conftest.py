import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
def use_test_settings(test_settings):
    """テスト実行時に設定をTestSettingsで置き換えるフィクスチャ"""
    with patch("src.config.settings", test_settings):
        with patch("src.routers.report.settings", test_settings):
            yield test_settings


@pytest.fixture
def temp_report_dir():
    """テスト用の一時レポートディレクトリを提供するフィクスチャ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def client(test_settings):
    """テスト用のFastAPIクライアントを提供するフィクスチャ"""
    from src.main import app
    from src.routers.report import verify_public_api_key

    # テスト用認証関数（TestSettingsの値を使用）
    async def test_verify_public_api_key():
        return test_settings.PUBLIC_API_KEY

    # 認証関数をオーバーライド
    app.dependency_overrides[verify_public_api_key] = test_verify_public_api_key

    return TestClient(app)
