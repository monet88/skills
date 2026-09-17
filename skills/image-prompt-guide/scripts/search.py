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

# A result must match at least half of the query's distinct terms, otherwise a
# single coincidental token turns an unrelated record into a confident hit.
MIN_TOKEN_COVERAGE = 0.5

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "about", "image", "prompt",
    "anh", "cho", "cua", "la", "mot", "nhung", "theo", "toi", "trong",
    "tu", "va", "ve", "voi",
    # Vietnamese function words, so a brief typed in Vietnamese does not
    # dilute the coverage ratio with terms that can never match the catalog.
    "ban", "bang", "cai", "can", "cung", "da", "dang", "day", "duoc", "gi",
    "giup", "hay", "hon", "khong", "kia", "khi", "ma", "minh", "muon",
    "nay", "nhat", "nhu", "nua", "rat", "ra", "roi", "sao", "se", "thi",
    "vao",
}

# Every query is translated to English before matching, because the catalog is
# indexed in English: a Vietnamese, Japanese, or Spanish brief must reach the
# same records an English one reaches. Longest phrases are tried first, so
# "thay background" wins over a bare "nền". Accented and CJK keys match as
# substrings; unaccented keys are matched as whole words.
TRANSLATIONS = {
    # Vietnamese
    "mặc đồ": "wearing outfit",
    "đổi trang phục": "change outfit",
    "đổi trang phục cho": "change outfit for",
    "thay quần áo": "change clothes",
    "trang phục": "outfit clothing",
    "quần áo": "clothes outfit",
    "người mẫu": "model",
    "mẫu": "model",
    "thay background": "replace background",
    "đổi background": "replace background",
    "xóa background": "remove background",
    "thay nền": "replace background",
    "đổi nền": "replace background",
    "xóa nền": "remove background",
    "tách nền": "cutout transparent background",
    "hậu cảnh": "background",
    "nền": "background",
    "trong suốt": "transparent",
    "ghép ảnh": "combine images",
    "ghép người": "compose person",
    "ghép": "combine",
    "phác thảo": "sketch",
    "bản vẽ tay": "hand drawing",
    "bản vẽ": "drawing",
    "áp phích": "poster",
    "poster phim": "movie poster",
    "phim": "film movie",
    "truyện tranh": "comic",
    "bảng nhân vật": "character sheet",
    "nhân vật": "character",
    "tư thế": "pose",
    "biểu cảm": "expression",
    "khuôn mặt": "face",
    "gương mặt": "face",
    "giữ nguyên": "preserve keep",
    "chỉnh sửa": "edit",
    "sửa ảnh": "edit photo",
    "thiết kế": "design",
    "tạo ảnh": "create image",
    "sản phẩm": "product",
    "bao bì": "packaging",
    "thương mại": "commerce",
    "quảng cáo": "advertising",
    "đồ ăn": "food",
    "thức ăn": "food",
    "món ăn": "food dish",
    "nhà hàng": "restaurant",
    "kiến trúc": "architecture",
    "nội thất": "interior",
    "phòng khách": "living room",
    "bất động sản": "real estate",
    "ảnh chân dung": "portrait photograph",
    "chân dung": "portrait",
    "nhiếp ảnh": "photography",
    "máy ảnh": "camera",
    "ánh sáng": "lighting",
    "màu sắc": "color",
    "bố cục": "composition",
    "tiêu đề": "headline title",
    "chữ": "text",
    "văn bản": "text",
    "dòng thời gian": "timeline",
    "biểu đồ": "chart diagram",
    "sơ đồ": "diagram",
    "bản đồ": "map",
    "thông tin": "infographic information",
    "hướng dẫn": "guide instructions",
    "giáo dục": "educational",
    "tài liệu": "document",
    "báo cáo": "report",
    "sách": "book",
    "tạp chí": "magazine",
    "bìa": "cover",
    "nhãn": "label",
    "thương hiệu": "brand",
    "nhận diện thương hiệu": "brand identity",
    "câu chuyện": "story",
    "phân cảnh": "storyboard shot",
    "kịch bản": "storyboard script",
    "hoạt hình": "animation",
    "màu nước": "watercolor",
    "minh họa": "illustration",
    "tranh": "painting artwork",
    "nghệ thuật": "art",
    "tối giản": "minimal",
    "cổ điển": "classical vintage",
    "hoài niệm": "nostalgic",
    "hiện đại": "modern",
    "tương lai": "future",
    "khoa học": "science",
    "kỹ thuật": "technical",
    "y tế": "medical",
    "mô hình": "mockup model",
    "mô phỏng": "mockup",
    "giao diện": "user interface",
    "ứng dụng": "app",
    "trang web": "website",
    "bảng điều khiển": "dashboard",
    "bài trình bày": "presentation slides",
    "phóng to": "upscale",
    "nâng cấp ảnh": "upscale image",
    "phục hồi": "restore",
    "ảnh cũ": "old photo",
    "dịch chữ": "translate text",
    "dịch sang": "translate into",
    "dịch": "translate",
    "phim kinh dị": "horror movie",
    "kinh dị": "horror",
    "kinh di": "horror",
    "sang": "into",
    "trên": "on",
    "dưới": "under",
    "có": "with",
    "của": "of",
    "các": "the",
    "tiếng việt": "vietnamese",
    "tiếng anh": "english",
    "tiếng hàn": "korean",
    "tiếng nhật": "japanese",
    "tiếng trung": "chinese",
    "bản địa hóa": "localization",
    "nhãn dán": "sticker",
    # Other languages: the same domain terms, so the query reaches English
    # records without carrying a language keyword in every catalog entry.
    "背景": "background", "海报": "poster", "产品": "product", "文字": "text",
    "人物": "character", "插画": "illustration", "照片": "photograph", "图片": "picture",
    "换掉": "replace", "替换": "replace", "保留": "keep preserve", "保持": "keep",
    "背景画像": "background", "ポスター": "poster", "製品": "product", "テキスト": "text",
    "キャラクター": "character", "イラスト": "illustration", "写真": "photograph", "画像": "picture",
    "배경": "background", "포스터": "poster", "제품": "product", "텍스트": "text",
    "캐릭터": "character", "일러스트": "illustration", "사진": "photograph", "이미지": "picture",
    "fondo": "background", "cartel": "poster", "producto": "product", "texto": "text",
    "personaje": "character", "ilustración": "illustration", "imagen": "photograph",
    "arrière-plan": "background", "affiche": "poster", "produit": "product", "texte": "text",
    "personnage": "character", "hintergrund": "background", "plakat": "poster",
    "produkt": "product", "figur": "character", "bild": "picture",
    "fundo": "background", "cartaz": "poster", "produto": "product", "personagem": "character",
    "imagem": "photograph", "latar belakang": "background", "gambar": "picture",
    "foto": "photograph", "moda": "fashion", "vêtement": "clothing", "ropa": "clothing",
    "kleidung": "clothing", "pakaian": "clothing", "maniquí": "model", "modelo": "model",
    # Function words from those languages, so they do not dilute coverage.
    "para": "for", "de": "of", "del": "of", "por": "for", "una": "a", "uno": "a",
    "los": "the", "las": "the", "el": "the", "le": "the", "les": "the", "une": "a",
    "des": "the", "du": "of", "der": "the", "das": "the", "und": "and", "mit": "with",
    "ein": "a", "eine": "a", "een": "a", "van": "of", "yang": "the", "untuk": "for",
    "avec": "with", "sur": "on", "dans": "in", "unter": "under", "über": "over",
    "auf": "on", "ang": "the", "mga": "the", "sa": "in", "ng": "the",
}

# ASCII keys are matched as whole words. Anything already a stopword, plus the
# words below, is excluded outright rather than rewritten inside a normal brief.
ENGLISH_WORDS = STOPWORDS | {
    "con", "dan", "des", "die", "do", "he", "is", "it", "may", "me", "mi",
    "mo", "my", "no", "one", "so", "su", "ta", "up", "us", "we",
}


def _translation_pattern() -> re.Pattern[str]:
    parts = []
    for phrase in sorted(TRANSLATIONS, key=lambda item: (-len(item), item)):
        if phrase.isascii() and phrase in ENGLISH_WORDS:
            continue
        escaped = re.escape(phrase)
        # ASCII keys match whole words only; CJK and accented keys match as
        # substrings, which is the only thing that works without spacing.
        parts.append(rf"\b{escaped}\b" if phrase.isascii() else escaped)
    return re.compile("|".join(parts))


_PATTERN = _translation_pattern()


def translate_query(text: str) -> str:
    """Rewrite any query into English before it is matched against the catalog."""
    lowered = re.sub(r"\s+", " ", text.strip().lower())
    return normalize(_PATTERN.sub(lambda match: f" {TRANSLATIONS[match.group(0)]} ", lowered))


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


def record_identity_tokens(record: dict[str, Any]) -> set[str]:
    """Only the fields that say what the record is about, not its prose body.

    Coverage must measure intent overlap, otherwise a guide sentence that
    happens to share a verb with the query promotes an unrelated pattern.
    """
    identity = [
        record.get("title", ""),
        _as_text(record.get("keywords", [])),
        record.get("domain", ""),
        _as_text(record.get("providers", [])),
        _as_text(record.get("modes", [])),
    ]
    return set(tokenize(" ".join(identity)))


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
    english_query = translate_query(query)
    query_tokens = tokenize(english_query)
    index = BM25([record_tokens(record) for record in records])
    normalized_query = english_query
    ranked: list[tuple[float, float, dict[str, Any]]] = []
    unique_query_tokens = set(query_tokens)

    for position, record in enumerate(records):
        score = index.score(query_tokens, position)
        identity_tokens = record_identity_tokens(record)
        title = normalize(record.get("title", ""))
        keyword_text = normalize(_as_text(record.get("keywords", [])))
        if normalized_query and normalized_query in title:
            score += 5.0
        elif normalized_query and normalized_query in keyword_text:
            score += 3.0
        title_tokens = set(tokenize(title))
        coverage = (
            len(unique_query_tokens.intersection(identity_tokens)) / len(unique_query_tokens)
            if unique_query_tokens
            else 0.0
        )
        score += 0.6 * len(unique_query_tokens.intersection(title_tokens))
        # A provider or mode filter is an explicit intent, and the provider or
        # mode name itself is near-worthless in BM25 (most records list it in
        # their providers/modes arrays). Prefer the record that *is* that axis.
        if provider and record.get("domain") == "provider":
            score += 2.0
        if mode and record.get("domain") == "mode":
            score += 2.0
        if score > 0 and coverage >= MIN_TOKEN_COVERAGE:
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
        "query_used": english_query,
        "filters": {"domain": domain, "provider": provider, "mode": mode},
        "count": len(results),
        "results": results,
        "suggestions": [] if results else _suggestions(records or all_records, english_query),
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
    if result.get("query_used") and result["query_used"] != normalize(result["query"]):
        lines.insert(2, f"English query: {result['query_used']}")
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
