---
name: novel-prompt
description: "Create, audit, and optimize Glossarion prompt packs from opening novel chapters or existing prompt files: a compact combined Translation/System Prompt and an analysis-driven Glossary Extraction Prompt by default, plus a project-specific Glossary Refinement User Prompt only when explicitly requested. Use for consistent Vietnamese long-form fiction translation, genre voice, scene-specific pronouns, Hán-Việt canonical naming, glossary identity, and compatible Glossarion prompt placeholders. Supports Korean Murim, Chinese wuxia/xianxia/xuanhuan, fantasy, LitRPG, and hybrid genres."
---

# Novel Prompt

Create or revise **two usable Glossarion prompts** by default: `system_prompt.md` and `glossary_extract_prompt.md`. Generate `glossary_refinement_user_prompt.md` **only** on explicit request. Do not generate `assistant_prompt.md`.

## 1. Inspect the evidence

1. Read the user's supplied source chapters or representative excerpts; identify the surface language, likely original-language family, genre and hybrid features, narration/voice, setting, rank/relationships, naming conventions, martial/power-system distinctions, and source-specific translation risks. Cross-check disputed facts against actual text; do not infer plot, gender, Hanja, rank, or kinship from the title or a romanized name.
2. On an existing-pack update, inspect `system_prompt.md` and `glossary_extract_prompt.md` plus the available original excerpts. When the user supplies a Glossarion source checkout, inspect its **current local** prompt placeholder expansion and active schema rather than assuming all placeholders are inert. Keep the source file choice in the *analysis workflow*, not the generated System Prompt.
3. Identify the original-language family if possible. When materially uncertain and it changes localization, ask one focused question. The target language defaults to Vietnamese unless otherwise specified.
4. For multilingual English intermediary texts, follow `references/multilingual-source-handling.md`. Do not browse external novel lore unless asked.

## 2. Separate responsibilities before writing

- **`system_prompt.md` (translator):** Controls complete, faithful, fluent translation; genre and narrator voice; context-dependent pronouns; canonical supplied glossary display names; named terms; literal HTML structure. Its job is to translate **the passage Glossarion supplies**, not select a source file or run the application.
- **`glossary_extract_prompt.md` (extractor):** Controls entity recognition, full character identity, Hán-Việt naming, aliases, genre-specific classification, CSV/schema fidelity, and conservative deduplication.
- **Glossarion runtime:** Owns EPUB/TXT/edition selection, paths, chapter ranges, 100-chapter batches or full-book scans, persistence, glossary injection and configuration. Do **not** copy these operational concerns into the System Prompt.
- **Application QA:** Owns detailed source-language residue detection, omissions, retry/repair, acceptance gates, and language-specific retranslation. The System Prompt needs only the translation target and **one brief** source-coverage instruction, not a QA script or dedicated Spanish/English/Korean exception blocks.

**Economy rule:** Generate the *shortest sufficient prompts*. Put a rule only where it can change that model's assigned behavior; do not repeat one requirement under TASK, STYLE, PROFILE and FINAL CHECK. Preserve correctness and genre distinctions rather than blindly deleting necessary instructions.

Read `references/prompt-architecture.md` and `references/prompt-templates.md` for the exact output architecture and structural section labels. Do not replace their required plain-text labels with Markdown headings.

## 3. Genre and localization policy

Read `references/genre-guidance.md`, `references/vietnamese-literary-craft.md` and `references/glossary-schema.md` as applicable.

- Use genre-specific register only when source evidence supports it. Murim/wuxia may need martial honorifics and established terms, but not every line requires archaic Vietnamese; do not import xianxia terms into Murim without source evidence.
- **Tín trước Đạt/Nhã & Khử mùi dịch máy (Anti-Translationese):** Translate by meaning rather than English word order, without changing who acts, negation, emotional force, pacing, imagery, chronology, speech interrupted by action, or deliberate humor. Bake core Vietnamese syntax mechanics from `references/vietnamese-literary-craft.md` directly into `STYLE` in `system_prompt.md` (since the runtime translation model only sees `system_prompt.md`, not external skills):
  - **Cấu trúc Đề–Thuyết & Chuỗi động từ nối tiếp (Topic–Comment & Serial Verbs):** Front-load time/place/condition before action when natural; chain consecutive same-subject verbs without mechanical `"và sau đó"` / `"rồi thì"` and omit repeated subjects once unambiguous.
  - **Thể/thì ngữ nghĩa & Bổ ngữ chỉ hướng (Semantic Aspect & Directional Complements):** Drop repetitive past-tense `"đã"`, habitual/stative `"đang"`, and conversational `"sẽ"` once timeframe is set (use `vừa/mới/từng/sắp/hay/đang... thì`); attach natural directional complements (`ra/vào/lên/xuống/đi/lại`) to motion, gaze, and emotion verbs (`ngã xuống`, `nhìn ra`, `trầm xuống`, `bùng lên`).
  - **Khử danh hóa, bị động thừa, sở hữu cách thừa & nhồi từ đồng nghĩa:** Replace nominalizations (`"sự/việc..."`), weak verb wrappers (`"thực hiện việc..."`), and `-ly` calques (`"một cách..."`) with direct verbs, expressive classifiers (`nỗi/niềm/mối/cơn/luồng`), or fitting từ láy/tượng hình/tượng thanh; convert `"bị/được... bởi"` passives to active clauses unless focus belongs on the affected party; drop redundant possessives (`"của anh ấy/cô ấy/hắn/nó"`) on body parts and held items; avoid stacking synonymous two-syllable doublets mechanically.
  - **Tách giọng Trần thuật vs. Đối thoại & Tiểu từ tình thái:** Keep spoken dialogue distinct from narration using natural spoken cadence and Vietnamese sentence-final modal particles (`à, ừ, nhỉ, nhé, đấy, thôi, mà, chứ, cơ, sao, đâu, ạ`) matched to speaker status and mood.
- **Scene-local address:** Silently determine speaker -> addressee and the reverse independently, including actual rank/kinship, witnesses, disguise, knowledge, relationship stage, public/private setting, and viewpoint. Do not freeze universal pronoun pairs or use future glossary revelations as if characters already know them.
- In Vietnamese Sino-influenced martial/cultivation fiction (Murim, wuxia/kiếm hiệp, xianxia/tiên hiệp, xuanhuan/huyền huyễn), named Sino-origin people, factions, epithets, arts, techniques, realms, items and locations should use **complete Hán-Việt** display forms. Avoid mixed romanized/Vietnamese syllables such as `Dư-min` and `Thủy-ryun`. Keep approved glossary names unchanged. Follow the canonical Korean Romaja/Pinyin-to-Hán-Việt anchor tables in `references/genre-guidance.md` for compound surnames/clans (`Bukgung / Baek Gung` → `Bắc Cung`, `Namgung` → `Nam Cung`, `Moyong` → `Mộ Dung`, `Jegal` → `Gia Cát`), orthodox/unorthodox/demonic factions, and standard Murim/cultivation realms (`Tam Lưu → Nhị Lưu → Nhất Lưu → Tuyệt Đỉnh → Siêu Tuyệt Đỉnh → Hóa Cảnh → Huyền Cảnh → Sinh Tử Cảnh → Tự Nhiên Cảnh`).
- **Bracketed CJK glosses, CJK verses, and trailing watermarks (Murim/wuxia/xianxia):** When the source attaches raw Hanja/Hanzi/Hangul in parentheses or brackets after an English/romanized term (`Mental Imagery Sparring [心像比武]`), localize the term into Vietnamese/Hán-Việt and **strip the bracketed CJK/Hangul gloss** so zero raw CJK characters remain in reader-facing prose. Convert standalone CJK poems, chants, or inscriptions into Hán-Việt or natural Vietnamese verse. Omit any standalone romanized/translated novel-title watermark tacked onto the end of a chapter (e.g., `Chang-gwi-musang`).
- **English-calqued proper noun reconstruction (Phục nguyên Danh từ riêng tiếng Anh sang Từ ghép Hán-Việt cô đọng):** When the source is an English translation of a Murim/wuxia/xianxia/historical work, proper nouns rendered in English words (pavilions, brothels, halls, towers, inns, fortresses, valleys, sects, formations, techniques, realms, items, epithets such as `Dusk Sentiments Pavilion`, `Dog Fortress`, `Lightning Strike`) MUST be condensed into **2–4 syllable Head-Final Hán-Việt compounds** (`[Modifier Hán-Việt] + [Head Noun Hán-Việt: Các / Lâu / Điện / Đường / Viện / Hiên / Trại / Bảo / Cốc / Môn / Phái / Bang / Hội / Trận / Pháp / Quyết / Công / Kích]`, e.g., `Mộ Tình Các` / `Tịch Tình Các`, `Khuyển Trại`, `Lôi Kích`). Never translate them word-by-word in modern Head-Initial vernacular Vietnamese order (`Lâu Các Tinh Thần Buổi Tối`, `Chó Trại`, `Sét Đánh`), and never append parenthetical glosses inside `translated_name` (`Khung Lâu (Lầu Cúi Đầu)`).
- Hán-Việt evidence priority: explicit Hanzi/Hanja > user-approved/existing canonical glossary > source-given meaning > strongly supported Sino reading > **natural, distinctive project-local Hán-Việt form**. For a newly encountered Murim-world character or English-calqued proper noun with no verified original characters, the extractor/translator must choose a **natural Sino-Vietnamese (Hán-Việt) display form**; "do not fabricate Hanja/Hanzi" only forbids inventing CJK characters in parentheses or claiming verified historical etymology—it never forbids translating English-calqued proper nouns into Sino-Vietnamese compounds. Clearly non-Sino modern-world identities need not be forcibly localized.
- Preserve source spelling for matching in `raw_name` and only confirmed alternative forms in `aliases`. Keep full personal names as one canonical identity. Do not merge different people because their raw spellings or proposed Vietnamese names look similar; avoid giving two distinct characters the same display name. Glossarion's software-level deduplication can still require separate verification.

## 4. Combined Translation/System Prompt

Use the **exact template headings and order** in `references/prompt-templates.md`, with one combined prompt and a short `<NOVEL_PROFILE>` block. Put book-specific facts only in the profile and reusable instructions outside it. Keep `STYLE` and `CHARACTER VOICE AND PRONOUNS` labels unmodified.

Include only what the translator needs:

- Translate all reader-facing text into the chosen language, with complete coverage and no omissions or inventions; preserve literal code, URLs and HTML attributes.
- Use concise sense-first prose and genre voice, scene-local xưng hô, accurate combat/system details, and established glossary display names.
- Preserve HTML tags/structure and source order. Use **one** compact `source-to-output coverage pass` in `FINAL CHECK`; no per-language residue scan, retry instructions, or duplicate QA checklists.
- Include `<NOVEL_PROFILE>` with only supported genre, setting, narrator/dialogue traits, hierarchy, naming exceptions and realistic pitfalls, normally **60-240 words** without padding. Preserve the field order from the template.
- Keep `{split_marker_instruction}` literally and as the **final non-empty line**.

**Never insert** directions to use EPUB rather than TXT, source paths, runtime variables, batch size, glossary extraction/CSV operations, or dedicated instructions for translating an isolated language that the application QA handles. No fact or proper-noun mapping from a different rendition may be asserted as source canon merely because it appears in context.

## 5. Glossary Extraction Prompt

Use `references/prompt-templates.md` and `references/glossary-schema.md`. Keep the original template section order and return only valid CSV in the dynamic column order.

- Preserve literal `{language}`, `{fields}`, `{gender_instruction}`, and `{entries}`. Optional `{description_mandatory}`, `{description_in_language}`, and `{description_detailed}` are allowed when appropriate. Do **not** use `{name_split_example}` / `{description_name_split_example}` when full names must remain single identities; current Glossarion expands them into conflicting full-name splits. Avoid stock `{example}` / `{description_example}` Korean-to-English examples when unsuitable.
- Extract only **canonical, reusable** entities in active `{entries}` types: personal identities, stable titles/ranks/honorifics, sects/clans/alliances/cults, factions, internal/external energy and arts, footwork/lightness arts, weapons, named techniques versus whole martial systems, realms, RPG traits, items, poisons, organizations, and locations when supported. Use the most specific active type; `terms` is fallback.
- Resolve a character's identity **before** assigning gender. Keep one full-name character row per identity; leave unsupported metadata empty, do not split surnames into independent people, and keep distinct homonyms apart. Ordinary pronouns and incidental addresses are not glossary rows; stable roles/honorifics may be. Record source-proven, direction-specific relationships only in an existing `description` column, never as fixed pronoun pairs.
- Keep `raw_name` source-faithful. Use a final, complete Vietnamese/Hán-Việt `translated_name` and only confirmed aliases. Allow distinctive **project-local** Hán-Việt names without claiming invented Hanja, following section 3.
- Reuse already approved names **if the canonical glossary is actually supplied to the extractor**. Do not tell the extractor to consult an unseen database: Glossarion's runtime may merge old rows *after* extraction, without injecting the existing glossary into every model prompt.
- Deduplicate by **confirmed identity**, not equal `translated_name` alone; separate different people. Exclude ordinary prose, unnamed extras, generic descriptive role phrases (`leading courtesan`, `brothel keeper`, `innkeeper`, `guard`), standalone bare titles/honorifics without a proper noun (`Sect Leader`, `Cult Leader`, `Elder`, `Young Master`, `Patriarch`, `Pavilion Master`, `Hall Master`, `Lord`, which depend on sect/clan/cult context in Murim/wuxia/xianxia), common nouns, and guessed lore, but retain named techniques even when they contain verbs.
- When optional `translation_mode`, `subtype`, `aliases`, or `description` columns exist, follow the allowed values and schema; do not invent columns.

## 6. Optional glossary refinement

Only on explicit request, generate `glossary_refinement_user_prompt.md` for Glossarion's **optional refinement User Prompt**. Follow `references/prompt-templates.md`; keep `{entries}`. Make it project-specific semantic cleanup, not a second extractor or copy of the application's generic CSV-format System Prompt. Preserve approved names and full identities, merge only confirmed aliases, retain distinct homonyms, and never fabricate Hanja or unsupported gender/relationships. Apply the same Hán-Việt and martial taxonomy used by extraction. Do not generate the file otherwise.

## 7. Validate and deliver

1. Check semantic grounding: profile facts and entity relationships appear in source; name etymologies are not invented; translations are faithful, natural and genre-appropriate; generator prompt respects supplied glossary names and scene-local knowledge.
2. Check responsibility boundaries: no EPUB/TXT operational instructions, chapter batching, glossary data processing or lengthy QA/retry rules in **System Prompt**; do not require Spanish-specific rules. Require **one** concise target-language/coverage instruction, not multiple checks.
3. Check exact heading order, dynamic extractor placeholders, one full identity per character, short profile and literal final `{split_marker_instruction}`. Read `references/format-validation.md`.
4. For in-place edits, back up the user's files before writing, preserve unrelated work, and re-read the final files. Run `python scripts/validate_prompt_pack.py <prompt-pack-directory>` against a directory containing only the candidate two files (and the refinement file only when explicitly requested). Fix all failures until the output is exactly `FORMAT VALIDATION: PASS`. Use `--require-refinement` only when requested; use `--allow-long-profile` only for a justified exception.
5. Deliver the ready-to-use **two complete prompt files**, plus the third file only when requested. Do not generate a separate Assistant Prompt or unrelated report. State what was verified; never claim actual Glossarion translation/QA execution unless performed.

## Skill package updates

When modifying this Skill itself, validate the generated prompt example(s), run the Skill package validator and package the entire updated Skill; do not return only revised references.
