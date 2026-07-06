import json
import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.frontend = cls.root / "frontend"
        cls.package = json.loads((cls.frontend / "package.json").read_text(encoding="utf-8"))
        cls.source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((cls.frontend / "src").rglob("*.ts*"))
        )
        cls.dist_html = (cls.frontend / "dist" / "index.html").read_text(encoding="utf-8")

    def test_react_vite_typescript_stack_is_configured(self):
        self.assertIn("react", self.package["dependencies"])
        self.assertIn("react-markdown", self.package["dependencies"])
        self.assertIn("vite", self.package["devDependencies"])
        self.assertIn("typescript", self.package["devDependencies"])
        self.assertEqual(self.package["scripts"]["build"], "tsc -b && vite build")

    def test_markdown_is_rendered_without_raw_html(self):
        self.assertIn("<ReactMarkdown", self.source)
        self.assertIn("skipHtml", self.source)
        self.assertNotIn("dangerouslySetInnerHTML", self.source)

    def test_access_and_history_contracts_remain_in_react(self):
        self.assertIn("user.role === 'admin'", self.source)
        self.assertIn("/conversations", self.source)
        self.assertIn("/assistant/chat", self.source)
        self.assertIn("/admin/knowledge/sync", self.source)

    def test_production_bundle_exists_and_uses_compiled_assets(self):
        self.assertIn("./assets/", self.dist_html)
        self.assertNotIn("/src/main.tsx", self.dist_html)
        self.assertTrue(any((self.frontend / "dist" / "assets").glob("*.js")))
        self.assertTrue(any((self.frontend / "dist" / "assets").glob("*.css")))

    def test_frontend_does_not_embed_secrets_or_legacy_analytics(self):
        combined = f"{self.source}\n{self.dist_html}".lower()
        self.assertNotIn("post" + "gres", combined)
        self.assertNotIn("ware" + "house", combined)
        self.assertNotIn("eyjhbgci", combined)
        self.assertNotIn("turso_auth_token=", combined)


if __name__ == "__main__":
    unittest.main()
