import re
import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (root / "frontend" / "script.js").read_text(encoding="utf-8")

    def test_every_by_id_reference_exists_in_html(self):
        html_ids = set(re.findall(r'id="([^"]+)"', self.html))
        javascript_ids = set(re.findall(r'byId\("([^"]+)"\)', self.javascript))
        self.assertEqual(javascript_ids - html_ids, set())

    def test_admin_and_dw_panels_start_hidden(self):
        self.assertRegex(self.html, r'id="dw-nav"[^>]+hidden')
        self.assertRegex(self.html, r'id="admin-nav"[^>]+hidden')

    def test_frontend_does_not_embed_database_credentials(self):
        self.assertNotIn("DW_PASSWORD", self.html)
        self.assertNotIn("10.20.9.21", self.html)
        self.assertNotIn("5432", self.javascript)


if __name__ == "__main__":
    unittest.main()
