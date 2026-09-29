import json
import os
import unittest
from unittest.mock import patch

import app


def event(body=None, method="POST", path="/api/search"):
    return {
        "rawPath": path,
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {"http": {"method": method}},
    }


class HandlerTests(unittest.TestCase):
    def setUp(self):
        app._cached_api_key = None

    def test_serves_web_ui(self):
        response = app.handler(event(method="GET", path="/"), None)

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("text/html", response["headers"]["content-type"])
        self.assertIn("YouTube only in this release", response["body"])

    def test_validates_topic_and_window(self):
        response = app.handler(event({"topic": "", "days": 7}), None)
        payload = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(payload["error"]["code"], "validation_error")

        response = app.handler(event({"topic": "valid", "days": 365}), None)
        self.assertEqual(response["statusCode"], 400)

    @patch("app.search_videos")
    @patch("app.get_api_key", return_value="test-key")
    def test_success_includes_fetch_time_and_methodology(self, _get_key, search):
        search.return_value = [
            {
                "id": "abc",
                "title": "Editing workflow example",
                "channelTitle": "Creator",
                "publishedAt": "2026-09-29T10:00:00Z",
                "viewCount": 42,
                "url": "https://www.youtube.com/watch?v=abc",
            }
        ]

        response = app.handler(
            event({"topic": "video editing", "days": 7}),
            None,
        )
        payload = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(payload["resultCount"], 1)
        self.assertTrue(payload["fetchedAt"].endswith("Z"))
        self.assertIn("signals from this search", payload["methodology"])
        self.assertIn("not an exact YouTube Shorts", payload["notice"])
        search.assert_called_once_with("video editing", 7, "test-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_is_a_useful_503(self):
        response = app.handler(event({"topic": "editing", "days": 7}), None)
        payload = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 503)
        self.assertEqual(payload["error"]["code"], "configuration_error")
        self.assertIn("not configured", payload["error"]["message"])

    @patch("app.search_videos", return_value=[])
    @patch("app.get_api_key", return_value="test-key")
    def test_empty_results_are_not_replaced_with_fixtures(self, _get_key, _search):
        response = app.handler(event({"topic": "very narrow", "days": 1}), None)
        payload = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(payload["themes"], [])
        self.assertIn("No matching", payload["emptyMessage"])


if __name__ == "__main__":
    unittest.main()
