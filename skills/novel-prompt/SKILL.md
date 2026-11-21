---
name: novel-prompt
description: "Create, audit, and optimize Glossarion prompt packs (`system_prompt.md`, `glossary_extract_prompt.md`, and optional `glossary_refinement_user_prompt.md`) from novel chapters or existing prompts for Vietnamese fiction translation (Murim, wuxia, xianxia, fantasy, LitRPG, modern/showbiz, Japanese LN, hybrids)."
---

# Novel Prompt

Generate or revise **two ready-to-paste Glossarion prompts** by default: `system_prompt.md` and `glossary_extract_prompt.md`. Generate `glossary_refinement_user_prompt.md` **only** on explicit request. Never generate `assistant_prompt.md`.

## 1. Inspect source evidence

1. **Sample broadly before drafting:** Read opening chapters (Ch 1–5). When given a multi-chapter folder or EPUB (>50 chapters), also sample **mid** (~50%) and **late** (last 2–3) chapters to catch mid-book translator/romanization shifts, late power-system reveals, aggregator watermarks, and footnote conventions.
2. **Check glossary coverage of the latest arc before trusting an existing glossary:** a glossary extracted from only part of the book silently lacks every name introduced later — techniques, epithets, places, factions — and the translator then paraphrases those names (see `NAMES AND PROPER NOUNS`). Diff late-arc capitalised compounds against the glossary; extract or append the tail arc separately rather than assuming full coverage. Verify each addition against the published translation before writing it, and never assume a low model confidence means the term is unimportant — a name appearing only in the final 100 chapters is still a name.
3. **Extract facts from text only:** Identify surface language, original-language family (Korean, Chinese, Japanese, Western, other), genre/hybrid features, POV/voice, dialogue register, social hierarchy, naming pattern, power/UI system, and recurring translation risks. Never infer plot, gender, Hanja/Hanzi, rank, or kinship from a title or romanized name alone.
4. **Ask one focused question only when materially blocked:**
   - Origin unclear and changes localization → *"Novel gốc là Hàn, Trung, Nhật hay phương Tây?"*
   - Modern-linked Murim hybrid where user preference is ambiguous → *"Tên nhân vật để Romaja (kiểu Murim Login) hay dịch 100% Hán-Việt?"*
   - Target language defaults to **Vietnamese**. Do not browse external novel lore unless asked.
5. **On existing-pack audits:** Read both existing prompt files plus representative source excerpts. When a local Glossarion checkout is present (`F:\CodeBase\Glossarion\src`), verify live placeholder behavior in `extract_glossary_from_epub.py` and `relations_tracking.py` rather than guessing.

*Done when:* origin, genre branch(es), naming mode, hierarchy, and key risks are grounded in observed text.

## 2. Select naming mode & load only needed references

Choose one explicit **Naming Mode** from source evidence (or user canon):

- **`full-han-viet`**: Default for Murim, wuxia/võ hiệp, xianxia/tiên hiệp, xuanhuan/huyền huyễn, Eastern supernatural/linh dị. Localize all recurring Sino-origin proper nouns (people, sects, realms, arts, places, items) to complete Hán-Việt.
- **`hybrid-world-hv`**: Modern-linked Korean Murim/Hunter hybrids when personal names stay Romaja (e.g., `Jin Taekyung`) while Murim world entities (places, sects, arts, realms, pills, epithets) use complete Hán-Việt.
- **`preserve`**: Western fantasy, LitRPG/Hunter, modern Korean showbiz/urban, Japanese LN — keep personal/proper names in clean romanization/original convention; translate semantic titles, skills, UI, and common organizations into Vietnamese.

Load references by branch (skip irrelevant files):

| Branch / Need | Read |
| :--- | :--- |
| Prompt skeletons & exact section labels (always) | `references/prompt-templates.md` |
| Vietnamese prose craft & scene-local `xưng hô` (Vietnamese target) | `references/vietnamese-literary-craft.md` |
| Glossarion `v9.15.19+` placeholders, Relations Tracker, CSV schema (always) | `references/glossary-schema.md` |
| Murim, wuxia, xianxia, xuanhuan, Eastern supernatural, or Sino hybrids | `references/sino-han-viet-guide.md` |
| Fantasy, LitRPG/Hunter, military/magitech, modern/showbiz, Japanese LN, hybrids | `references/non-sino-genres.md` |
| English-intermediary text with embedded Hangul/Hanzi/Hanja/Kana/other scripts | `references/multilingual-source-handling.md` |
| Format & validator contract (when auditing or fixing failures) | `references/format-validation.md` |

## 3. Respect responsibility boundaries & priority

Keep each layer strictly in its lane:

- **`system_prompt.md` (translator):** Complete, faithful, natural translation; genre/narrator voice; bidirectional scene-local `xưng hô`; exact supplied glossary display names; 1-to-1 HTML `<p>` structure; one concise coverage pass.
- **`glossary_extract_prompt.md` (extractor):** Canonical entity recognition, single full-name character identity, localization policy, genre classification, CSV/placeholder schema, conservative deduplication, Relations/Gender Tracker compatibility.
- **Glossarion runtime (exclude from prompts):** EPUB/TXT choice, local paths, chapter ranges, batch sizes, glossary persistence/merging, CLI commands, and config flags.
- **Application QA (exclude from prompts):** Per-language residue scanners, retry/fallback loops, and acceptance gates. Put only one brief `source-to-output coverage pass` in `FINAL CHECK`.

**Economy rule:** Write the shortest sufficient prompts for Flash-class models (`cli/gemini-3.8-flash`). Prefer positive, scannable bullets over long semicolon chains or lists of bad examples. State each rule once in its owning section. Keep prompts **book-general regardless of length**: put book-specific steering strictly inside `<NOVEL_PROFILE>` (60–400 words) with at most 2–3 durable anchor examples; never turn prompts into character/technique rosters (those belong in the Glossary).

**Translation priority:** Current source text > `<NOVEL_PROFILE>` > supplied canonical glossary > chapter-gated relations/character context > prior translated context. Prior context never overrides current source facts.

**Refinement priority (only when requested):** Approved canon & verified identity > explicit source-script/Hanzi/Hanja already in rows > project localization policy > conservative cleanup. Never invent entities or historical etymology.

## 4. Draft the prompt files

1. **`system_prompt.md`:** Follow exact plain-text section labels and order in `references/prompt-templates.md` (no `#` Markdown headings, no code fences). Distill Vietnamese craft mechanics from `references/vietnamese-literary-craft.md` directly into `STYLE` and `CHARACTER VOICE AND PRONOUNS` (the runtime translator sees only this file). End with literal `{split_marker_instruction}` as the final non-empty line.
2. **`glossary_extract_prompt.md`:** Follow exact plain-text section labels and order in `references/prompt-templates.md`. Preserve literal `{language}`, `{fields}`, `{gender_instruction}`, `{entries}`, plus `{subject_tracking_instruction}`, `{relations_instruction}`, and optional `{description_*}` placeholders (Glossarion silently strips inactive line placeholders). Never include `{name_split_example}`, `{description_name_split_example}`, `{example}`, or `{description_example}`. End with `Do not output anything except the CSV.`
3. **`glossary_refinement_user_prompt.md` (conditional):** Generate **only** on explicit request. Keep `{entries}` literal; carry only project-specific semantic cleanup (never duplicate Glossarion's generic CSV refinement System Prompt).

## 5. Validate and deliver

1. **Back up before in-place edits** to existing user prompt files, then re-read final files to verify no unfilled `[...]` template stubs or book-specific leaks outside `<NOVEL_PROFILE>`.
2. **Run mechanical validation** on a directory containing the candidate files:
   ```bash
   python scripts/validate_prompt_pack.py <prompt-pack-directory>
   ```
   Pass `--require-refinement` only when refinement was requested; pass `--naming-mode full-han-viet|hybrid-world-hv|preserve` if auto-detection needs an explicit override; pass `--allow-long-profile` only for a justified >400-word profile. Fix every failure until output is exact `FORMAT VALIDATION: PASS`.
3. **Verify semantic grounding:** Profile facts match source; naming mode is consistent across both files; no raw CJK/Hangul residue policy gaps; no contradiction between `{relations_instruction}` and `description` rules.
4. **Deliver** the ready-to-use prompt files (without claiming Glossarion translation/QA was run unless executed). If the user asks to wire them into Glossarion immediately, hand off to `glossarion config save-profile` outside the prompt files.
