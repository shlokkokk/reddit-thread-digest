import unittest

from src.archiver.compiler import (
    build_contextual_reply,
    build_markdown_digest,
    detect_opt_out,
)


class CompilerTests(unittest.TestCase):
    def test_markdown_digest_structure(self):
        digest = build_markdown_digest(
            [
                {
                    "title": "How to start a garden?",
                    "category": "Advice",
                    "score": 42,
                    "url": "https://reddit.com/r/Advice/example",
                    "summary": "Start with an easy herb.",
                }
            ]
        )

        self.assertTrue(digest.startswith("# Weekly Community Digest\n"))
        self.assertIn("## Advice", digest)
        self.assertIn("42 points", digest)
        self.assertIn("Start with an easy herb.", digest)

    def test_opt_out_detection_is_case_insensitive(self):
        self.assertTrue(detect_opt_out("Please !OPTOUT"))
        self.assertTrue(detect_opt_out("!optout", ["!optout"]))
        self.assertFalse(detect_opt_out("regular community tip"))

    def test_opted_out_title_is_not_added_to_digest(self):
        digest = build_markdown_digest(
            [{"title": "Private thread !optout", "category": "Advice"}]
        )
        self.assertIn("No qualifying discussions", digest)
        self.assertNotIn("Private thread", digest)

    def test_contextual_reply(self):
        reply = build_contextual_reply(
            "Helpful archive",
            "https://example.com/archive",
        )
        self.assertIn("Archived context:", reply)
        self.assertIn("https://example.com/archive", reply)

    def test_contextual_reply_honors_opt_out(self):
        reply = build_contextual_reply(
            "Thread !optout",
            "https://example.com/archive",
        )
        self.assertEqual(reply, "")


if __name__ == "__main__":
    unittest.main()
