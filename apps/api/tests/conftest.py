import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# report_status / report_launcher などは import 時の src.config.settings を持ち続けるので、
# 下の use_test_settings で差し替えても、データ置き場は実ディレクトリのままになる。
# src を import する前に環境変数で一時ディレクトリへ向け、開発者のレポート一覧
# (data/report_status.json) や成果物をテストが書き換えないようにする。
_TEST_DATA_ROOT = Path(tempfile.mkdtemp(prefix="kouchou-api-tests-"))
atexit.register(shutil.rmtree, _TEST_DATA_ROOT, ignore_errors=True)
for _name, _subdir in (
    ("DATA_DIR", "data"),
    ("REPORT_DIR", "pipeline/outputs"),
    ("CONFIG_DIR", "pipeline/configs"),
    ("INPUT_DIR", "pipeline/inputs"),
):
    os.environ[_name] = str(_TEST_DATA_ROOT / _subdir)
# 公開設定の変更などで送る revalidate 通知を、実在の public-viewer に届けない
# (到達できない loopback のポートにして、名前解決もさせない)
os.environ["REVALIDATE_URL"] = "http://127.0.0.1:9/api/revalidate"

# テスト実行時にsrcディレクトリをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_config import TestSettings  # noqa: E402


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

    yield TestClient(app)

    # 公開 API キーの検証を試すテストに上書きが残らないよう、後片付けする
    app.dependency_overrides.pop(verify_public_api_key, None)
