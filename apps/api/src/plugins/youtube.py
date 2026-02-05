"""
YouTube input plugin for fetching video comments.

This plugin requires a YouTube Data API v3 key to function.
The API key must be set in the YOUTUBE_API_KEY environment variable.

Usage:
    1. Enable the YouTube Data API v3 in Google Cloud Console
    2. Create an API key
    3. Set YOUTUBE_API_KEY environment variable
    4. The plugin will become available in the admin UI
"""

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import polars as pl

from src.plugins.base import InputPlugin, PluginManifest, PluginSetting, SettingType
from src.plugins.registry import PluginRegistry

logger = logging.getLogger("uvicorn")

# YouTube URL patterns
VIDEO_PATTERNS = [
    r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
]
PLAYLIST_PATTERN = r"youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"


def parse_youtube_url(url: str) -> tuple[str | None, str | None]:
    """
    Extract video ID and/or playlist ID from a YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Tuple of (video_id, playlist_id), either may be None
    """
    video_id = None
    playlist_id = None

    # Try video patterns
    for pattern in VIDEO_PATTERNS:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    # Check for playlist in URL parameters
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "list" in params:
        playlist_id = params["list"][0]

    # Also try direct playlist URL pattern
    if not playlist_id:
        match = re.search(PLAYLIST_PATTERN, url)
        if match:
            playlist_id = match.group(1)

    return video_id, playlist_id


@PluginRegistry.register
class YouTubePlugin(InputPlugin):
    """
    Input plugin for YouTube video comments.

    Fetches comments from YouTube videos using the YouTube Data API v3.
    Supports both single videos and playlists.
    """

    manifest = PluginManifest(
        id="youtube",
        name="YouTube",
        description="YouTubeの動画コメントを取得します。",
        version="1.0.0",
        icon="youtube",
        placeholder="https://www.youtube.com/watch?v=... または https://www.youtube.com/playlist?list=...",
        enabled_by_default=False,  # Requires API key configuration
        settings=[
            PluginSetting(
                key="YOUTUBE_API_KEY",
                label="YouTube API Key",
                description="YouTube Data API v3のAPIキー。Google Cloud Consoleで取得できます。",
                setting_type=SettingType.SECRET,
                required=True,
            ),
        ],
    )

    def validate_source(self, source: str) -> tuple[bool, str | None]:
        """Validate YouTube URL."""
        video_id, playlist_id = parse_youtube_url(source)
        if not video_id and not playlist_id:
            return False, "無効なYouTube URLです。動画またはプレイリストのURLを入力してください。"
        return True, None

    def fetch_data(self, source: str, **options: Any) -> pl.DataFrame:
        """
        Fetch comments from a YouTube video or playlist.

        Args:
            source: YouTube URL
            max_results: Maximum number of comments to fetch (default: 1000)
            include_replies: Whether to include reply comments (default: False)

        Returns:
            DataFrame with columns: comment-id, comment-body, source, url,
            plus optional: author, published_at, like_count
        """
        # Validate configuration first
        self.ensure_configured()

        # Validate URL
        is_valid, error = self.validate_source(source)
        if not is_valid:
            raise ValueError(error)

        video_id, playlist_id = parse_youtube_url(source)
        max_results = options.get("max_results", 1000)
        include_replies = options.get("include_replies", False)

        # Get API key from settings
        api_key = self.manifest.settings[0].get_value()

        if video_id:
            return self._fetch_video_comments(video_id, api_key, max_results, include_replies)
        elif playlist_id:
            return self._fetch_playlist_comments(playlist_id, api_key, max_results, include_replies)
        else:
            raise ValueError("Could not extract video or playlist ID from URL")

    def _fetch_video_comments(
        self, video_id: str, api_key: str, max_results: int, include_replies: bool
    ) -> pl.DataFrame:
        """Fetch comments from a single video."""
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError as e:
            raise ImportError(
                "google-api-python-client is required for YouTube plugin. "
                "Install with: pip install google-api-python-client"
            ) from e

        youtube = build("youtube", "v3", developerKey=api_key)
        comments = []

        try:
            # First, get video info
            video_response = youtube.videos().list(part="snippet", id=video_id).execute()

            if not video_response.get("items"):
                raise ValueError(f"Video not found: {video_id}")

            video_title = video_response["items"][0]["snippet"]["title"]

            # Fetch comment threads
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_results),  # API max is 100 per request
                textFormat="plainText",
            )

            while request and len(comments) < max_results:
                response = request.execute()

                for item in response.get("items", []):
                    # Top-level comment
                    snippet = item["snippet"]["topLevelComment"]["snippet"]
                    comment_id = item["snippet"]["topLevelComment"]["id"]

                    comments.append(
                        {
                            "comment-id": comment_id,
                            "comment-body": snippet["textDisplay"],
                            "source": "YouTube",
                            "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                            "attribute_author": snippet.get("authorDisplayName", ""),
                            "attribute_published_at": snippet.get("publishedAt", ""),
                            "attribute_like_count": snippet.get("likeCount", 0),
                            "attribute_video_title": video_title,
                        }
                    )

                    # Include replies if requested
                    if include_replies and "replies" in item:
                        for reply in item["replies"]["comments"]:
                            reply_snippet = reply["snippet"]
                            reply_id = reply["id"]
                            comments.append(
                                {
                                    "comment-id": reply_id,
                                    "comment-body": reply_snippet["textDisplay"],
                                    "source": "YouTube",
                                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={reply_id}",
                                    "attribute_author": reply_snippet.get("authorDisplayName", ""),
                                    "attribute_published_at": reply_snippet.get("publishedAt", ""),
                                    "attribute_like_count": reply_snippet.get("likeCount", 0),
                                    "attribute_video_title": video_title,
                                    "attribute_is_reply": "true",
                                }
                            )

                    if len(comments) >= max_results:
                        break

                # Get next page
                request = youtube.commentThreads().list_next(request, response)

        except HttpError as e:
            if e.resp.status == 403:
                raise ValueError(
                    "YouTube APIへのアクセスが拒否されました。APIキーを確認してください。"
                    "また、この動画のコメントが無効になっている可能性があります。"
                ) from e
            elif e.resp.status == 404:
                raise ValueError(f"動画が見つかりません: {video_id}") from e
            else:
                raise ValueError(f"YouTube APIエラー: {e}") from e

        logger.info(f"Fetched {len(comments)} comments from YouTube video {video_id}")
        return pl.DataFrame(comments)

    def _fetch_playlist_comments(
        self, playlist_id: str, api_key: str, max_results: int, include_replies: bool
    ) -> pl.DataFrame:
        """Fetch comments from all videos in a playlist."""
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError as e:
            raise ImportError(
                "google-api-python-client is required for YouTube plugin. "
                "Install with: pip install google-api-python-client"
            ) from e

        youtube = build("youtube", "v3", developerKey=api_key)
        all_comments = []

        try:
            # Get playlist items
            request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50)

            video_ids = []
            while request and len(video_ids) < 50:  # Limit to 50 videos
                response = request.execute()
                for item in response.get("items", []):
                    video_ids.append(item["snippet"]["resourceId"]["videoId"])
                request = youtube.playlistItems().list_next(request, response)

            logger.info(f"Found {len(video_ids)} videos in playlist {playlist_id}")

            # Fetch comments from each video
            comments_per_video = max(max_results // len(video_ids), 10) if video_ids else max_results

            for video_id in video_ids:
                try:
                    video_comments = self._fetch_video_comments(video_id, api_key, comments_per_video, include_replies)
                    all_comments.append(video_comments)

                    if sum(len(df) for df in all_comments) >= max_results:
                        break
                except ValueError as e:
                    # Skip videos with disabled comments
                    logger.warning(f"Skipping video {video_id}: {e}")
                    continue

        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"プレイリストが見つかりません: {playlist_id}") from e
            else:
                raise ValueError(f"YouTube APIエラー: {e}") from e

        if not all_comments:
            return pl.DataFrame(
                {
                    "comment-id": [],
                    "comment-body": [],
                    "source": [],
                    "url": [],
                }
            )

        result = pl.concat(all_comments, how="vertical")
        logger.info(f"Fetched {len(result)} total comments from playlist {playlist_id}")
        return result.head(max_results)
