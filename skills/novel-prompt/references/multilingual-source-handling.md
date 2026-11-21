# Multilingual Source Handling

Load this reference when the supplied source is primarily English (or another intermediary language) containing embedded fragments from the novel's original script (Korean Hangul, Chinese Hanzi, Korean Hanja, Japanese Kanji/Kana, or other languages).

## 1. Separate Surface Language from Origin Family

Always distinguish:
1. **Surface language:** Language carrying most of the text (commonly English).
2. **Original-language family:** Tradition the novel comes from (Korean, Chinese, Japanese, Western, other), determined from original-script fragments, diagnostic naming patterns, or explicit metadata.

If origin is materially uncertain and changes naming policy, ask one focused question (*"Novel gốc là Hàn, Trung hay Nhật?"*). Do not ask when text evidence is already clear.

## 2. All-Language Coverage & Zero Raw-Script Prose

In `system_prompt.md`, express coverage as **one compact rule**: translate all readable prose into Vietnamese regardless of source language. Do not insert per-language QA scanners or retry scripts (Glossarion QA and `Partial.b2` own residue scanning and surgical repair).

- **Translate every readable fragment** across English narration, dialogue, inner thoughts, UI text, and embedded original scripts. Never copy readable source sentences through unchanged.
- **Korean Hangul (`가-힣` and jamo):** Zero raw Hangul in Vietnamese output. Convert Sino-Korean terms to Hán-Việt (e.g., `냉혈아수라왕` → `Lãnh Huyết A Tu La Vương`); translate native Korean words by meaning; convert chat jamo (`ㅋㅋ`, `ㅎㅎ`, `ㅠㅠ`, `ㅇㅇ`) to natural Vietnamese/Latin chat equivalents.
- **Chinese Hanzi / Korean Hanja:** Translate ordinary Hanzi prose; localize recurring Sino-origin entities per `references/sino-han-viet-guide.md`. Strip parenthetical/bracketed CJK glosses (`Term [漢字]`, `Term (漢字)`) after localizing the term; render standalone CJK poems/chants/inscriptions into Hán-Việt or Vietnamese verse.
- **Japanese Kanji/Kana:** Translate Japanese prose; keep Japanese personal names in established romanization unless Hán-Việt is explicitly requested; leave zero raw Kanji/Hiragana/Katakana in output.
- **Other languages:** Translate embedded fragments by meaning using natural Vietnamese localization; do not force Hán-Việt merely because foreign script appears.
- **Watermarks vs. footnotes:** Omit standalone aggregator title watermarks tacked onto a chapter's end; translate genuine author/translator footnotes cleanly (`Chú thích:`).
- **Allowed literal exceptions:** Glossary matching metadata (`raw_name`, confirmed `aliases`) may retain source scripts; literal code, URLs, and HTML tag names/attributes stay untouched.

## 3. Glossary Matching vs. Display Separation

- Keep exact original-script or source-surface spelling in `raw_name` when it is the source lookup key.
- Consolidate confirmed English glosses, romanizations, and original-script variants of the same identity into one row using `aliases` (`|`), e.g. `raw_name: 냉혈아수라왕`, `translated_name: Lãnh Huyết A Tu La Vương`, `aliases: Cold-Blooded Asura King`.
- Put only the final Vietnamese display form in `translated_name`.
