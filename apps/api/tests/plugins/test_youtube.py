"""Test cases for YouTube plugin."""

import pytest

from src.plugins.youtube import YouTubePlugin, parse_youtube_url


class TestParseYouTubeUrl:
    """Test cases for parse_youtube_url function."""

    def test_parse_standard_video_url(self):
        """標準的な動画URLを解析できる"""
        video_id, playlist_id = parse_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        assert playlist_id is None

    def test_parse_short_video_url(self):
        """短縮URLを解析できる"""
        video_id, playlist_id = parse_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        assert playlist_id is None

    def test_parse_embed_url(self):
        """埋め込みURLを解析できる"""
        video_id, playlist_id = parse_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        assert playlist_id is None

    def test_parse_video_with_playlist(self):
        """プレイリスト付き動画URLを解析できる"""
        video_id, playlist_id = parse_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        )
        assert video_id == "dQw4w9WgXcQ"
        assert playlist_id == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

    def test_parse_playlist_url(self):
        """プレイリストURLを解析できる"""
        video_id, playlist_id = parse_youtube_url(
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        )
        assert video_id is None
        assert playlist_id == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

    def test_parse_invalid_url(self):
        """無効なURLの場合は両方Noneを返す"""
        video_id, playlist_id = parse_youtube_url("https://www.google.com")
        assert video_id is None
        assert playlist_id is None

    def test_parse_malformed_url(self):
        """不正なURLの場合は両方Noneを返す"""
        video_id, playlist_id = parse_youtube_url("not-a-url")
        assert video_id is None
        assert playlist_id is None


class TestYouTubePlugin:
    """Test cases for YouTubePlugin class."""

    def test_manifest_properties(self):
        """マニフェストが正しく設定されている"""
        plugin = YouTubePlugin()

        assert plugin.manifest.id == "youtube"
        assert plugin.manifest.name == "YouTube"
        assert plugin.manifest.enabled_by_default is False
        assert len(plugin.manifest.settings) == 1
        assert plugin.manifest.settings[0].key == "YOUTUBE_API_KEY"
        assert plugin.manifest.settings[0].required is True

    def test_validate_source_valid_video(self):
        """有効な動画URLを検証できる"""
        plugin = YouTubePlugin()
        is_valid, error = plugin.validate_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert is_valid is True
        assert error is None

    def test_validate_source_valid_playlist(self):
        """有効なプレイリストURLを検証できる"""
        plugin = YouTubePlugin()
        is_valid, error = plugin.validate_source(
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        )

        assert is_valid is True
        assert error is None

    def test_validate_source_invalid(self):
        """無効なURLを検証できる"""
        plugin = YouTubePlugin()
        is_valid, error = plugin.validate_source("https://www.google.com")

        assert is_valid is False
        assert error is not None
        assert "無効なYouTube URL" in error


SECRET_KEY = "AIzaSECRETKEY1234567890"


class _FakeResp:
    def __init__(self, status: int):
        self.status = status


class _FakeHttpError(Exception):
    """googleapiclient.errors.HttpError と同じく str にキー入り URI を含む偽物"""

    def __init__(self, status: int, uri: str, reason: str):
        super().__init__()
        self.resp = _FakeResp(status)
        self.uri = uri
        self.reason = reason

    def __str__(self) -> str:
        return f'<HttpError {self.resp.status} when requesting {self.uri} returned "{self.reason}">'


def _install_fake_googleapiclient(monkeypatch, failing_call: str, status: int):
    import sys
    import types
    from unittest.mock import MagicMock

    uri = f"https://youtube.googleapis.com/youtube/v3/{failing_call}?alt=json&key={SECRET_KEY}"
    error = _FakeHttpError(status, uri, "Bad Request")

    client = MagicMock()
    getattr(client, failing_call).return_value.list.return_value.execute.side_effect = error

    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda *args, **kwargs: client
    errors = types.ModuleType("googleapiclient.errors")
    errors.HttpError = _FakeHttpError
    root = types.ModuleType("googleapiclient")
    monkeypatch.setitem(sys.modules, "googleapiclient", root)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)
    monkeypatch.setitem(sys.modules, "googleapiclient.errors", errors)


class TestYouTubeErrorMessagesDoNotLeakApiKey:
    """HttpError の文字列（キー入り URI）をエラーメッセージに含めない"""

    def test_video_http_error_message_hides_api_key(self, monkeypatch):
        import pytest

        _install_fake_googleapiclient(monkeypatch, "videos", 400)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin()._fetch_video_comments("dQw4w9WgXcQ", SECRET_KEY, 10, False)

        message = str(exc_info.value)
        assert SECRET_KEY not in message
        assert "key=" not in message
        assert "400" in message
        assert "Bad Request" in message

    def test_playlist_http_error_message_hides_api_key(self, monkeypatch):
        import pytest

        _install_fake_googleapiclient(monkeypatch, "playlistItems", 500)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin()._fetch_playlist_comments("PLxxxx", SECRET_KEY, 10, False)

        message = str(exc_info.value)
        assert SECRET_KEY not in message
        assert "key=" not in message
        assert "500" in message

    @pytest.mark.parametrize(
        ("method", "failing_call", "status"),
        [
            ("_fetch_video_comments", "videos", 400),
            ("_fetch_video_comments", "videos", 403),
            ("_fetch_video_comments", "videos", 404),
            ("_fetch_playlist_comments", "playlistItems", 404),
            ("_fetch_playlist_comments", "playlistItems", 500),
        ],
    )
    def test_traceback_does_not_chain_http_error(self, monkeypatch, method, failing_call, status):
        """logger.exception などでトレースバックを出しても、連鎖した HttpError からキーが出ない"""
        import traceback

        _install_fake_googleapiclient(monkeypatch, failing_call, status)
        with pytest.raises(ValueError) as exc_info:
            getattr(YouTubePlugin(), method)("dQw4w9WgXcQ", SECRET_KEY, 10, False)

        rendered = "".join(traceback.format_exception(exc_info.value))
        assert SECRET_KEY not in rendered
        assert exc_info.value.__cause__ is None
