"""Unit-level rules for public material discussion replies.

Run:
  cd backend && PYTHONPATH=src .venv/bin/python -m unittest tests.test_feedback_discussion_rules -v
"""

from __future__ import annotations

import unittest

from cmcp.modules.materials.models import MaterialFeedbackTypeEnum
from cmcp.modules.materials.feedback_schemas import (
    MaterialFeedbackCreateIn,
    MaterialFeedbackDiscussionReplyIn,
)


class FeedbackDiscussionSchemaTests(unittest.TestCase):
    def test_public_types_still_accepted(self):
        for ftype in ("comment", "clarification"):
            payload = MaterialFeedbackCreateIn(feedback_type=ftype, message="Hello class")
            self.assertEqual(payload.feedback_type, ftype)
            self.assertEqual(payload.message, "Hello class")

    def test_broken_file_still_requires_message(self):
        with self.assertRaises(Exception):
            MaterialFeedbackCreateIn(feedback_type="broken_file", message="")

    def test_rating_unchanged(self):
        payload = MaterialFeedbackCreateIn(feedback_type="rating", rating=4)
        self.assertEqual(payload.rating, 4)

    def test_discussion_reply_trims_message(self):
        payload = MaterialFeedbackDiscussionReplyIn(message="  thanks  ")
        self.assertEqual(payload.message, "thanks")

    def test_public_types_enum_values(self):
        public = {
            MaterialFeedbackTypeEnum.COMMENT.value,
            MaterialFeedbackTypeEnum.CLARIFICATION.value,
        }
        privateish = {MaterialFeedbackTypeEnum.BROKEN_FILE.value}
        self.assertIn("comment", public)
        self.assertIn("clarification", public)
        self.assertIn("broken_file", privateish)
        self.assertNotIn("rating", public)


if __name__ == "__main__":
    unittest.main()
