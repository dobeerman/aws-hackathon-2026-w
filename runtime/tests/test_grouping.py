import unittest

from grouping import group_videos


def video(identifier, title, views, published):
    return {
        "id": identifier,
        "title": title,
        "viewCount": views,
        "publishedAt": published,
        "url": f"https://www.youtube.com/watch?v={identifier}",
    }


class GroupingTests(unittest.TestCase):
    def test_repeated_title_phrase_becomes_explainable_theme(self):
        videos = [
            video("a", "Build AI agent workflows fast", 100, "2026-09-29T10:00:00Z"),
            video(
                "b",
                "AI agent workflows for creators",
                250,
                "2026-09-28T10:00:00Z",
            ),
            video("c", "A practical prompt guide", None, "2026-09-27T10:00:00Z"),
        ]

        themes = group_videos(videos, "AI")

        self.assertEqual(themes[0]["label"], "Agent Workflows")
        self.assertEqual(themes[0]["videoCount"], 2)
        self.assertEqual(themes[0]["availableViewTotal"], 350)
        self.assertEqual(themes[0]["videos"][0]["id"], "b")
        self.assertIn("evidence: agent workflows", themes[0]["why"])
        self.assertEqual(themes[1]["label"], "Other relevant signals")

    def test_empty_input_produces_no_themes(self):
        self.assertEqual(group_videos([], "anything"), [])

    def test_topic_words_do_not_create_a_circular_theme(self):
        videos = [
            video("a", "Python tutorial one", 1, "2026-09-29T10:00:00Z"),
            video("b", "Python tutorial two", 2, "2026-09-29T11:00:00Z"),
        ]

        themes = group_videos(videos, "Python tutorial")

        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["label"], "Other relevant signals")


if __name__ == "__main__":
    unittest.main()
