"""Test cases for YouTube plugin."""

import json
import sys
import types
from types import SimpleNamespace

import pytest

from src.plugins.youtube import YouTubePlugin, parse_youtube_url

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
VIDEO_IDS = [f"vid{i}aaaaaaa" for i in range(1, 6)]
COMMENTS_PER_VIDEO = 3
FAKE_API_KEY = "fake-youtube-key"


class FakeHttpError(Exception):
    """googleapiclient.errors.HttpError と同じ形 (resp, content: bytes, uri) の偽物。"""

    def __init__(self, resp, content, uri=None):
        if not isinstance(content, bytes):
            raise TypeError("HTTP content should be bytes")
        self.resp = resp
        self.content = content
        self.uri = uri
        data = json.loads(content.decode("utf-8"))
        self.reason = data["error"]["message"]
        self.error_details = data["error"].get("errors", "")
        super().__init__(f'<HttpError {resp.status} when requesting {uri} returned "{self.reason}">')


def _http_error(status: int, reason: str, domain: str = "youtube.commentThread") -> FakeHttpError:
    content = json.dumps(
        {
            "error": {
                "code": status,
                "message": f"message for {reason}",
                "errors": [{"message": f"message for {reason}", "domain": domain, "reason": reason}],
            }
        }
    ).encode("utf-8")
    uri = f"https://youtube.googleapis.com/youtube/v3/commentThreads?key={FAKE_API_KEY}&alt=json"
    return FakeHttpError(SimpleNamespace(status=status, reason="error"), content, uri=uri)


class _Request:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeYouTube:
    """playlistItems / videos / commentThreads だけを持つ YouTube クライアントの偽物。"""

    def __init__(self, failures: dict[str, FakeHttpError]):
        self.failures = failures

    def playlistItems(self):  # noqa: N802 - SDK と同じ名前
        items = [{"snippet": {"resourceId": {"videoId": vid}}} for vid in VIDEO_IDS]
        return SimpleNamespace(
            list=lambda **kwargs: _Request(lambda: {"items": items}),
            list_next=lambda request, response: None,
        )

    def videos(self):
        return SimpleNamespace(
            list=lambda **kwargs: _Request(lambda: {"items": [{"snippet": {"title": f"title {kwargs['id']}"}}]})
        )

    def commentThreads(self):  # noqa: N802 - SDK と同じ名前
        def list_(**kwargs):
            video_id = kwargs["videoId"]

            def execute():
                if video_id in self.failures:
                    raise self.failures[video_id]
                return {
                    "items": [
                        {
                            "snippet": {
                                "topLevelComment": {
                                    "id": f"{video_id}-c{i}",
                                    "snippet": {"textDisplay": f"comment {i}", "authorDisplayName": "a"},
                                }
                            }
                        }
                        for i in range(COMMENTS_PER_VIDEO)
                    ]
                }

            return _Request(execute)

        return SimpleNamespace(list=list_, list_next=lambda request, response: None)


@pytest.fixture
def fake_youtube(monkeypatch):
    """googleapiclient を偽物に差し替え、動画ごとの失敗を指定できるようにする（実 API は呼ばない）。"""
    failures: dict[str, FakeHttpError] = {}
    googleapiclient = types.ModuleType("googleapiclient")
    discovery = types.ModuleType("googleapiclient.discovery")
    errors = types.ModuleType("googleapiclient.errors")
    discovery.build = lambda *args, **kwargs: FakeYouTube(failures)
    errors.HttpError = FakeHttpError
    googleapiclient.discovery = discovery
    googleapiclient.errors = errors
    monkeypatch.setitem(sys.modules, "googleapiclient", googleapiclient)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)
    monkeypatch.setitem(sys.modules, "googleapiclient.errors", errors)
    monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
    return failures


class TestPlaylistErrorHandling:
    """プレイリスト取り込みで、飛ばしてよい失敗と取り込み全体を止める失敗を区別する。"""

    def test_all_videos_ok(self, fake_youtube):
        df = YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert len(df) == len(VIDEO_IDS) * COMMENTS_PER_VIDEO

    @pytest.mark.parametrize(
        ("status", "reason", "domain"),
        [
            (403, "commentsDisabled", "youtube.commentThread"),
            (404, "videoNotFound", "youtube.commentThread"),
            (403, "forbidden", "youtube.commentThread"),
        ],
    )
    def test_video_specific_failures_are_skipped(self, fake_youtube, status, reason, domain):
        fake_youtube[VIDEO_IDS[2]] = _http_error(status, reason, domain)
        df = YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert len(df) == (len(VIDEO_IDS) - 1) * COMMENTS_PER_VIDEO
        assert not any(url.startswith(f"https://www.youtube.com/watch?v={VIDEO_IDS[2]}") for url in df["url"])

    @pytest.mark.parametrize(
        ("status", "reason", "domain", "expected"),
        [
            (403, "quotaExceeded", "youtube.quota", "上限"),
            (403, "dailyLimitExceeded", "usageLimits", "上限"),
            (403, "rateLimitExceeded", "usageLimits", "上限"),
            (429, "rateLimitExceeded", "usageLimits", "上限"),
            (500, "backendError", "global", "一時的"),
            (503, "backendError", "global", "一時的"),
            (403, "forbidden", "global", "アクセスが拒否"),
        ],
    )
    def test_quota_and_transient_failures_abort_the_import(self, fake_youtube, status, reason, domain, expected):
        fake_youtube[VIDEO_IDS[2]] = _http_error(status, reason, domain)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert expected in str(exc_info.value)

    def test_failure_on_first_video_does_not_return_empty_success(self, fake_youtube):
        fake_youtube[VIDEO_IDS[0]] = _http_error(429, "rateLimitExceeded", "usageLimits")
        with pytest.raises(ValueError):
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)

    def test_all_videos_skipped_is_an_error(self, fake_youtube):
        for vid in VIDEO_IDS:
            fake_youtube[vid] = _http_error(403, "commentsDisabled")
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert "コメントを取得できませんでした" in str(exc_info.value)

    def test_single_video_comments_disabled_message(self, fake_youtube):
        fake_youtube[VIDEO_IDS[0]] = _http_error(403, "commentsDisabled")
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin().fetch_data(f"https://www.youtube.com/watch?v={VIDEO_IDS[0]}", max_results=10)
        assert "コメントが無効" in str(exc_info.value)
        # コメント無効を API キーの問題と取り違えさせない
        assert "APIキー" not in str(exc_info.value)


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
