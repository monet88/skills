#!/usr/bin/env python3
"""Offline keyword search for Image Prompt Guide patterns."""

from __future__ import annotations

import argparse
import difflib
import io
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = SKILL_DIR / "references" / "patterns.json"
DEFAULT_RESULTS = 3

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "about", "image", "prompt",
    "anh", "cho", "cua", "la", "mot", "nhung", "theo", "toi", "trong",
    "tu", "va", "ve", "voi",
}

SYNONYMS = {
    "ap phich": "poster typography headline",
    "anh that": "photorealistic photography",
    "bai dang": "social post",
    "bang dieu khien": "dashboard ui",
    "bang nhan vat": "character sheet turnaround",
    "bao bi": "packaging product commerce",
    "bieu do": "chart data visualization",
    "bo cuc": "composition layout canvas",
    "chinh sua": "edit preserve invariants",
    "chu": "text typography",
    "do an": "food photography",
    "dong thoi gian": "timeline infographic",
    "giao dien": "ui ux mockup",
    "giu nguyen": "preserve invariants",
    "ghep anh": "multi reference composition",
    "hoat hinh": "animation illustration anime",
    "kien truc": "architecture building",
    "lam dep": "beauty editorial",
    "mau nuoc": "watercolor illustration",
    "mat na": "mask inpaint region",
    "nhan dien": "brand identity",
    "nhan vat": "character design",
    "noi that": "interior architecture",
    "nguoi mau": "model fashion editorial",
    "nhieu anh": "multi reference",
    "phan canh": "storyboard cinematic sequence",
    "san pham": "product commerce",
    "so do": "diagram infographic flow",
    "tao anh": "generate text to image",
    "tao moi": "generate text to image",
    "tham chieu": "reference input",
    "thoi trang": "fashion editorial garment",
    "thuong hieu": "brand identity",
    "trang phuc": "outfit garment fashion",
    "ty le": "aspect ratio canvas",
    "ung dung": "app ui",
    "ve": "illustration draw",
    "xoa vat the": "remove object inpaint",
}


def _configure_utf8() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower().replace("-", "") != "utf8" and hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8"))


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    folded = folded.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def expand_query(query: str) -> str:
    normalized = normalize(query)
    expansions = [value for phrase, value in SYNONYMS.items() if phrase in normalized]
    return " ".join([normalized, *expansions]).strip()


def tokenize(text: str) -> list[str]:
    return [token for token in normalize(text).split() if len(token) > 1 and token not in STOPWORDS]


def load_catalog(path: Path = DATA_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError(f"Catalog has no records: {path}")
    return payload


def _as_text(values: Iterable[Any]) -> str:
    return " ".join(str(value) for value in values)


def record_tokens(record: dict[str, Any]) -> list[str]:
    weighted = [
        record.get("title", ""),
        record.get("title", ""),
        record.get("title", ""),
        _as_text(record.get("keywords", [])),
        _as_text(record.get("keywords", [])),
        _as_text(record.get("keywords", [])),
        record.get("domain", ""),
        _as_text(record.get("providers", [])),
        _as_text(record.get("modes", [])),
        record.get("guidance", ""),
        record.get("prompt_shape", ""),
        _as_text(record.get("pitfalls", [])),
    ]
    return tokenize(" ".join(weighted))


class BM25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.lengths = [len(document) for document in documents]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        self.frequencies = [Counter(document) for document in documents]
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(set(document))
        count = len(documents)
        self.idf = {
            token: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def score(self, query_tokens: list[str], index: int) -> float:
        if not query_tokens or not self.documents:
            return 0.0
        frequencies = self.frequencies[index]
        length = self.lengths[index]
        total = 0.0
        for token in query_tokens:
            frequency = frequencies.get(token, 0)
            if not frequency:
                continue
            denominator = frequency + self.k1 * (
                1.0 - self.b + self.b * length / (self.average_length or 1.0)
            )
            total += self.idf[token] * frequency * (self.k1 + 1.0) / denominator
        return total


def _matches_provider(record: dict[str, Any], provider: str | None) -> bool:
    if provider is None:
        return True
    providers = set(record.get("providers", []))
    if provider == "universal":
        return "universal" in providers
    return provider in providers or "universal" in providers


def _matches_mode(record: dict[str, Any], mode: str | None) -> bool:
    return mode is None or mode in set(record.get("modes", []))


def _suggestions(records: list[dict[str, Any]], query: str, limit: int = 6) -> list[str]:
    vocabulary: set[str] = set()
    for record in records:
        vocabulary.update(tokenize(record.get("title", "")))
        vocabulary.update(tokenize(_as_text(record.get("keywords", []))))
    suggestions: list[str] = []
    for token in tokenize(query):
        for match in difflib.get_close_matches(token, sorted(vocabulary), n=2, cutoff=0.72):
            if match not in suggestions:
                suggestions.append(match)
    return suggestions[:limit]


def search_catalog(
    query: str,
    *,
    domain: str | None = None,
    provider: str | None = None,
    mode: str | None = None,
    max_results: int = DEFAULT_RESULTS,
    catalog_path: Path = DATA_FILE,
) -> dict[str, Any]:
    payload = load_catalog(catalog_path)
    all_records = payload["records"]
    records = [
        record
        for record in all_records
        if (domain is None or record.get("domain") == domain)
        and _matches_provider(record, provider)
        and _matches_mode(record, mode)
    ]
    expanded = expand_query(query)
    query_tokens = tokenize(expanded)
    index = BM25([record_tokens(record) for record in records])
    normalized_query = normalize(query)
    ranked: list[tuple[float, float, dict[str, Any]]] = []
    unique_query_tokens = set(query_tokens)

    for position, record in enumerate(records):
        score = index.score(query_tokens, position)
        document_tokens = set(index.documents[position])
        coverage = (
            len(unique_query_tokens.intersection(document_tokens)) / len(unique_query_tokens)
            if unique_query_tokens
            else 0.0
        )
        title = normalize(record.get("title", ""))
        keyword_text = normalize(_as_text(record.get("keywords", [])))
        if normalized_query and normalized_query in title:
            score += 5.0
        elif normalized_query and normalized_query in keyword_text:
            score += 3.0
        title_tokens = set(tokenize(title))
        score += 0.6 * len(title_tokens.intersection(query_tokens))
        if score > 0 and coverage >= 0.15:
            ranked.append((score, coverage, record))

    ranked.sort(key=lambda item: (-item[0], item[2]["id"]))
    relative_floor = ranked[0][0] * 0.2 if ranked else 0.0
    results = []
    for score, coverage, record in ranked:
        if score < max(0.75, relative_floor):
            continue
        item = dict(record)
        item["score"] = round(score, 3)
        item["token_coverage"] = round(coverage, 3)
        results.append(item)
        if len(results) >= max_results:
            break

    return {
        "query": query,
        "expanded_query": expanded,
        "filters": {"domain": domain, "provider": provider, "mode": mode},
        "count": len(results),
        "results": results,
        "suggestions": [] if results else _suggestions(records or all_records, query),
        "catalog_version": payload.get("version"),
        "catalog_file": str(catalog_path),
    }


def format_text(result: dict[str, Any]) -> str:
    filters = ", ".join(
        f"{key}={value}" for key, value in result["filters"].items() if value is not None
    ) or "none"
    lines = [
        "## Image Prompt Guide Search Results",
        f"Query: {result['query']} | Filters: {filters} | Found: {result['count']}",
        "",
    ]
    if not result["results"]:
        lines.append("No catalog match. Retry once with broader terms or an explicit filter.")
        if result["suggestions"]:
            lines.append("Closest known terms: " + ", ".join(result["suggestions"]))
        return "\n".join(lines)

    for number, record in enumerate(result["results"], 1):
        lines.extend(
            [
                f"### Result {number}: {record['title']}",
                f"- ID: {record['id']}",
                f"- Domain: {record['domain']}",
                f"- Providers: {', '.join(record['providers'])}",
                f"- Modes: {', '.join(record['modes'])}",
                f"- Score: {record['score']}",
                f"- Token coverage: {record['token_coverage']}",
                f"- Guidance: {record['guidance']}",
                f"- Prompt shape: {record['prompt_shape']}",
                f"- Pitfalls: {'; '.join(record['pitfalls'])}",
                f"- Source: {record['source']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _catalog_values(records: list[dict[str, Any]], field: str) -> list[str]:
    values: set[str] = set()
    for record in records:
        value = record.get(field)
        if isinstance(value, list):
            values.update(value)
        elif value:
            values.add(str(value))
    return sorted(values)


def main(argv: list[str] | None = None) -> int:
    _configure_utf8()
    try:
        catalog = load_catalog()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error loading catalog: {error}", file=sys.stderr)
        return 1

    records = catalog["records"]
    domains = _catalog_values(records, "domain")
    providers = _catalog_values(records, "providers")
    modes = _catalog_values(records, "modes")

    parser = argparse.ArgumentParser(description="Search bundled image-prompt patterns")
    parser.add_argument("query", nargs="?", help="Two to six terms describing one dominant intent")
    parser.add_argument("--domain", "-d", choices=domains, help="Pattern domain")
    parser.add_argument("--provider", "-p", choices=providers, help="Target provider")
    parser.add_argument("--mode", "-m", choices=modes, help="Generation/edit mode")
    parser.add_argument("--max-results", "-n", type=int, choices=range(1, 21), default=DEFAULT_RESULTS)
    parser.add_argument("--json", action="store_true", help="Emit complete machine-readable JSON")
    parser.add_argument("--list", action="store_true", help="List supported filters and exit")
    args = parser.parse_args(argv)

    if args.list:
        print(json.dumps({"domains": domains, "providers": providers, "modes": modes}, indent=2))
        return 0
    if not args.query:
        parser.error("query is required unless --list is used")

    result = search_catalog(
        args.query,
        domain=args.domain,
        provider=args.provider,
        mode=args.mode,
        max_results=args.max_results,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
