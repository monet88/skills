from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "search.py"
CATALOG = SCRIPT.parent.parent / "references" / "patterns.json"
SPEC = importlib.util.spec_from_file_location("image_prompt_search", SCRIPT)
assert SPEC and SPEC.loader
SEARCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEARCH)


class SearchCatalogTests(unittest.TestCase):
    def test_vietnamese_poster_query_finds_typography_template(self) -> None:
        result = SEARCH.search_catalog("áp phích chữ tiếng Việt", max_results=3)
        ids = [item["id"] for item in result["results"]]
        self.assertIn("template-poster-typography", ids)

    def test_edit_query_ranks_the_invariant_contract_first(self) -> None:
        result = SEARCH.search_catalog(
            "preserve face replace outfit",
            mode="edit",
            max_results=3,
        )
        ids = [item["id"] for item in result["results"]]
        self.assertIn("mode-edit-invariants", ids)
        self.assertEqual("mode-edit-invariants", result["results"][0]["id"])

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


class RetrievalContractTests(unittest.TestCase):
    """One query per intent that a prompt author actually types."""

    EXPECTED_TOP_HIT = {
        "tattoo flash sheet": "template-tattoo-flash",
        "isometric diorama": "template-isometric",
        "cyberpunk neon city": "template-retro-cyberpunk",
        "whitepaper document page": "template-document-publishing",
        "pose sheet 16 panels": "template-pose-sheet",
        "3d collectible toy figure": "template-3d-collectible",
        "chinese ink wash landscape": "template-history-classical",
        "reverse prompt from image": "mode-reverse-anchors",
        "game key art hud": "template-gaming-keyart",
        "screen photography phone shot": "template-screen-photography",
        "sticker sheet": "template-sticker-pack",
        "mind map diagram": "template-research-diagram",
        "exploded view blueprint": "template-technical-illustration",
        "fashion editorial portrait": "template-fashion-editorial",
        "negative prompt avoid artifacts": "craft-targeted-avoid",
        "inpaint remove background": "mode-inpaint",
        "change only the sofa": "craft-edit-preserve-inventory",
        "risograph style artefacts": "craft-style-artefacts",
        "which gpt image 2.5 model": "provider-openai-2-5-models",
        "sketch to photoreal": "mode-sketch-to-render",
        "transparent background cutout png": "mode-transparent-cutout",
        "nano banana positive framing": "provider-gemini-creative-brief",
        "product packaging hero shot": "template-product-commerce",
        "restaurant food photography": "template-food",
        "architecture interior render": "template-architecture-interior",
        "infographic timeline education": "template-infographic",
        "research paper figure flow": "template-research-diagram",
        "high fidelity app mockup": "template-ui-mockup",
        "storyboard shot list": "template-storyboard",
        "upscale to 4k restore old photo": "mode-upscale-restore",
        "translate text in image to korean": "mode-text-localization",
        "magazine cover on desk mockup": "template-physical-object-mockup",
        "how a chef sees a kitchen": "template-perspective-framing",
        "2000s nostalgic bedroom vibe": "craft-vibe-signature-details",
        "blend two images into one": "mode-multi-reference",
        "assign reference roles": "mode-multi-reference",
        "mẫu A mặc đồ mẫu B thay background mẫu C": "mode-multi-reference",
        "model wearing outfit from image 2 replace background image 3": "mode-multi-reference",
        "背景换掉，人物保留": "mode-multi-reference",
        "thiết kế poster phim kinh dị": "template-poster-typography",
        "dịch chữ trên lon sang tiếng Hàn": "mode-text-localization",
        "tách nền sản phẩm": "mode-transparent-cutout",
        "phác thảo nội thất phòng khách": "template-architecture-interior",
        "keep character consistent across panels": "craft-multi-panel-consistency",
        "poster for a rock concert": "template-poster-typography",
        "deck of slides with data": "template-document-publishing",
    }

    EXPECTED_EMPTY = (
        "ảnh cưới",
        "sơ yếu lý lịch",
        "texture seamless pattern",
        "menu board restaurant",
        "comic strip panel",
    )

    def test_known_intents_rank_their_pattern_first(self) -> None:
        for query, expected in self.EXPECTED_TOP_HIT.items():
            with self.subTest(query=query):
                result = SEARCH.search_catalog(query, max_results=1)
                self.assertTrue(result["results"], f"{query} returned no match")
                self.assertEqual(expected, result["results"][0]["id"])

    def test_partial_overlap_returns_no_match_instead_of_a_wrong_pattern(self) -> None:
        # Each query shares one incidental token with an unrelated record; a
        # single-token coincidence must not be presented as a house pattern.
        for query in self.EXPECTED_EMPTY:
            with self.subTest(query=query):
                result = SEARCH.search_catalog(query, max_results=3)
                self.assertEqual([], result["results"])

    def test_reverse_mode_filter_selects_only_reverse_patterns(self) -> None:
        result = SEARCH.search_catalog("reverse prompt", mode="reverse", max_results=3)
        self.assertGreater(result["count"], 0)
        for item in result["results"]:
            self.assertIn("reverse", item["modes"])

    def test_every_query_is_translated_to_english_before_matching(self) -> None:
        translated = SEARCH.translate_query("mẫu A mặc đồ của mẫu B thay background mẫu C")
        self.assertIn("wearing outfit", translated)
        self.assertIn("replace background", translated)
        self.assertIn("model", translated)

    def test_translation_does_not_rewrite_english_queries(self) -> None:
        for query in (
            "do not change the background",
            "preserve face replace outfit",
            "poster for a horror movie",
        ):
            with self.subTest(query=query):
                self.assertEqual(SEARCH.normalize(query), SEARCH.translate_query(query))

    def test_json_result_reports_the_english_query(self) -> None:
        result = SEARCH.search_catalog("tách nền sản phẩm", max_results=1)
        self.assertEqual("cutout transparent background product", result["query_used"])
        self.assertEqual("mode-transparent-cutout", result["results"][0]["id"])


class CatalogIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = json.loads(CATALOG.read_text(encoding="utf-8"))["records"]

    def test_record_ids_are_unique(self) -> None:
        ids = [record["id"] for record in self.records]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_record_declares_provider_mode_and_source(self) -> None:
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertTrue(record["providers"])
                self.assertTrue(record["modes"])
                self.assertTrue(record["pitfalls"])

    def test_source_is_author_repo_path_or_url(self) -> None:
        pattern = re.compile(r"^author$|^[\w.-]+/[\w.-]+ .+|^https?://\S+$")
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertRegex(record["source"], pattern)


if __name__ == "__main__":
    unittest.main()
