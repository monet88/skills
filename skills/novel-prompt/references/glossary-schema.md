# Glossarion Glossary Schema (`v9.15.19+`)

Authoritative placeholder and schema contract verified against `F:\CodeBase\Glossarion\src\extract_glossary_from_epub.py`, `relations_tracking.py`, and `glossary_refinement.py`.

## 1. Extraction Prompt Placeholders (Balanced/Full CSV)

**Required literal placeholders:**
- `{language}` — target display language (`Vietnamese`)
- `{fields}` — expands to comma-separated column header (`type, raw_name, translated_name, gender, <custom_fields>`) and enabled `Entry Types` when prompt specifies CSV. *(Do not mix with `{fields1}`, which selects U+001F Unit Separator format.)*
- `{gender_instruction}` — expands dynamically for entry types with `has_gender=True`; empty if none.
- `{entries}` — human-readable list of enabled entry types.

**Recommended Glossarion `v9.15.19+` line/inline placeholders (auto-removed when feature is OFF):**
- `{subject_tracking_instruction}` — owns its line; expands when `include_gender_context` is ON, dropped cleanly when OFF.
- `{relations_instruction}` — owns its line; expands when Relations Tracker (`--relations` / `glossary_enable_relations_tracker`) is ON, dropped cleanly when OFF. Instructs the extractor to populate the dedicated `relations` column (`other_raw_name: role; ...` in both directions) written to `*_relations_tracker.json` and injected chapter-gated at translation time. **Omitting it triggers a Glossarion runtime warning when `--relations` is ON.**
- `{description_mandatory}`, `{description_detailed}` — line-owning; active only when `description` is in Custom Fields.
- `{description_in_language}` — inline (`" and description"` when active, `""` when inactive).
- `{description_excluded_note}` — inline; use only alongside Glossarion's stock rejected-starter rule.

**Forbidden placeholders (for Vietnamese full-identity packs):**
- `{description_name_split_example}`, `{name_split_example}` — expand to hardcoded Korean surname/given-name **splitting**, directly contradicting full canonical character identities.
- `{description_example}`, `{example}` — expand to fixed Korean-to-English rows that bias Vietnamese/non-Korean extraction.

**Single-occurrence rule:** Never repeat multi-line/line-owning placeholders (`{fields}`, `{fields1}`, `{gender_instruction}`, `{entries}`, `{description_mandatory}`, `{description_detailed}`, `{subject_tracking_instruction}`, `{relations_instruction}`) more than once — Glossarion inserts their full text in place.

## 2. Entry Types & Custom Fields

Use only types enabled in `{entries}`; prefer the most specific type and fall back to `terms` last:
`character`, `terms`, `locations`, `nicknames`, `surnames`, `titles`, `organizations`, `races_species`, `ranks`, `classes`, `spells`, `skills`, `abilities`, `techniques`, `traits`, `items`, `materials`, `currencies`, `power_system`, `technologies`, `events`.

Standard custom fields (`D:\Novel-Translate\config.json` default: `description`, `subtype`, `translation_mode`, `aliases`):
- **`raw_name`**: Exact literal spelling physically present in the source text (lookup/compression key). Never back-translate an English or romanized source term into Hangul/Hanzi/Kana—even if Glossarion's built-in `{relations_instruction}` examples show Korean `raw_name`s.
- **`translated_name`**: Single clean canonical Vietnamese display form. No `/` alternatives, no roles, no parenthetical glosses, no `(EN)` markers.
- **`aliases`**: Confirmed alternate spellings, romanizations, English glosses, or original-script forms for the same identity, separated by `|` (never commas). Glossarion's alias-aware glossary compression matches against both `raw_name` and `aliases`.
- **`subtype`**: Concise evidence-based sub-category when supported; else empty.
- **`translation_mode`**: Allowed values only: `preserve_en`, `translate`, `transliterate`, `hybrid`. Use `translate`/`hybrid` for Hán-Việt localized entities; `preserve_en` for names/brands kept verbatim.
- **`description`**: Brief stable identity, faction, rank, or function context (no plot recap, no invented lore).
- **Relations vs. `description` boundary:** When Glossarion's Relations Tracker is active, `{relations_instruction}` states that inter-character relationships belong exclusively in the `relations` column (never duplicated into `description`). When the Relations Tracker is OFF, `{relations_instruction}` is stripped and concise verified directional role/kinship facts may live in `description` — never as fixed pronoun pairs.

## 3. Identity, Gender, Deduplication & Rejection Contract

- **Identity before gender:** Resolve canonical character identity first; emit at most one `character` row per person. Never split a character into two rows for conflicting gender evidence — keep one row and follow `{gender_instruction}` (empty/unknown) when unresolved.
- **Full names & homonyms:** Keep full personal names as one canonical character row (do not split surnames into standalone people). Allow duplicate `raw_name` rows only for proven distinct homonymous characters, and avoid assigning two distinct characters identical `translated_name` values (prevents downstream homonym collision in `glossarion glossary clean`).
- **Existing canon:** Reuse approved canon only when actually supplied in the request; Glossarion merges prior rows post-extraction and does not inject the full database into every extraction call.
- **Hard rejections:** Reject complete sentences, dialogue lines, ordinary pronouns, unnamed extras, generic descriptive role phrases (`innkeeper`, `guard`, `courtesan`, `servant`), bare standalone titles/honorifics without a proper noun or institution (`Sect Leader`, `Elder`, `Young Master`, `Lord`, `Master`, `Captain`), generic common nouns, ordinary actions, temporary descriptions, and prose fragments. Retain named techniques/skills/items even when they contain verbs.

## 4. Optional Glossary Refinement User Prompt (`glossary_refinement_user_prompt.md`)

Generate **only** on explicit request. Glossarion's built-in `DEFAULT_GLOSSARY_REFINEMENT_SYSTEM_PROMPT` (`glossary_refinement.py`) already handles CSV formatting, delimiter, column order, and no-header output.

Available placeholders: `{entries}` (preferred in User Prompt), `{fields}`, `{fields1}`, `{columns}`, `{chunk_index}`, `{total_chunks}`.

Keep the User Prompt strictly project-specific and semantic:
- Canonical identity & conservative duplicate merging (preserving distinct homonyms and full personal names)
- Gender-conflict consolidation without guessing
- Project Naming Mode normalization & alias consolidation (`|`)
- Genre taxonomy preservation (institutions, power systems, techniques, titles)
- Preserving already-correct canon and leaving uncertain metadata empty
