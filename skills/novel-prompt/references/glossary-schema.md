# Glossarion Glossary Schema

## Dynamic placeholders

Mandatory for the default manual Balanced/Full **CSV** custom prompt (retain literally):

- `{language}` — translated display language
- `{fields}` — dynamically generates comma-separated column header and active types when prompt specifies CSV
- `{gender_instruction}` — gender field eligibility and unknown handling
- `{entries}` — active glossary entry types

Use only when their expansion matches the task:

- `{description_mandatory}`, `{description_in_language}`, `{description_detailed}` — appropriate for schema-driven descriptions
- `{description_excluded_note}` — only useful with the built-in rejected-starter wording
- `{description_example}`, `{example}` — **fixed Korean-to-English examples** in current Glossarion; normally omit for Vietnamese or Western fantasy (the supplied examples are not genre/language neutral)
- `{description_name_split_example}`, `{name_split_example}` — **fixed full-name splitting instructions** in current Glossarion; never use when a character must have one full-name canonical identity

The source of truth for the observed expansion is `src/extract_glossary_from_epub.py` in the supplied Glossarion checkout: `_apply_description_rule_placeholders`, `_DESCRIPTION_NAME_SPLIT_EXAMPLE_TEXT`, `_NAME_SPLIT_EXAMPLE_TEXT` and `build_prompt`. Inspect current local source when available; behavior may change in later versions. Avoid copying any placeholder merely to satisfy a template checklist. `{fields1}` uses a distinct U+001F Unit Separator schema, not a drop-in CSV replacement for `{fields}`.

## Recommended entry types

Use only types actually enabled by `{entries}`. A broad recommended vocabulary is:

- `character`
- `terms`
- `locations`
- `nicknames`
- `surnames`
- `titles`
- `organizations`
- `races_species`
- `ranks`
- `classes`
- `spells`
- `skills`
- `abilities`
- `techniques`
- `traits`
- `items`
- `materials`
- `currencies`
- `power_system`
- `technologies`
- `events`

Use `terms` only as fallback when a more specific active type does not fit.

## Recommended custom fields

- `description`: concise stable context useful for future translation; for characters, include brief **directional** hierarchy/kinship/honorific facts when explicitly supported (e.g., who is whose superior), noting public/private role or relationship stage when relevant. Do not impose fixed Vietnamese pronoun pairings, guess seniority, or recap the plot.
- `subtype`: more precise classification only when supported; otherwise empty.
- `translation_mode`: if present, restrict to `preserve_en`, `translate`, `transliterate`, `hybrid`. For Vietnamese Murim/wuxia/xianxia/xuanhuan, prefer `translate` or `hybrid` for Sino-origin entities so `translated_name` is Hán-Việt/localized Vietnamese rather than raw romanization.
- `aliases`: confirmed alternate names for the same entity; separate multiple aliases with `|`, not commas.

## Translation behavior

- `raw_name` must preserve the canonical source form because it is the lookup/matching key. This may legitimately be Hangul, Hanzi, Kanji/Kana, English, or romanization if that is what appears in source.
- `aliases`, when available, should capture confirmed alternate English glosses, romanizations, and original-script forms for the same identity; do not create separate competing rows for the same entity.
- `translated_name` must contain only the chosen Vietnamese display form: direct translation, accepted equivalent, Hán-Việt localization, transliteration, or preserved proper name as appropriate to the genre. Reader-facing Vietnamese must not inherit untranslated original script merely because `raw_name` contains it.
- Do not inject roles, descriptions, or parenthetical glosses into `translated_name` (e.g., never `Khung Lâu (Lầu Cúi Đầu)`).
- When target language is Vietnamese and genre is Murim, wuxia/võ hiệp, xianxia/tiên hiệp, xuanhuan/huyền huyễn, or similar Sino-influenced martial/cultivation fiction, default recurring Sino-origin proper nouns to Hán-Việt/localized Vietnamese. Do not copy raw pinyin/romanized Korean names into `translated_name` merely because original Hanzi/Hanja is unavailable.
- **English-calqued proper noun reconstruction:** Reconstruct English-rendered proper nouns (pavilions, brothels, halls, towers, fortresses, valleys, sects, formations, techniques, realms, items, epithets such as `Dusk Sentiments Pavilion`, `Dog Fortress`, `Lightning Strike`) into concise 2–4 syllable Head-Final Hán-Việt compounds (`Mộ Tình Các`, `Khuyển Trại`, `Lôi Kích`), never word-by-word modern vernacular phrases (`Lâu Các Tinh Thần Buổi Tối`, `Chó Trại`, `Sét Đánh`). Clarify that "do not fabricate Hanja/Hanzi" only forbids inventing CJK characters or claiming verified etymology, never Sino-Vietnamese compound reconstruction.
- **Dịch 100% Hán-Việt**: cleanly convert every still-romanized Romaja/pinyin/English-rendered Sino-origin canonical name to a complete Hán-Việt display name. Mixed forms such as `Dư-min` and `Thủy-ryun` are invalid. Do not merely remove the hyphen; localize the remaining romanized syllable(s) too, then use normal spaces between Hán-Việt name components.
- A reader-facing `translated_name` for a Sino-origin character must not contain leftover romanized name syllables or English name words once a Hán-Việt canonical identity is being used. Preserve such source variants only in `raw_name` or confirmed `aliases`.
- Hán-Việt evidence priority: explicit Hanzi/Hanja > established/user canon > explicit semantic gloss > strongly supported Sino-Korean/Sino-Chinese reading > stable project-local Hán-Việt localization.
- If original characters cannot be established, freely choose one **distinctive, natural project-local Hán-Việt** display name for a new Sino-influenced Murim character (including minor characters), and identify it as a project localization in `description` when available. Never fabricate original Hangul/Hanja, etymology, surname, identity, relationships or gender to justify the name. Do not reuse an existing distinct character's display name; software-level deduplication still requires separate checks.
- In this Vietnamese Sino-influenced branch, allow `translated_name == raw_name` only when the raw source is already the accepted Vietnamese/Hán-Việt form, the entity is clearly non-Sino and should remain original, or the user explicitly requests raw preservation.
- Do not append artificial markers such as `(EN)` unless the user explicitly requires that legacy convention.

## Address and dialogue evidence

- Silently examine the supplied dialogue and nearby narration to identify **speaker -> addressee** for each observed reusable title or relationship. Analyze the reverse direction separately; Vietnamese xưng hô is asymmetric.
- Extract only canonical/reusable honorifics, noble/clerical/military ranks, kinship titles, and stable forms of address when an enabled entry type matches. Ordinary I/you/they, incidental insults, and one-off address phrases must not become glossary rows.
- When `description` is active, document verified directional relationships and the conditions under which a title is used (public ceremony, hidden identity, changing status), keeping brief and source-grounded. Never imply a character knows someone else's secret identity before the source reveals that knowledge.
- The glossary anchors identities, stable titles, and evidence-based relationships; **the translation prompt owns scene-specific pronoun selection**. Do not encode per-scene self/address pronoun pairs as `translated_name`, aliases, new entry types, or invented columns. A chapter-local extractor cannot claim facts outside its provided evidence.

## Extraction behavior

Reject:
- complete sentences and dialogue lines
- common pronouns
- unnamed background characters
- generic common nouns
- temporary visual descriptions
- ordinary actions and random fragments

Do not reject a candidate solely because it contains a verb-like word; canonical skills, spells, techniques, titles, or items may contain action words.

Prefer canonical/reusable entities whose stable translation matters across chapters.


## Original-script residue handling

- Use `references/multilingual-source-handling.md` to determine how Korean, Chinese, Japanese, and other embedded source-language fragments should be localized.
- For Korean-origin Murim, an identifiable Sino-Korean Hangul title such as `냉혈아수라왕` should map to `Lãnh Huyết A Tu La Vương`, not remain Hangul in `translated_name`.
- Original script belongs in matching metadata (`raw_name`, confirmed `aliases`), while `translated_name` is the final Vietnamese display form.

## Glossary Refinement User Prompt

Generate this prompt only when the user explicitly requests glossary refinement/cleanup instructions. Glossarion's glossary refinement UI uses a generic System Prompt plus an optional project-specific User Prompt. Novel Prompt should generate only the project-specific User Prompt as `glossary_refinement_user_prompt.md`; do not replace the app's generic refinement System Prompt unless the user explicitly asks.

Available refinement placeholders may include:
- `{fields}`
- `{columns}`
- `{fields1}`
- `{entries}`
- `{chunk_index}`
- `{total_chunks}`

For the generated User Prompt, prefer `{entries}` so the cleanup policy explicitly respects the active refinement types. Do not duplicate the generic CSV/schema/delimiter/output-only instructions already owned by the refinement System Prompt.

The refinement User Prompt should focus on:
- canonical identity before metadata cleanup
- conservative duplicate/near-duplicate merging
- full-name preservation for character identities
- one canonical character row per confirmed identity
- gender-conflict resolution without duplicate male/female rows
- aliases/source-script/romanization normalization
- project-specific naming/localization policy
- genre-specific terminology, hierarchy, stable forms of address, institutions, factions, techniques, power-system distinctions, items, organizations, and locations
- preserving already correct canonical `translated_name` values
- leaving unsupported optional metadata empty instead of guessing

For Vietnamese Korean Murim / Chinese wuxia and related Sino-influenced projects:
- apply complete Hán-Việt normalization to established canonical Sino-origin names and named terms
- reject mixed Hán-Việt/Romaja or Hán-Việt/pinyin forms such as `Dư-min` and `Thủy-ryun`
- use normal spaces after full localization
- keep Romaja/pinyin/original-script variants in `raw_name` or `aliases`, not as the canonical `translated_name`
- when refinement input does not reliably establish a Hán-Việt mapping, do not invent historical Hanja/Hanzi merely from pronunciation
- preserve distinctions among sect/clan/family/alliance/cult, titles/ranks/forms of address, internal/external arts, movement/footwork/lightness skills, weapon arts, complete arts vs named forms, realms/ranks, and other supported Murim/wuxia terminology
