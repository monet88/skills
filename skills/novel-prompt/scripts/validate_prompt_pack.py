#!/usr/bin/env python3
"""Validate Novel Prompt output: two required prompts plus optional refinement."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SYSTEM_REQUIRED = [
    "TASK",
    "STYLE",
    "CHARACTER VOICE AND PRONOUNS",
    "GENRE TERMINOLOGY",
    "MULTILINGUAL SOURCE FRAGMENTS",
    "NAMES AND PROPER NOUNS",
    "IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA",
    "HTML AND PUNCTUATION",
    "SOURCE FIDELITY AND CONTEXT PRIORITY",
    "FINAL CHECK",
]
SYSTEM_OPTIONAL = ["COMBAT / POWER SYSTEM / TECHNICAL CLARITY"]

PROFILE_REQUIRED = [
    "Genre:",
    "Setting:",
    "Translation Style:",
    "Narrative Voice:",
    "Dialogue Style:",
    "Worldbuilding / Hierarchy Priorities:",
    "Naming Conventions:",
    "Pronoun / Address Conventions:",
    "Avoid:",
]
PROFILE_OPTIONAL = ["Title:", "Power-System Treatment:"]

GLOSSARY_REQUIRED = [
    "OUTPUT FORMAT",
    "TRANSLATION REQUIREMENTS",
    "ACTIVE ENTRY TYPES",
    "GENRE-SPECIFIC CLASSIFICATION",
    "CHARACTERS / NAMES / TITLES / RANKS / ADDRESS",
    "POWER SYSTEM / TECHNIQUES / ITEMS / ORGANIZATIONS",
    "TRANSLATION_MODE / SUBTYPE / ALIASES / DESCRIPTION",
    "EXISTING CANON AND DEDUPLICATION",
    "HARD REJECTION RULES",
    "COMPLETION CHECK",
]

GLOSSARY_BASE_PLACEHOLDERS = (
    "{language}",
    "{gender_instruction}",
    "{entries}",
)

SINGLE_OCCURRENCE_PLACEHOLDERS = (
    "{fields}",
    "{fields1}",
    "{gender_instruction}",
    "{entries}",
    "{description_mandatory}",
    "{description_detailed}",
    "{subject_tracking_instruction}",
    "{relations_instruction}",
)

# Current Glossarion expands these to surname/given-name splitting or Korean-to-English
# example rows. Do not include them in Vietnamese full-identity packs.
GLOSSARY_NAME_SPLIT_PLACEHOLDERS = ("{description_name_split_example}", "{name_split_example}")
GLOSSARY_STOCK_EXAMPLE_PLACEHOLDERS = ("{description_example}", "{example}")

REFINEMENT_REQUIRED = [
    "PROJECT-SPECIFIC REFINEMENT POLICY",
    "IDENTITY AND CANON",
    "NAMING / LOCALIZATION",
    "CHARACTERS / TITLES / RANKS / ADDRESS",
    "TERMINOLOGY / HIERARCHY / ENTITY DISTINCTIONS",
    "CONFLICT RESOLUTION",
    "FINAL PROJECT CHECK",
]

# Detect leftover template instruction brackets without flagging legitimate prose brackets
# such as [心像比武], [Hệ Thống], [Modifier Hán-Việt], or [Đang chờ xác định].
UNFILLED_TEMPLATE_RE = re.compile(
    r"\[(?:"
    r"detected genre[^\]\n]*"
    r"|when known"
    r"|target-language"
    r"|Genre supported by source"
    r"|Observed [^\]\n]+"
    r"|Book-specific [^\]\n]+"
    r"|POV, narrator [^\]\n]+"
    r"|Key social, [^\]\n]+"
    r"|Naming Mode \+ [^\]\n]+"
    r"|1–3 concrete [^\]\n]+"
    r"|Optional\s*[—:-][^\]\n]+"
    r"|One concise [^\]\n]+"
    r"|One (?:short|book-specific|or two) [^\]\n]+"
    r"|Only [^\]\n]{5,}"
    r"|Populate [^\]\n]+"
    r"|Insert exact [^\]\n]+"
    r"|Insert the project [^\]\n]+"
    r"|Apply the [^\]\n]+"
    r"|For (?:Sino-origin|Sino-Vietnamese|modern Korean|Vietnamese|Korean|other) [^\]\n]+:[^\]\n]*"
    r"|Standard CSV [^\]\n]+"
    r"|Add (?:genre-supported|only supported) [^\]\n]+"
    r"|Conditional behavior [^\]\n]+"
    r"|Reject complete [^\]\n]+"
    r"|Verify every row [^\]\n]+"
    r"|State (?:original-language|the detected) [^\]\n]+"
    r"|Preserve the project's [^\]\n]+"
    r"|Relevant [^\]\n]+"
    r"|Viewpoint and narration"
    r")\]"
)

LOCAL_LEAK_RE = re.compile(
    r"(?:(?<![A-Za-z])[A-Z]:\\[^\s\"'`]+|"
    r"\bglossarion\s+(?:novel|glossary|config|qa|epub|manga)\b|"
    r"\b(?:translation_progress|glossary_progress|validation_results)\.json\b|"
    r"\bvalidate_prompt_pack\.py\b)"
)

SINO_GENRE_RE = re.compile(
    r"(?i)\b(?:murim|wuxia|xianxia|xuanhuan)\b|"
    r"v\u00f5 hi\u1ec7p|ti\u00ean hi\u1ec7p|huy\u1ec1n huy\u1ec5n|linh d\u1ecb"
)

MURIM_WUXIA_RE = re.compile(r"(?i)\b(?:murim|wuxia)\b|v\u00f5 hi\u1ec7p")

HYBRID_WORLD_HV_RE = re.compile(
    r"(?i)(?:personal names?[^.\n]{0,80}(?:romaja|romanized|keep|stay|preserve))"
    r"|(?:(?:keep|stay|preserve)[^.\n]{0,50}personal names?[^.\n]{0,40}(?:romaja|romanized))"
    r"|(?:never\s+h\u00e1n-vi\u1ec7t-?ize[^.\n]{0,40}personal)"
    r"|(?:non-person[^.\n]{0,50}h\u00e1n-vi\u1ec7t)"
)

MURIM_CATEGORY_GROUPS = (
    ("sect / môn phái", re.compile(r"(?i)\bsect\b|m\u00f4n ph\u00e1i|\bph\u00e1i\b")),
    ("clan / gia tộc", re.compile(r"(?i)\bclan\b|gia t\u1ed9c|th\u1ebf gia")),
    ("internal / nội công", re.compile(r"(?i)\binternal\b|n\u1ed9i c\u00f4ng|n\u1ed9i l\u1ef1c")),
    ("external / ngoại công", re.compile(r"(?i)\bexternal\b|ngo\u1ea1i c\u00f4ng")),
    ("footwork / bộ pháp", re.compile(r"(?i)\bfootwork\b|b\u1ed9 ph\u00e1p|th\u00e2n ph\u00e1p")),
    ("lightness / khinh công", re.compile(r"(?i)\blightness\b|khinh c\u00f4ng")),
)


def read_text(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.name}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{path.name}: must be UTF-8 text")
        return ""


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def check_plain_prompt(text: str, name: str, errors: list[str]) -> None:
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            errors.append(f"{name}: Markdown heading is not allowed: {stripped!r}")
        if stripped.startswith("```"):
            errors.append(f"{name}: Markdown code fence is not allowed")
    stub = UNFILLED_TEMPLATE_RE.search(text)
    if stub:
        errors.append(f"{name}: unfilled template placeholder found: {stub.group(0)!r}")
    leak = LOCAL_LEAK_RE.search(text)
    if leak:
        errors.append(f"{name}: local path, CLI command, or runtime artifact leaked into prompt: {leak.group(0)!r}")


def line_positions(text: str, labels: list[str]) -> dict[str, int]:
    positions: dict[str, int] = {}
    lines = text.splitlines()
    for label in labels:
        for i, line in enumerate(lines):
            if line.strip() == label:
                positions[label] = i
                break
    return positions


def check_order(text: str, labels: list[str], name: str, errors: list[str]) -> None:
    positions = line_positions(text, labels)
    for label in labels:
        if label not in positions:
            errors.append(f"{name}: missing required section/field {label!r}")
    present = [label for label in labels if label in positions]
    indexes = [positions[label] for label in present]
    if indexes != sorted(indexes):
        errors.append(f"{name}: required sections/fields are out of template order")


def require_substrings(text: str, needles: list[str], name: str, purpose: str, errors: list[str]) -> None:
    for needle in needles:
        if needle not in text:
            errors.append(f"{name}: missing {purpose} containing {needle!r}")


def extract_profile(text: str) -> str:
    match = re.search(r"<NOVEL_PROFILE>\s*(.*?)\s*</NOVEL_PROFILE>", text, flags=re.S)
    return match.group(1) if match else ""


def extract_section(text: str, heading: str, next_headings: list[str]) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        return ""
    stop_set = set(next_headings)
    out = []
    for line in lines[start:]:
        if line.strip() in stop_set:
            break
        out.append(line)
    return "\n".join(out).strip()


def detect_naming_mode(
    requested_mode: str,
    genre_identity: str,
    vietnamese_identity: str,
    system_text: str,
    glossary_text: str,
) -> str:
    if requested_mode != "auto":
        return requested_mode
    is_sino_vn = bool(
        SINO_GENRE_RE.search(genre_identity)
        and re.search(r"(?i)Vietnamese|H\u00e1n-Vi\u1ec7t", vietnamese_identity)
    )
    if not is_sino_vn:
        return "preserve"
    combined = system_text + "\n" + glossary_text
    if HYBRID_WORLD_HV_RE.search(combined):
        return "hybrid-world-hv"
    return "full-han-viet"


def check_profile(system_text: str, errors: list[str], allow_long: bool, max_words: int) -> None:
    name = "system_prompt.md"
    if system_text.count("<NOVEL_PROFILE>") != 1 or system_text.count("</NOVEL_PROFILE>") != 1:
        errors.append(f"{name}: NOVEL_PROFILE wrapper must appear exactly once")
        return

    positions = line_positions(
        system_text,
        ["SOURCE FIDELITY AND CONTEXT PRIORITY", "<NOVEL_PROFILE>", "</NOVEL_PROFILE>", "FINAL CHECK"],
    )
    required = ["SOURCE FIDELITY AND CONTEXT PRIORITY", "<NOVEL_PROFILE>", "</NOVEL_PROFILE>", "FINAL CHECK"]
    if all(label in positions for label in required):
        if not (
            positions["SOURCE FIDELITY AND CONTEXT PRIORITY"]
            < positions["<NOVEL_PROFILE>"]
            < positions["</NOVEL_PROFILE>"]
            < positions["FINAL CHECK"]
        ):
            errors.append(f"{name}: NOVEL_PROFILE must appear after context priority and before FINAL CHECK")

    body = extract_profile(system_text)
    if not body:
        errors.append(f"{name}: NOVEL_PROFILE body is empty or malformed")
        return

    check_order(body, PROFILE_REQUIRED, name, errors)
    positions = line_positions(body, PROFILE_REQUIRED + PROFILE_OPTIONAL)
    canonical = [
        "Title:",
        "Genre:",
        "Setting:",
        "Translation Style:",
        "Narrative Voice:",
        "Dialogue Style:",
        "Worldbuilding / Hierarchy Priorities:",
        "Naming Conventions:",
        "Pronoun / Address Conventions:",
        "Power-System Treatment:",
        "Avoid:",
    ]
    present = [label for label in canonical if label in positions]
    indexes = [positions[label] for label in present]
    if indexes != sorted(indexes):
        errors.append(f"{name}: NOVEL_PROFILE fields are out of template order")

    words = re.findall(r"\S+", body)
    if len(words) < 60:
        errors.append(f"{name}: embedded NOVEL_PROFILE too short ({len(words)} words); expected 60-{max_words} words")
    if len(words) > max_words and not allow_long:
        errors.append(
            f"{name}: embedded NOVEL_PROFILE too long ({len(words)} words); keep at or below {max_words} or rerun with "
            "--allow-long-profile only for a justified exception"
        )


def check_system(
    text: str,
    errors: list[str],
    naming_mode: str,
    allow_long_profile: bool,
    max_profile_words: int,
) -> None:
    name = "system_prompt.md"
    check_plain_prompt(text, name, errors)
    check_order(text, SYSTEM_REQUIRED, name, errors)

    positions = line_positions(text, SYSTEM_REQUIRED + SYSTEM_OPTIONAL)
    optional = SYSTEM_OPTIONAL[0]
    if optional in positions:
        before = positions.get("NAMES AND PROPER NOUNS", -1)
        after = positions.get("IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA", 10**9)
        if not before < positions[optional] < after:
            errors.append(f"{name}: optional COMBAT section is in the wrong template position")

    split = "{split_marker_instruction}"
    if text.count(split) != 1:
        errors.append(f"{name}: {split} must appear exactly once")
    lines = nonempty_lines(text)
    if lines and lines[-1] != split:
        errors.append(f"{name}: {split} must be the final non-empty line")
    if not lines or not lines[0].startswith("You are "):
        errors.append(f"{name}: first non-empty line must begin with 'You are '")

    check_profile(text, errors, allow_long_profile, max_profile_words)

    require_substrings(text, ["source-to-output coverage pass"], name, "single coverage guardrail", errors)
    if not re.search(r"(?i)\b(?:Vietnamese|target language)\b", text):
        errors.append(f"{name}: must declare reader-facing target language")
    if not re.search(r"(?i)\bglossary\b", text):
        errors.append(f"{name}: must use supplied canonical glossary names")
    if text.count("source-to-output coverage pass") > 1:
        errors.append(f"{name}: use one concise coverage check, not multiple repeated passes")
    if re.search(r"(?i)\b(?:EPUB|TXT)\b", text):
        errors.append(f"{name}: EPUB/TXT source-file selection belongs to preparation/runtime, not System Prompt")
    if re.search(r"(?i)\b(?:CHAPTER_RANGE|BATCH_SIZE|GLOSSARY_REQUIRE_COMPLETE_BEFORE_TRANSLATION)\b", text):
        errors.append(f"{name}: Glossarion batch/settings variables belong to runtime")

    html_section = extract_section(text, "HTML AND PUNCTUATION", SYSTEM_REQUIRED + SYSTEM_OPTIONAL)
    if not re.search(r"(?i)\bHTML\b|\btag", html_section):
        errors.append(f"{name}: HTML AND PUNCTUATION section must instruct preserving HTML tags/structure")

    if naming_mode in ("full-han-viet", "hybrid-world-hv"):
        if "Hán-Việt" not in text:
            errors.append(f"{name}: Sino-Vietnamese ({naming_mode}) prompt must specify Hán-Việt canonical names")


def check_glossary(
    text: str,
    errors: list[str],
    naming_mode: str,
    require_murim_wuxia: bool,
    require_relations: bool,
) -> None:
    name = "glossary_extract_prompt.md"
    check_plain_prompt(text, name, errors)
    check_order(text, GLOSSARY_REQUIRED, name, errors)
    lines = nonempty_lines(text)
    if not lines or not lines[0].startswith("You are a glossary extraction assistant specialized in "):
        errors.append(
            f"{name}: first non-empty line must begin with "
            "'You are a glossary extraction assistant specialized in '"
        )

    for placeholder in GLOSSARY_BASE_PLACEHOLDERS:
        if placeholder not in text:
            errors.append(f"{name}: missing literal placeholder {placeholder}")

    has_fields = "{fields}" in text
    has_fields1 = "{fields1}" in text
    if not has_fields and not has_fields1:
        errors.append(f"{name}: missing literal schema placeholder {{fields}} (or {{fields1}})")
    if has_fields and has_fields1:
        errors.append(f"{name}: cannot mix {{fields}} (CSV) and {{fields1}} (Unit Separator) in one prompt")

    for placeholder in SINGLE_OCCURRENCE_PLACEHOLDERS:
        if text.count(placeholder) > 1:
            errors.append(
                f"{name}: {placeholder} must occur at most once; Glossarion expands it into a multi-line instruction"
            )

    if require_relations and "{relations_instruction}" not in text:
        errors.append(f"{name}: missing literal placeholder {{relations_instruction}} (--require-relations)")

    if "{relations_instruction}" in text:
        if re.search(r"(?i)relationships?\s+only\s+in\s+(?:an\s+active\s+)?description", text):
            errors.append(
                f"{name}: restricts relationships exclusively to 'description', contradicting {{relations_instruction}}"
            )

    if "full" in text.lower() and "canonical" in text.lower():
        for placeholder in GLOSSARY_NAME_SPLIT_PLACEHOLDERS:
            if placeholder in text:
                errors.append(
                    f"{name}: {placeholder} expands to surname/given-name splitting and "
                    "contradicts the canonical full-name policy"
                )
    for placeholder in GLOSSARY_STOCK_EXAMPLE_PLACEHOLDERS:
        if placeholder in text:
            errors.append(
                f"{name}: {placeholder} expands to fixed Korean-to-English example rows; "
                "omit it unless the runtime example actually matches the target genre/language"
            )

    if "The columns must appear in exactly this order:" not in text:
        errors.append(f"{name}: missing exact dynamic-column ordering instruction")
    if "Do not output anything except the CSV." not in text:
        errors.append(f"{name}: missing final CSV-only instruction")

    require_substrings(
        text,
        [
            "Resolve canonical character identity before assigning gender",
            "Output at most one character row per canonical identity",
            "conflicting gender",
            "{gender_instruction}",
            "homonymous",
            "full",
            "forms of address",
        ],
        name,
        "identity/gender/address guardrail",
        errors,
    )

    if naming_mode in ("full-han-viet", "hybrid-world-hv"):
        if "Hán-Việt" not in text:
            errors.append(f"{name}: Sino-Vietnamese ({naming_mode}) extractor must specify Hán-Việt localization")
        if not re.search(
            r"(?i)100%\s*H\u00e1n-Vi\u1ec7t|complete\s+H\u00e1n-Vi\u1ec7t|mixed|partial|half-localized|half-H\u00e1n",
            text,
        ):
            errors.append(f"{name}: Sino-Vietnamese extractor must enforce complete Hán-Việt (no mixed/partial forms)")
        if not re.search(r"(?i)normal spaces?", text):
            errors.append(f"{name}: Sino-Vietnamese extractor must require normal spaces between localized components")
        if not re.search(r"(?i)project-local|project localization", text):
            errors.append(
                f"{name}: Sino-Vietnamese extractor must allow conservative project-local names when Hanja/Hanzi is absent"
            )

    if require_murim_wuxia:
        matched = sum(1 for _, pattern in MURIM_CATEGORY_GROUPS if pattern.search(text))
        if matched < 4:
            missing_labels = [label for label, pattern in MURIM_CATEGORY_GROUPS if not pattern.search(text)]
            errors.append(
                f"{name}: Murim/wuxia terminology classification is incomplete; missing distinctions such as: "
                + ", ".join(missing_labels)
            )


def check_refinement(
    text: str,
    errors: list[str],
    naming_mode: str,
    require_murim_wuxia: bool,
) -> None:
    name = "glossary_refinement_user_prompt.md"
    check_plain_prompt(text, name, errors)
    check_order(text, REFINEMENT_REQUIRED, name, errors)
    lines = nonempty_lines(text)
    if not lines or not lines[0].startswith("Apply the following project-specific glossary refinement rules for "):
        errors.append(
            f"{name}: first non-empty line must begin with "
            "'Apply the following project-specific glossary refinement rules for '"
        )
    if "{entries}" not in text:
        errors.append(f"{name}: missing literal placeholder {{entries}}")
    if text.count("{entries}") > 1:
        errors.append(f"{name}: {{entries}} must occur at most once")

    final_line = "Refine conservatively. Correct only what can be supported by the supplied glossary data."
    if not lines or lines[-1] != final_line:
        errors.append(f"{name}: final non-empty line must be {final_line!r}")

    forbidden_format_contracts = [
        "Return ONLY valid CSV",
        "The columns must appear in exactly this order:",
        "Do not include a header row",
        "using the columns and delimiter",
    ]
    for phrase in forbidden_format_contracts:
        if phrase in text:
            errors.append(
                f"{name}: generic refinement System-Prompt format contract leaked into User Prompt: {phrase!r}"
            )

    require_substrings(
        text,
        [
            "canonical identity",
            "full personal name",
            "homonym",
            "gender",
            "forms of address",
            "invent new entities",
        ],
        name,
        "refinement semantic guardrail",
        errors,
    )

    if naming_mode in ("full-han-viet", "hybrid-world-hv"):
        if "Hán-Việt" not in text:
            errors.append(f"{name}: Sino-Vietnamese ({naming_mode}) refinement must specify Hán-Việt policy")
        if not re.search(
            r"(?i)(?:do not|never)\s+(?:invent|fabricate)[^.\n]*(?:Hanja|Hanzi)",
            text,
        ):
            errors.append(f"{name}: Sino-Vietnamese refinement must forbid inventing unsupported Hanja/Hanzi")

    if require_murim_wuxia:
        matched = sum(1 for _, pattern in MURIM_CATEGORY_GROUPS if pattern.search(text))
        if matched < 4:
            errors.append(f"{name}: Murim/wuxia refinement terminology policy is incomplete")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Glossarion prompt pack.")
    parser.add_argument("pack_dir", type=Path, help="Directory containing the prompt pack")
    parser.add_argument("--allow-long-profile", action="store_true", help="Bypass max NOVEL_PROFILE word count")
    parser.add_argument(
        "--max-profile-words",
        type=int,
        default=400,
        help="Maximum allowed word count for embedded NOVEL_PROFILE (default: 400)",
    )
    parser.add_argument(
        "--naming-mode",
        choices=("auto", "full-han-viet", "hybrid-world-hv", "preserve"),
        default="auto",
        help="Override Hán-Việt naming policy validation mode (default: auto)",
    )
    parser.add_argument(
        "--require-refinement",
        action="store_true",
        help="Require glossary_refinement_user_prompt.md when refinement was explicitly requested",
    )
    parser.add_argument(
        "--require-relations",
        action="store_true",
        help="Require {relations_instruction} placeholder in glossary_extract_prompt.md",
    )
    args = parser.parse_args()

    errors: list[str] = []
    if (args.pack_dir / "assistant_prompt.md").exists():
        errors.append("assistant_prompt.md: obsolete output; merge NOVEL_PROFILE into system_prompt.md and remove this file")

    system = read_text(args.pack_dir / "system_prompt.md", errors)
    glossary = read_text(args.pack_dir / "glossary_extract_prompt.md", errors)
    refinement_path = args.pack_dir / "glossary_refinement_user_prompt.md"
    if args.require_refinement and not refinement_path.is_file():
        errors.append("missing file: glossary_refinement_user_prompt.md")
    refinement = read_text(refinement_path, errors) if refinement_path.is_file() else ""

    system_first = nonempty_lines(system)[0] if nonempty_lines(system) else ""
    glossary_first = nonempty_lines(glossary)[0] if nonempty_lines(glossary) else ""
    refinement_first = nonempty_lines(refinement)[0] if nonempty_lines(refinement) else ""
    profile = extract_profile(system)
    genre_match = re.search(
        r"Genre:\s*(.*?)(?=\n(?:Setting:|Translation Style:|Narrative Voice:|Dialogue Style:|Worldbuilding / Hierarchy Priorities:|Naming Conventions:|Pronoun / Address Conventions:|Power-System Treatment:|Avoid:)|\Z)",
        profile,
        flags=re.S,
    )
    profile_genre = genre_match.group(1) if genre_match else ""
    genre_identity = "\n".join([system_first, glossary_first, refinement_first, profile_genre])
    vietnamese_identity = system_first + "\n" + profile_genre + "\n" + refinement_first

    naming_mode = detect_naming_mode(args.naming_mode, genre_identity, vietnamese_identity, system, glossary)
    require_murim_wuxia = bool(MURIM_WUXIA_RE.search(genre_identity))

    if system:
        check_system(system, errors, naming_mode, args.allow_long_profile, args.max_profile_words)
    if glossary:
        check_glossary(glossary, errors, naming_mode, require_murim_wuxia, args.require_relations)
    if refinement:
        check_refinement(refinement, errors, naming_mode, require_murim_wuxia)

    if errors:
        print("FORMAT VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("FORMAT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
