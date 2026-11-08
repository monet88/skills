# Changelog

All notable changes to `@monet88/skills` are documented in this file.

## [2026-11-08]

### Added
- **`novel-prompt`** (`skills/novel-prompt`):
  - Added full skill package for generating, auditing, and validating Glossarion prompt packs (`system_prompt.md`, `glossary_extract_prompt.md`, and optional `glossary_refinement_user_prompt.md`) for Vietnamese long-form fiction translation across Korean Murim, Chinese wuxia/xianxia/xuanhuan, Western fantasy, LitRPG, and hybrid genres.
  - Distilled Vietnamese literary syntax and anti-translationese mechanics (`references/vietnamese-literary-craft.md`, `references/prompt-templates.md`, `SKILL.md`) directly into the model-facing `STYLE` block of `system_prompt.md`:
    - Topic–Comment (`Đề–Thuyết`) clause ordering and serial verb chains (`chuỗi động từ nối tiếp`).
    - Semantic aspect control (eliminating mechanical past-tense `"đã"`, stative/habitual `"đang"`, and conversational `"sẽ"`) and directional verb complements (`ra, vào, lên, xuống, đi, lại`).
    - Anti-nominalization (`"sự/việc..."`), active-voice preference over `"bị/được... bởi"` calques, expressive classifiers (`nỗi, niềm, mối, cơn, luồng`), possessive pruning, and anti-synonym-stacking.
    - Spoken dialogue separation from narration with character-fitted Vietnamese sentence-final modal particles (`à, ừ, nhỉ, nhé, đấy, thôi, mà, chứ, cơ, sao, đâu, ạ`).
  - Included `scripts/validate_prompt_pack.py` mechanical format validator and comprehensive genre/glossary/multilingual reference guides.

## [2026-09-17]

### Added
- **`image-prompt-guide`** (`skills/image-prompt-guide`):
  - Added image generation and editing prompt optimization skill with translate-first search, real provenance, and packaged test suite (`tests/image-prompt-guide.test.mjs`).
- Added repository installation guide in `README.md` (`npx skills@latest add monet88/skills`).

### Removed
- Removed deprecated `pinchtab` and `browseract` skills.

## [2026-08-28]

### Added
- **`agent-browser-skill-forge`** (`skills/agent-browser-skill-forge`):
  - Forges reusable skill packages and direct API clients from live website exploration via `agent-browser`, with RAE-derived verification invariants, recursive credential redaction, and black-box acceptance tests.
- **`ask-impeccable`** (`skills/ask-impeccable`):
  - Coordinator workflow for delegating UI/UX commands inside coding workers.
