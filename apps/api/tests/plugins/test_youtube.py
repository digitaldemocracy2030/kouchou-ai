"""Test cases for YouTube plugin."""

import httpx
import pytest

import src.plugins.youtube as youtube_module
from src.plugins.youtube import YouTubePlugin, parse_youtube_url

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
VIDEO_IDS = [f"vid{i}aaaaaaa" for i in range(1, 6)]
COMMENTS_PER_VIDEO = 3
FAKE_API_KEY = "fake-youtube-key"


def _error_body(status: int, reason: str, domain: str) -> dict:
    return {
        "error": {
            "code": status,
            "message": f"message for {reason}",
            "errors": [{"message": f"message for {reason}", "domain": domain, "reason": reason}],
        }
    }


def _http_error(status: int, reason: str, domain: str = "youtube.commentThread") -> httpx.Response:
    return httpx.Response(status, json=_error_body(status, reason, domain))


class FakeYouTubeServer:
    """YouTube Data API の playlistItems / videos / commentThreads だけを返す偽物（実 API は呼ばない）。"""

    def __init__(self):
        # 動画 ID → commentThreads が返すエラー応答
        self.failures: dict[str, httpx.Response] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        resource = request.url.path.rsplit("/", 1)[-1]
        params = request.url.params
        if resource == "playlistItems":
            # 2 ページに分けて返し、nextPageToken をたどることを確かめる
            if params.get("pageToken") == "page2":
                ids, next_token = VIDEO_IDS[3:], None
            else:
                ids, next_token = VIDEO_IDS[:3], "page2"
            body: dict = {"items": [{"snippet": {"resourceId": {"videoId": vid}}} for vid in ids]}
            if next_token:
                body["nextPageToken"] = next_token
            return httpx.Response(200, json=body)
        if resource == "videos":
            return httpx.Response(200, json={"items": [{"snippet": {"title": f"title {params['id']}"}}]})
        if resource == "commentThreads":
            video_id = params["videoId"]
            if video_id in self.failures:
                return self.failures[video_id]
            items = [
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
            return httpx.Response(200, json={"items": items})
        return httpx.Response(404, json=_error_body(404, "notFound", "global"))


def _use_transport(monkeypatch, handler) -> None:
    original = youtube_module._new_http_client
    monkeypatch.setattr(
        youtube_module,
        "_new_http_client",
        lambda api_key: original(api_key, transport=httpx.MockTransport(handler)),
    )


@pytest.fixture
def fake_youtube(monkeypatch):
    """YouTube Data API への HTTP を偽物の応答に差し替え、動画ごとの失敗を指定できるようにする。"""
    server = FakeYouTubeServer()
    _use_transport(monkeypatch, server.handle)
    monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
    return server


class TestRequests:
    """YouTube Data API への送り方"""

    def test_api_key_is_sent_in_header_not_url(self, fake_youtube):
        YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert fake_youtube.requests
        for request in fake_youtube.requests:
            assert request.headers["X-Goog-Api-Key"] == FAKE_API_KEY
            assert FAKE_API_KEY not in str(request.url)
            assert "key" not in request.url.params

    def test_playlist_follows_next_page_token(self, fake_youtube):
        df = YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert len(df) == len(VIDEO_IDS) * COMMENTS_PER_VIDEO
        playlist_requests = [r for r in fake_youtube.requests if r.url.path.endswith("/playlistItems")]
        assert [r.url.params.get("pageToken") for r in playlist_requests] == [None, "page2"]

    def test_comment_threads_stop_at_max_results(self, monkeypatch):
        """max_results に達したら、次のページを取りに行かない。"""
        calls: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if request.url.path.endswith("/videos"):
                return httpx.Response(200, json={"items": [{"snippet": {"title": "t"}}]})
            page = int(request.url.params.get("pageToken") or 0)
            items = [
                {"snippet": {"topLevelComment": {"id": f"c{page}-{i}", "snippet": {"textDisplay": "x"}}}}
                for i in range(2)
            ]
            return httpx.Response(200, json={"items": items, "nextPageToken": str(page + 1)})

        _use_transport(monkeypatch, handler)
        df = YouTubePlugin()._fetch_video_comments("dQw4w9WgXcQ", FAKE_API_KEY, 3, False)
        assert len(df) == 3
        assert len([r for r in calls if r.url.path.endswith("/commentThreads")]) == 2

    def test_connection_error_is_user_facing(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out", request=request)

        _use_transport(monkeypatch, handler)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin()._fetch_video_comments("dQw4w9WgXcQ", FAKE_API_KEY, 10, False)
        assert "接続できませんでした" in str(exc_info.value)
        assert exc_info.value.__cause__ is None


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
        fake_youtube.failures[VIDEO_IDS[2]] = _http_error(status, reason, domain)
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
        fake_youtube.failures[VIDEO_IDS[2]] = _http_error(status, reason, domain)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert expected in str(exc_info.value)

    def test_failure_on_first_video_does_not_return_empty_success(self, fake_youtube):
        fake_youtube.failures[VIDEO_IDS[0]] = _http_error(429, "rateLimitExceeded", "usageLimits")
        with pytest.raises(ValueError):
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)

    def test_all_videos_skipped_is_an_error(self, fake_youtube):
        for vid in VIDEO_IDS:
            fake_youtube.failures[vid] = _http_error(403, "commentsDisabled")
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin().fetch_data(PLAYLIST_URL, max_results=1000)
        assert "コメントを取得できませんでした" in str(exc_info.value)

    def test_single_video_comments_disabled_message(self, fake_youtube):
        fake_youtube.failures[VIDEO_IDS[0]] = _http_error(403, "commentsDisabled")
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


def _install_failing_api(monkeypatch, failing_call: str, status: int):
    """failing_call への要求だけがエラー応答（本文に Bad Request）を返すようにする。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(f"/{failing_call}"):
            body = _error_body(status, "badRequest", "global")
            body["error"]["message"] = "Bad Request"
            return httpx.Response(status, json=body)
        return httpx.Response(200, json={"items": []})

    _use_transport(monkeypatch, handler)


class TestYouTubeErrorMessagesDoNotLeakApiKey:
    """エラーメッセージとトレースバックに API キーを含めない"""

    def test_video_http_error_message_hides_api_key(self, monkeypatch):
        import pytest

        _install_failing_api(monkeypatch, "videos", 400)
        with pytest.raises(ValueError) as exc_info:
            YouTubePlugin()._fetch_video_comments("dQw4w9WgXcQ", SECRET_KEY, 10, False)

        message = str(exc_info.value)
        assert SECRET_KEY not in message
        assert "key=" not in message
        assert "400" in message
        assert "Bad Request" in message

    def test_playlist_http_error_message_hides_api_key(self, monkeypatch):
        import pytest

        _install_failing_api(monkeypatch, "playlistItems", 500)
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
        """logger.exception などでトレースバックを出しても、連鎖した例外からキーが出ない"""
        import traceback

        _install_failing_api(monkeypatch, failing_call, status)
        with pytest.raises(ValueError) as exc_info:
            getattr(YouTubePlugin(), method)("dQw4w9WgXcQ", SECRET_KEY, 10, False)

        rendered = "".join(traceback.format_exception(exc_info.value))
        assert SECRET_KEY not in rendered
        assert exc_info.value.__cause__ is None
