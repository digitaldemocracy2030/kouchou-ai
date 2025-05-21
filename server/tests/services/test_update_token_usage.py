from unittest.mock import patch

from src.schemas.report import ReportStatus, ReportVisibility
from src.services.report_status import _report_status, update_token_usage


class TestUpdateTokenUsage:
    """update_token_usage関数のテスト"""

    def setup_method(self):
        """各テスト前に_report_statusをクリアして初期化"""
        _report_status.clear()
        _report_status["test-slug"] = {
            "status": ReportStatus.READY.value,
            "title": "Test Report",
            "description": "Test Description",
            "visibility": ReportVisibility.PUBLIC.value,
            "is_pubcom": False,
            "created_at": "2023-01-01T00:00:00Z",
            "token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }
        
    def teardown_method(self):
        """各テスト後に_report_statusをクリア"""
        _report_status.clear()

    def test_update_token_usage_all_values(self):
        """トークン使用量（合計、入力、出力）を正しく更新できることをテスト"""
        update_token_usage("test-slug", 100, 40, 60)

        assert _report_status["test-slug"]["token_usage"] == 100
        assert _report_status["test-slug"]["token_usage_input"] == 40
        assert _report_status["test-slug"]["token_usage_output"] == 60

    def test_update_token_usage_total_only(self):
        """合計トークン使用量のみを更新できることをテスト"""
        update_token_usage("test-slug", 300)

        assert _report_status["test-slug"]["token_usage"] == 300
        assert _report_status["test-slug"]["token_usage_input"] == 0
        assert _report_status["test-slug"]["token_usage_output"] == 0

    def test_update_token_usage_nonexistent_slug(self):
        """存在しないスラッグの場合は警告ログが出力されるだけで例外は発生しないことをテスト"""
        update_token_usage("non-existent-slug", 200, 80, 120)

        assert "test-slug" in _report_status
        assert "non-existent-slug" not in _report_status

    def test_update_token_usage_calls_save_status(self):
        """update_token_usage関数がsave_status関数を呼び出すことをテスト"""
        with patch("src.services.report_status.save_status") as mock_save_status:
            update_token_usage("test-slug", 400, 160, 240)

            mock_save_status.assert_called_once()

    def test_update_token_usage_with_none_values(self):
        """入力・出力トークン使用量にNoneを指定した場合のテスト"""
        _report_status["test-slug"]["token_usage_input"] = 50
        _report_status["test-slug"]["token_usage_output"] = 70

        update_token_usage("test-slug", 500, None, None)

        assert _report_status["test-slug"]["token_usage"] == 500
        assert _report_status["test-slug"]["token_usage_input"] == 50
        assert _report_status["test-slug"]["token_usage_output"] == 70

    def test_update_token_usage_with_provider_and_model(self):
        """providerとmodelを指定した場合のテスト"""
        update_token_usage("test-slug", 600, 200, 400, "openai", "gpt-4o")

        assert _report_status["test-slug"]["token_usage"] == 600
        assert _report_status["test-slug"]["token_usage_input"] == 200
        assert _report_status["test-slug"]["token_usage_output"] == 400
        assert _report_status["test-slug"]["provider"] == "openai"
        assert _report_status["test-slug"]["model"] == "gpt-4o"

    @patch("src.services.report_status.LLMPricing.calculate_cost", return_value=0.123)
    def test_update_token_usage_with_cost_calculation(self, mock_calculate_cost):
        """providerとmodelを指定した場合に推定コストが計算されることをテスト"""
        update_token_usage("test-slug", 700, 300, 400, "azure", "gpt-4o-mini")

        assert _report_status["test-slug"]["provider"] == "azure"
        assert _report_status["test-slug"]["model"] == "gpt-4o-mini"
        assert _report_status["test-slug"]["estimated_cost"] == 0.123
        mock_calculate_cost.assert_called_once_with("azure", "gpt-4o-mini", 300, 400)

    def test_update_token_usage_with_none_provider_model(self):
        """providerとmodelにNoneを指定した場合のテスト"""
        # 初期値を設定
        _report_status["test-slug"]["provider"] = "openai"
        _report_status["test-slug"]["model"] = "gpt-4o"

        # Noneを指定して更新
        update_token_usage("test-slug", 800, 350, 450, None, None)

        # providerとmodelは変更されないこと
        assert _report_status["test-slug"]["token_usage"] == 800
        assert _report_status["test-slug"]["token_usage_input"] == 350
        assert _report_status["test-slug"]["token_usage_output"] == 450
        assert _report_status["test-slug"]["provider"] == "openai"
        assert _report_status["test-slug"]["model"] == "gpt-4o"
