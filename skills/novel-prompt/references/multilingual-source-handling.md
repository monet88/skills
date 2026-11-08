# Multilingual Source Handling

Use this whenever the translation source is primarily English but may contain untranslated fragments from the novel's original language.

## Separate two language facts

Always distinguish:

1. **Surface/source language**: the language carrying most of the supplied text, often English.
2. **Original-language family / novel origin**: the language tradition the work came from, commonly Korean, Chinese, or Japanese.

Do not treat `English-to-Vietnamese` as permission to ignore non-English fragments embedded in the English source.

## Determine original-language family

Infer the original-language family only from supplied evidence such as:
- Hangul, Hanzi, Kana, or original-script fragments
- naming patterns that are strongly diagnostic
- title/author metadata supplied by the user
- explicit statements in the chapters or project context

If the original-language family is still materially uncertain and the choice would change naming or localization policy, ask one focused question before generating the prompt pack, e.g.:

`Novel gốc là Hàn, Trung hay Nhật?`

Do not ask when the supplied evidence is already clear enough.

## Mandatory all-language-to-Vietnamese translation

During analysis, identify all source languages and original-script fragments. In the generated System Prompt, express their treatment as **one compact rule**: translate all readable supplied prose to Vietnamese (unless the user chooses another target language), regardless of source language. Do not enumerate an individual QA procedure for each encountered language.

For human-readable narrative content:
- Translate **every** source-language sentence and meaningful fragment into Vietnamese, including English narration/dialogue/thought/UI text as well as embedded Korean, Chinese, Japanese, or other languages. Never copy a readable source-language sentence or clause through unchanged.
- Perform a source-to-output coverage pass before returning: each source sentence/meaningful fragment must have a Vietnamese counterpart in narrative order.
- Korean Hangul, including syllables in the range `가-힣` and Hangul Jamo, must not survive untranslated in the final Vietnamese prose.
- Chinese Hanzi / Korean Hanja must not survive untranslated in the final Vietnamese prose when they are ordinary narrative text, poems/chants, or parenthetical/bracketed glosses attached to terms (`Term [漢字]`, `Term (漢字)`). In Murim/wuxia/xianxia works, localize the term into Vietnamese/Hán-Việt and **strip the bracketed CJK/Hangul gloss** completely so zero raw CJK characters remain in reader-facing output; render standalone CJK verses/formulas into Hán-Việt or natural Vietnamese verse.
- If a chapter ends with a standalone romanized or translated novel-title watermark tacked onto the final sentence/paragraph without grammatical connection (e.g., `Chang-gwi-musang`), omit the watermark rather than translating it into the prose.
- Japanese Kanji/Kana (Hiragana/Katakana) must not survive untranslated in the final Vietnamese prose when they are ordinary narrative text or canonical entities that should be localized/transliterated.
- The only human-readable source-form exception is glossary/matching metadata: `raw_name` and confirmed `aliases` may retain original spellings/scripts for lookup. Running translated prose gets no such exception. Preserve source code, literal data, URLs, tag names/attributes, and other clearly non-translatable technical payloads as literals; they are not prose.

## Language-family localization policy

### Korean-origin novels

- For Murim and other Sino-Korean martial/cultivation fiction, convert identifiable Sino-Korean Hangul names/terms/titles to standard Vietnamese Hán-Việt forms.
- Example: `냉혈아수라왕` → `Lãnh Huyết A Tu La Vương`.
- If the Hangul term is clearly native Korean rather than Sino-Korean, translate its meaning or use a stable Vietnamese transliteration as context requires; do not pretend it has Hanja.
- If Hanja is unavailable for a recurring proper noun but the project uses Hán-Việt localization, apply the project's stable inferred Hán-Việt form and mark uncertainty only in glossary metadata, never in running prose.

### Chinese-origin novels

- Translate ordinary Chinese prose into Vietnamese.
- For wuxia/xianxia/xuanhuan and other Sino-influenced genres, convert canonical names, sects, titles, techniques, realms, items, formations, locations, and similar recurring entities to established Hán-Việt forms.
- Prefer explicit Hanzi as the strongest evidence for the Hán-Việt reading.

### Japanese-origin novels

- Translate ordinary Japanese prose into Vietnamese.
- Do not leave Kanji, Hiragana, or Katakana raw in running Vietnamese prose.
- Preserve Japanese identity for personal/proper names through established Japanese romanization/transliteration unless the user or project explicitly requires Hán-Việt readings of Kanji.
- Translate semantic titles, ranks, techniques, organizations, and terms according to genre and project canon.

### Other origins

- Translate embedded original-language fragments by meaning and use a stable transliteration/localization policy appropriate to that language.
- Do not apply Hán-Việt merely because CJK-looking text appears unless the genre/origin policy supports it.

## Glossary behavior

Original script is allowed and useful in glossary matching data even when it must disappear from running Vietnamese prose:
- Keep exact original-script spelling in `raw_name` when it is the source match key.
- Put confirmed alternate English/romanized/original-script forms in `aliases` when available.
- Put only the final Vietnamese display form in `translated_name`.
- In the Vietnamese Hán-Việt branch, enforce **100% Hán-Việt** for Sino-origin names: no partial Romaja/pinyin/English residue and no hybrid hyphenated forms such as `Dư-min` or `Thủy-ryun`. Convert the entire canonical name, then use normal spaces between Hán-Việt components.
- If an English gloss and an original-script form clearly identify the same entity, deduplicate them as one identity instead of creating competing Vietnamese names.

Example:
- raw source: `냉혈아수라왕`
- translated_name: `Lãnh Huyết A Tu La Vương`
- possible confirmed alias: `Cold-Blooded Asura King`

## Post-translation QA ownership

Translate every human-readable source fragment; this is a **translation requirement**, not a multi-step testing script. When the Glossarion QA pipeline is configured to detect untranslated fragments and retry them, leave detailed language detection, residue scanning and repair to QA. The System Prompt should contain only one concise source-coverage instruction, not repeated automatic retry or multilingual inspection steps. Never add dedicated Spanish/Korean/English exception rules solely because a chapter happens to contain a short passage in that language.

Original scripts remain useful in `raw_name` / confirmed `aliases` for matching. Literal code, URLs and HTML attributes are not running prose. Do not impose a naive Latin-character ban on Vietnamese output.
