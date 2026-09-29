import unittest

from grouping import group_videos


def video(identifier, title, views, published, channel=None):
    return {
        "id": identifier,
        "title": title,
        "viewCount": views,
        "publishedAt": published,
        "channelTitle": channel or f"Channel {identifier}",
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
        self.assertIn('phrase "agent workflows"', themes[0]["why"])
        self.assertEqual(themes[1]["label"], "Other relevant signals")

    def test_generic_words_do_not_dominate_specific_subjects(self):
        videos = [
            video("a", "Trending AI Edit Prompt", 900, "2026-09-29T10:00:00Z"),
            video(
                "b",
                "Trending AI Edit Prompt Tutorial",
                800,
                "2026-09-29T09:00:00Z",
            ),
            video(
                "c",
                "Hotel Lobby Edit Trending",
                100,
                "2026-09-29T08:00:00Z",
            ),
            video(
                "d",
                "Hotel Lobby AI Edit",
                90,
                "2026-09-29T07:00:00Z",
            ),
        ]

        themes = group_videos(videos, "AI video editing")
        labels = [theme["label"] for theme in themes]

        self.assertEqual(labels[0], "Hotel Lobby")
        self.assertNotIn("Trending", labels)
        self.assertNotIn("Edit", labels)
        self.assertNotIn("Prompt", labels)
        self.assertEqual(labels[-1], "Other relevant signals")

    def test_recurring_observed_subjects_become_specific_themes(self):
        videos = [
            video("a", "Car Jump Edit Trending", 10, "2026-09-29T10:00:00Z"),
            video("b", "Car Jump AI Edit", 11, "2026-09-29T09:00:00Z"),
            video("c", "Spider-Man Edit Trending", 12, "2026-09-29T08:00:00Z"),
            video("d", "Spider-Man Fan Edit", 13, "2026-09-29T07:00:00Z"),
            video("e", "Hotel Lobby Edit", 14, "2026-09-29T06:00:00Z"),
            video("f", "Hotel Lobby Viral Edit", 15, "2026-09-29T05:00:00Z"),
            video("g", "Fairy Girl Edit", 16, "2026-09-29T04:00:00Z"),
            video("h", "Fairy Girl Trending Edit", 17, "2026-09-29T03:00:00Z"),
        ]

        themes = group_videos(videos, "AI video editing")
        labels = {theme["label"] for theme in themes}

        self.assertEqual(
            labels,
            {"Car Jump", "Spider-Man", "Hotel Lobby", "Fairy Girl"},
        )
        for theme in themes:
            self.assertGreaterEqual(theme["videoCount"], 2)
            self.assertGreaterEqual(
                len({video["channelTitle"] for video in theme["videos"]}),
                2,
            )

    def test_same_channel_duplicates_do_not_create_a_theme(self):
        videos = [
            video(
                "a",
                "Car Jump Edit One",
                10,
                "2026-09-29T10:00:00Z",
                "Duplicate Channel",
            ),
            video(
                "b",
                "Car Jump Edit Two",
                20,
                "2026-09-29T09:00:00Z",
                "Duplicate Channel",
            ),
        ]

        themes = group_videos(videos, "AI video editing")

        self.assertEqual(
            [theme["label"] for theme in themes], ["Other relevant signals"]
        )
        self.assertEqual(themes[0]["videoCount"], 2)

    def test_no_defensible_recurrence_returns_only_remainder(self):
        videos = [
            video("a", "Trending Edit Prompt", 10, "2026-09-29T10:00:00Z"),
            video("b", "Viral Video Tutorial", 20, "2026-09-29T09:00:00Z"),
            video("c", "Amazing New Shorts", 30, "2026-09-29T08:00:00Z"),
        ]

        themes = group_videos(videos, "AI video editing")

        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["label"], "Other relevant signals")
        self.assertEqual(themes[0]["videoCount"], 3)

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
