"""Test cases for YouTube plugin."""

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
