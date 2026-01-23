from broadlistening.pipeline.services.parse_json_list import parse_extraction_response


class TestParseJsonList:
    """JSONリストのパース機能のテスト"""

    def test_parse_extraction_response_valid(self):
        """parse_extraction_response: 有効なJSONレスポンスを正しくパースできる"""
        # 有効なJSONレスポンス
        response = '{"extractedOpinionList": ["テスト1", "テスト2", "テスト3"]}'
        result = parse_extraction_response(response)
        assert result == ["テスト1", "テスト2", "テスト3"]

    def test_parse_extraction_response_empty_list(self):
        """parse_extraction_response: 空のリストを正しくパースできる"""
        # 空のリスト
        response = '{"extractedOpinionList": []}'
        result = parse_extraction_response(response)
        assert result == []

    def test_parse_extraction_response_invalid_json(self):
        """parse_extraction_response: 無効なJSONの場合は空のリストを返す"""
        # 無効なJSON
        response = '{"extractedOpinionList": ["テスト1", "テスト2"'
        result = parse_extraction_response(response)
        assert result == []

    def test_parse_extraction_response_no_key(self):
        """parse_extraction_response: extractedOpinionListキーがない場合は空のリストを返す"""
        # extractedOpinionListキーがない
        response = '{"results": ["テスト1", "テスト2"]}'
        result = parse_extraction_response(response)
        assert result == []

    def test_parse_extraction_response_unexpected_error(self):
        """parse_extraction_response: 予期しないエラーが発生した場合は空のリストを返す"""
        # 予期しないエラーを発生させる
        response = '{"extractedOpinionList": null}'
        result = parse_extraction_response(response)
        assert result == []  # 実際の実装ではNoneが返されるかもしれないが、空リストを期待
