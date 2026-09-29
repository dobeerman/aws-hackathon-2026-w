import io
import json
import unittest
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from unittest.mock import patch

from youtube import YouTubeError, search_videos


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class YouTubeClientTests(unittest.TestCase):
    @patch("youtube.urllib.request.urlopen")
    def test_search_uses_two_calls_and_returns_real_metadata_shape(self, urlopen):
        urlopen.side_effect = [
            FakeResponse({"items": [{"id": {"videoId": "abc123"}}]}),
            FakeResponse(
                {
                    "items": [
                        {
                            "id": "abc123",
                            "snippet": {
                                "title": "A real title",
                                "channelTitle": "Creator",
                                "publishedAt": "2026-09-28T12:00:00Z",
                                "thumbnails": {
                                    "medium": {"url": "https://i.ytimg.com/example.jpg"}
                                },
                            },
                            "statistics": {"viewCount": "1234"},
                            "contentDetails": {"duration": "PT58S"},
                        }
                    ]
                }
            ),
        ]

        result = search_videos(
            "video tools",
            7,
            "test-key",
            now=datetime(2026, 9, 29, tzinfo=timezone.utc),
        )

        self.assertEqual(urlopen.call_count, 2)
        search_url = urlopen.call_args_list[0].args[0].full_url
        search_query = urllib.parse.parse_qs(urllib.parse.urlparse(search_url).query)
        self.assertEqual(search_query["videoDuration"], ["short"])
        self.assertEqual(search_query["maxResults"], ["25"])
        self.assertEqual(search_query["publishedAfter"], ["2026-09-22T00:00:00Z"])
        self.assertEqual(result[0]["viewCount"], 1234)
        self.assertEqual(result[0]["url"], "https://www.youtube.com/watch?v=abc123")

    @patch("youtube.urllib.request.urlopen")
    def test_empty_search_skips_details_call(self, urlopen):
        urlopen.return_value = FakeResponse({"items": []})

        self.assertEqual(search_videos("niche", 3, "test-key"), [])
        self.assertEqual(urlopen.call_count, 1)

    @patch("youtube.urllib.request.urlopen")
    def test_quota_error_has_stable_useful_message(self, urlopen):
        payload = {
            "error": {"errors": [{"reason": "quotaExceeded"}]},
        }
        urlopen.side_effect = urllib.error.HTTPError(
            "https://example.test",
            403,
            "Forbidden",
            {},
            io.BytesIO(json.dumps(payload).encode("utf-8")),
        )

        with self.assertRaises(YouTubeError) as raised:
            search_videos("niche", 7, "test-key")

        self.assertEqual(raised.exception.code, "quota_exceeded")
        self.assertEqual(raised.exception.status, 429)
        self.assertNotIn("test-key", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
