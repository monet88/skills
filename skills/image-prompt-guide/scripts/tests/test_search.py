from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "search.py"
SPEC = importlib.util.spec_from_file_location("image_prompt_search", SCRIPT)
assert SPEC and SPEC.loader
SEARCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEARCH)


class SearchCatalogTests(unittest.TestCase):
    def test_vietnamese_poster_query_finds_typography_template(self) -> None:
        result = SEARCH.search_catalog("áp phích chữ tiếng Việt", max_results=3)
        ids = [item["id"] for item in result["results"]]
        self.assertIn("template-poster-typography", ids)

    def test_edit_query_finds_invariant_contract(self) -> None:
        result = SEARCH.search_catalog(
            "preserve face replace outfit",
            mode="edit",
            max_results=3,
        )
        ids = [item["id"] for item in result["results"]]
        self.assertIn("mode-edit-invariants", ids)

    def test_gemini_filter_keeps_provider_and_universal_patterns(self) -> None:
        result = SEARCH.search_catalog(
            "Gemini natural prose creative brief",
            provider="gemini",
            max_results=3,
        )
        self.assertEqual("provider-gemini-creative-brief", result["results"][0]["id"])
        for item in result["results"]:
            self.assertTrue("gemini" in item["providers"] or "universal" in item["providers"])

    def test_unknown_query_returns_explicit_empty_result(self) -> None:
        result = SEARCH.search_catalog("qzxwvuplm", max_results=3)
        self.assertEqual(0, result["count"])
        self.assertEqual([], result["results"])

    def test_cli_json_is_complete_and_parseable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "product packaging", "--domain", "template", "--json"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        result = json.loads(completed.stdout)
        self.assertGreater(result["count"], 0)
        self.assertIn("prompt_shape", result["results"][0])


if __name__ == "__main__":
    unittest.main()
