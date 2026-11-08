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

GLOSSARY_PLACEHOLDERS = [
    "{language}",
    "{fields}",
    "{gender_instruction}",
    "{entries}",
]

# Current Glossarion expands these to default full-name splitting or Korean-to-English
# example rows. Do not silently include them in a Vietnamese canonical-identity pack.
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

HANVIET_GUARDRAILS = [
    "D\u1ecbch 100% H\u00e1n-Vi\u1ec7t",
    "D\u01b0-min",
    "Th\u1ee7y-ryun",
]

# One concise coverage check suffices. Do not require long overlapping
# residue/metadata checklists in a translation model's System Prompt.
LANGUAGE_COVERAGE_GUARDRAILS = [
    "source-to-output coverage pass",
]


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


def check_profile(system_text: str, errors: list[str], allow_long: bool) -> None:
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
        errors.append(f"{name}: embedded NOVEL_PROFILE too short ({len(words)} words); expected about 60-240 words")
    if len(words) > 240 and not allow_long:
        errors.append(
            f"{name}: embedded NOVEL_PROFILE too long ({len(words)} words); keep at or below 240 or rerun with "
            "--allow-long-profile only for a justified exception"
        )


def check_system(text: str, errors: list[str], require_hanviet: bool, allow_long_profile: bool) -> None:
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

    check_profile(text, errors, allow_long_profile)

    require_substrings(text, LANGUAGE_COVERAGE_GUARDRAILS, name, "single coverage guardrail", errors)
    if not re.search(r"(?i)\b(?:Vietnamese|target language)\b", text):
        errors.append(f"{name}: must declare reader-facing target language")
    if not re.search(r"(?i)\bglossary\b", text):
        errors.append(f"{name}: must use supplied canonical glossary names")
    if text.count("source-to-output coverage pass") != 1:
        errors.append(f"{name}: use one concise coverage check, not multiple repeated passes")
    if re.search(r"(?i)\b(?:EPUB|TXT)\b", text):
        errors.append(f"{name}: EPUB/TXT source-file selection belongs to preparation/runtime, not System Prompt")
    if re.search(r"(?i)\b(?:CHAPTER_RANGE|BATCH_SIZE|GLOSSARY_REQUIRE_COMPLETE_BEFORE_TRANSLATION)\b", text):
        errors.append(f"{name}: Glossarion batch/settings variables belong to runtime")

    if require_hanviet:
        if "Hán-Việt" not in text:
            errors.append(f"{name}: Vietnamese Murim/wuxia must use Hán-Việt canonical names")


def check_glossary(text: str, errors: list[str], require_hanviet: bool, require_murim_wuxia: bool) -> None:
    name = "glossary_extract_prompt.md"
    check_plain_prompt(text, name, errors)
    check_order(text, GLOSSARY_REQUIRED, name, errors)
    lines = nonempty_lines(text)
    if not lines or not lines[0].startswith("You are a glossary extraction assistant specialized in "):
        errors.append(
            f"{name}: first non-empty line must begin with "
            "'You are a glossary extraction assistant specialized in '"
        )

    for placeholder in GLOSSARY_PLACEHOLDERS:
        if placeholder not in text:
            errors.append(f"{name}: missing literal placeholder {placeholder}")
    for placeholder in ("{fields}", "{gender_instruction}", "{entries}", "{description_mandatory}", "{description_detailed}"):
        if text.count(placeholder) > 1:
            errors.append(f"{name}: {placeholder} must occur at most once; Glossarion expands it into a multi-line instruction")
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

    if require_hanviet:
        require_substrings(text, HANVIET_GUARDRAILS, name, "strict Han-Viet glossary guardrail", errors)
        if "normal spaces" not in text:
            errors.append(f"{name}: Han-Viet branch must require normal spaces")
        if "project-local" not in text and "project localization" not in text:
            errors.append(f"{name}: Han-Viet extractor must allow conservative project-local names when original characters are unavailable")

    if require_murim_wuxia:
        require_substrings(
            text,
            ["sect", "clan", "internal", "external", "footwork", "lightness"],
            name,
            "Murim/wuxia terminology classification",
            errors,
        )


def check_refinement(text: str, errors: list[str], require_hanviet: bool, require_murim_wuxia: bool) -> None:
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

    if require_hanviet:
        require_substrings(text, HANVIET_GUARDRAILS, name, "strict Han-Viet refinement guardrail", errors)
        if not re.search(r"(?i)do not invent .*Hanja|do not invent .*Hanzi", text):
            errors.append(f"{name}: Han-Viet refinement must forbid inventing unsupported Hanja/Hanzi")

    if require_murim_wuxia:
        require_substrings(
            text,
            ["sect", "clan", "forms of address", "internal", "external", "footwork", "lightness"],
            name,
            "Murim/wuxia refinement terminology policy",
            errors,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_dir", type=Path, help="Directory containing the prompt pack")
    parser.add_argument("--allow-long-profile", action="store_true")
    parser.add_argument(
        "--require-refinement",
        action="store_true",
        help="Require glossary_refinement_user_prompt.md when refinement was explicitly requested",
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

    require_hanviet = bool(
        re.search(r"(?i)\b(?:murim|wuxia|xianxia|xuanhuan)\b|v\u00f5 hi\u1ec7p|ti\u00ean hi\u1ec7p|huy\u1ec1n huy\u1ec5n", genre_identity)
        and re.search(r"(?i)Vietnamese|H\u00e1n-Vi\u1ec7t", vietnamese_identity)
    )
    require_murim_wuxia = bool(re.search(r"(?i)\b(?:murim|wuxia)\b|v\u00f5 hi\u1ec7p", genre_identity))

    if system:
        check_system(system, errors, require_hanviet, args.allow_long_profile)
    if glossary:
        check_glossary(glossary, errors, require_hanviet, require_murim_wuxia)
    if refinement:
        check_refinement(refinement, errors, require_hanviet, require_murim_wuxia)

    if errors:
        print("FORMAT VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("FORMAT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
