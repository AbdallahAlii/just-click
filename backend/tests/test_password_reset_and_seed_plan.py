"""Focused unit tests for password-reset tokens and chapter material seed plan.

Run:
  cd backend && PYTHONPATH=src .venv/bin/python -m unittest tests.test_password_reset_and_seed_plan -v
"""

from __future__ import annotations

import unittest
from datetime import timedelta

from cmcp.common.security.tokens import (
    generate_password_reset_token,
    hash_token,
    verify_token,
)
from cmcp.seed_data.university.data import UNIVERSITIES
from cmcp.seed_data.university.seeder import _chapter_material_plan, _mock_files_dir


class PasswordResetTokenTests(unittest.TestCase):
    def test_generate_and_verify(self):
        tok = generate_password_reset_token(ttl_minutes=60)
        self.assertTrue(tok.token)
        self.assertEqual(tok.token_hash, hash_token(tok.token))
        self.assertTrue(verify_token(tok.token, tok.token_hash))
        self.assertFalse(verify_token("wrong-token", tok.token_hash))

    def test_expiry_is_in_future(self):
        tok = generate_password_reset_token(ttl_minutes=30)
        # expires_at should be roughly now + 30 minutes
        delta = tok.expires_at - tok.expires_at.replace(microsecond=0)
        self.assertIsNotNone(tok.expires_at)
        self.assertGreater(tok.expires_at.timestamp(), 0)


class SeedMaterialPlanTests(unittest.TestCase):
    def test_materials_config_lists_real_mock_files(self):
        material_spec = UNIVERSITIES[0]["academic"]["materials"]
        base = _mock_files_dir(material_spec)
        self.assertTrue(base.exists(), f"mock_files dir missing: {base}")

        for group in ("pdf_files", "slide_files", "doc_files", "video_files"):
            names = material_spec.get(group) or []
            self.assertTrue(names, f"{group} should not be empty")
            for name in names:
                path = base / name
                self.assertTrue(path.is_file(), f"Missing mock file for {group}: {path}")

        links = material_spec.get("link_resources") or []
        self.assertGreaterEqual(len(links), 3)
        for link in links:
            url = str(link.get("url") or "")
            self.assertTrue(url.startswith("https://"), url)

    def test_chapter_plan_approximately_fifteen_with_required_types(self):
        material_spec = UNIVERSITIES[0]["academic"]["materials"]
        plan = _chapter_material_plan(material_spec)
        self.assertGreaterEqual(len(plan), 14)
        self.assertLessEqual(len(plan), 16)

        kinds = {item["kind"] for item in plan}
        for required in ("slides", "pdf", "doc", "video", "link"):
            self.assertIn(required, kinds)

        link_items = [i for i in plan if i["kind"] == "link"]
        self.assertTrue(link_items)
        for item in link_items:
            self.assertTrue(item.get("link"))
            self.assertTrue(str(item["link"].get("url", "")).startswith("https://"))


if __name__ == "__main__":
    unittest.main()
