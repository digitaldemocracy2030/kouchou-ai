import pytest

from src.utils.validation import validate_filename


class TestValidateFilename:
    """ファイル名検証関数のテストクラス"""

    @pytest.mark.parametrize(
        "filename",
        [
            "test123",  # 基本的な英数字
            "test-123",  # ハイフンを含む
            "123",  # 数字のみ
            "123test",  # 数字で始まる
            "test-file-name-123",  # 複数のハイフン
            "a" * 255,  # 最大長ちょうど
        ],
    )
    def test_valid_filenames(self, filename):
        """有効なファイル名のテスト"""
        result, message = validate_filename(filename)
        assert result is True
        assert message == ""

    @pytest.mark.parametrize(
        "filename, expected_msg",
        [
            ("", "ファイル名が空です"),
            ("Test123", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("test@123", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("テスト123", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("test_123", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("-test123", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("test123-", "ファイル名には英小文字、数字、ハイフンのみ使用できます"),
            ("a" * 256, "ファイル名が長すぎます。255文字以内にしてください"),
        ],
    )
    def test_invalid_filenames(self, filename, expected_msg):
        """無効なファイル名のテスト"""
        result, message = validate_filename(filename)
        assert result is False
        assert message == expected_msg

    def test_custom_max_length(self):
        """カスタム最大長のテスト"""
        # 最大長を超えるケース
        result, message = validate_filename("abcdefghijk", max_length=10)
        assert result is False
        assert message == "ファイル名が長すぎます。10文字以内にしてください"

        # 最大長ちょうどのケース
        result, message = validate_filename("abcdefghij", max_length=10)
        assert result is True
        assert message == ""
