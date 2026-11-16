import sys
import unittest
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_search_index import build_documents, clean_public_text  # noqa: E402
from validate_projects import load_manifests  # noqa: E402


class SearchIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = load_manifests()

    def test_every_project_and_verified_section_has_a_deep_link(self):
        docs = build_documents(self.projects, [])
        for project in self.projects:
            overview = next(doc for doc in docs if doc["id"] == f"{project['slug']}:project")
            self.assertEqual(overview["url"], f"/work/{project['slug']}/")
            for section in project["sections"]:
                result = next(doc for doc in docs if doc["id"] == f"{project['slug']}:{section['id']}")
                self.assertEqual(result["url"], f"/work/{project['slug']}/#{section['id']}")

    def test_only_successfully_built_published_app_paths_are_advertised(self):
        docs = build_documents(self.projects, [])
        built_path = ROOT / "generated" / "search-index" / "built-frontends.json"
        available = set(json.loads(built_path.read_text(encoding="utf-8")).get("available", [])) if built_path.is_file() else set()
        publishable = {project["slug"] for project in self.projects if project["frontend"].get("publish") and project["slug"] in available}
        for doc in docs:
            expected = f"/projects/{doc['slug']}/" if doc["slug"] in publishable else None
            self.assertEqual(doc["application_url"], expected)

    def test_only_approved_documentation_is_used_as_input(self):
        docs = build_documents(self.projects, [])
        self.assertEqual(len(docs), sum(1 + len(project["sections"]) for project in self.projects))
        self.assertTrue(all(doc["text"] for doc in docs))

    def test_markdown_secret_like_values_are_redacted_and_code_is_removed(self):
        text = clean_public_text("Public docs\n```env\nAPI_KEY=abc123\n```\npassword: should-not-appear")
        self.assertNotIn("abc123", text)
        self.assertNotIn("should-not-appear", text)
        self.assertIn("redacted", text)

    def test_generated_vector_artifacts_match_and_are_normalized(self):
        index_dir = ROOT / "generated" / "search-index"
        index = json.loads((index_dir / "documents.json").read_text(encoding="utf-8"))
        vectors = json.loads((index_dir / "embeddings.json").read_text(encoding="utf-8"))
        ids = {document["id"] for document in index["documents"]}
        self.assertEqual(len(ids), len(index["documents"]))
        self.assertEqual(vectors["index_hash"], index["meta"]["index_hash"])
        self.assertEqual(set(vectors["vectors"]), ids)
        for vector in vectors["vectors"].values():
            self.assertEqual(len(vector), 384)
            self.assertAlmostEqual(math.sqrt(sum(value * value for value in vector)), 1.0, places=3)

    def test_deployment_tree_has_only_bounded_static_assets_and_real_frontends(self):
        dist = ROOT / "dist"
        if not dist.is_dir():
            self.skipTest("static build has not been created")
        maximum = 25 * 1024 * 1024
        oversized = [str(path.relative_to(dist)) for path in dist.rglob("*") if path.is_file() and path.stat().st_size > maximum]
        self.assertEqual(oversized, [])
        self.assertTrue((dist / "index.html").is_file())
        self.assertTrue((dist / "search" / "index.html").is_file())
        self.assertTrue((dist / "projects" / "scholarlysources" / "index.html").is_file())
        self.assertFalse((dist / "projects" / "construct" / "index.html").exists())
        self.assertFalse(any(path.name.startswith("ort-wasm-simd-threaded.asyncify") and path.suffix == ".wasm" for path in dist.rglob("*")))


if __name__ == "__main__":
    unittest.main()
