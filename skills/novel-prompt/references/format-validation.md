# Prompt Pack Format Validation

Mandatory mechanical and semantic contract before delivering a prompt pack. Synchronized 1-to-1 with `scripts/validate_prompt_pack.py`.

## 1. General Rules

- Default output: `system_prompt.md` + `glossary_extract_prompt.md`. Generate `glossary_refinement_user_prompt.md` **only** on explicit request. Never output `assistant_prompt.md`.
- Plain ready-to-paste text only: no Markdown `#` headings, no code fences, no commentary, no unfilled `[...]` skeleton placeholders.
- Preserve exact uppercase section labels and template order from `references/prompt-templates.md` without subtitles or parentheticals.

## 2. `system_prompt.md`

**Required section order:**
1. Role line starting with `You are `
2. `TASK`
3. `STYLE`
4. `CHARACTER VOICE AND PRONOUNS`
5. `GENRE TERMINOLOGY`
6. `MULTILINGUAL SOURCE FRAGMENTS`
7. `NAMES AND PROPER NOUNS`
8. `COMBAT / POWER SYSTEM / TECHNICAL CLARITY` *(optional)*
9. `IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA`
10. `HTML AND PUNCTUATION`
11. `SOURCE FIDELITY AND CONTEXT PRIORITY`
12. `<NOVEL_PROFILE>` … `</NOVEL_PROFILE>` *(exactly once)*
13. `FINAL CHECK`
14. `{split_marker_instruction}` *(literal, exactly once, final non-empty line)*

**`<NOVEL_PROFILE>` field order (60–400 words default; `--allow-long-profile` for justified exceptions):**
`Title:` *(optional)* → `Genre:` → `Setting:` → `Translation Style:` → `Narrative Voice:` → `Dialogue Style:` → `Worldbuilding / Hierarchy Priorities:` → `Naming Conventions:` → `Pronoun / Address Conventions:` → `Power-System Treatment:` *(optional)* → `Avoid:`.

**Content gates:**
- Declares reader-facing target language (Vietnamese by default) and supplied glossary authority.
- Contains **exactly one** `source-to-output coverage pass` under `FINAL CHECK`.
- Preserves HTML tags and 1-to-1 `<p>` paragraph structure under `HTML AND PUNCTUATION`.
- Zero operational/runtime leaks (`EPUB`, `TXT`, `CHAPTER_RANGE`, `BATCH_SIZE`, local paths like `D:\...`, `glossarion` CLI commands, `*_progress.json`).
- Generic sections outside `<NOVEL_PROFILE>` contain no book-specific character/plot dumps.
- Bidirectional scene-local `xưng hô` without frozen pronoun pairs; sense-first Vietnamese craft.

## 3. `glossary_extract_prompt.md`

**Required section order:**
1. Role line starting with `You are a glossary extraction assistant specialized in `
2. `OUTPUT FORMAT`
3. `TRANSLATION REQUIREMENTS`
4. `ACTIVE ENTRY TYPES`
5. `GENRE-SPECIFIC CLASSIFICATION`
6. `CHARACTERS / NAMES / TITLES / RANKS / ADDRESS`
7. `POWER SYSTEM / TECHNIQUES / ITEMS / ORGANIZATIONS`
8. `TRANSLATION_MODE / SUBTYPE / ALIASES / DESCRIPTION`
9. `EXISTING CANON AND DEDUPLICATION`
10. `HARD REJECTION RULES`
11. `COMPLETION CHECK`
12. Final line: `Do not output anything except the CSV.`

**Placeholder & schema gates:**
- Must include literal `{language}`, `{fields}` (or `{fields1}`, never both), `{gender_instruction}`, `{entries}`.
- Recommended Glossarion `v9.15.19+` placeholders: `{subject_tracking_instruction}`, `{relations_instruction}`, plus `{description_mandatory}`, `{description_in_language}`, `{description_detailed}`.
- Multi-line/line-owning placeholders (`{fields}`, `{fields1}`, `{gender_instruction}`, `{entries}`, `{description_mandatory}`, `{description_detailed}`, `{subject_tracking_instruction}`, `{relations_instruction}`) must each appear **at most once**.
- Forbidden: `{name_split_example}`, `{description_name_split_example}` (conflicts with full-name identity), `{example}`, `{description_example}` (hardcoded Korean-to-English rows).
- Must contain `The columns must appear in exactly this order:`.
- Must enforce: identity before gender, at most one row per canonical identity, conflicting-gender handling, distinct homonyms, full personal names unsplit, reusable forms of address.
- When `{relations_instruction}` is present, do not contradict it by restricting relationships exclusively to `description`.
- For `full-han-viet` and `hybrid-world-hv` naming modes: require Hán-Việt localization, complete non-mixed syllables with normal spaces, and conservative project-local handling when original Hanja/Hanzi is absent. For Murim/wuxia, `GENRE-SPECIFIC CLASSIFICATION` must distinguish core institutional and martial categories (EN or VI terms).

## 4. `glossary_refinement_user_prompt.md` *(conditional)*

Validate only when explicitly requested (`--require-refinement`).
- Starts with `Apply the following project-specific glossary refinement rules for ` and ends with `Refine conservatively. Correct only what can be supported by the supplied glossary data.`
- Required section order: `PROJECT-SPECIFIC REFINEMENT POLICY` → `IDENTITY AND CANON` → `NAMING / LOCALIZATION` → `CHARACTERS / TITLES / RANKS / ADDRESS` → `TERMINOLOGY / HIERARCHY / ENTITY DISTINCTIONS` → `CONFLICT RESOLUTION` → `FINAL PROJECT CHECK`.
- Keeps literal `{entries}` (at most once) and excludes Glossarion's generic CSV/header/delimiter System Prompt contract.
- Covers canonical identity, full personal names, homonyms, gender conflicts, forms of address, no invented entities; Sino-Vietnamese modes enforce Hán-Việt and forbid inventing Hanja/Hanzi.

## 5. Running the Validator

```bash
python scripts/validate_prompt_pack.py <prompt-pack-directory>
```

Optional flags:
- `--naming-mode auto|full-han-viet|hybrid-world-hv|preserve` (default: `auto`)
- `--max-profile-words <N>` (default: `400`)
- `--allow-long-profile` (bypass profile word ceiling for justified exceptions)
- `--require-refinement` (require and validate `glossary_refinement_user_prompt.md`)
- `--require-relations` (enforce `{relations_instruction}` presence in `glossary_extract_prompt.md`)

Fix every reported error until output is exact `FORMAT VALIDATION: PASS`.
