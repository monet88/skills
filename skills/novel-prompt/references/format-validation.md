# Prompt Pack Format Validation

Use this contract after drafting and before delivery. Format validation is mandatory; semantic/content validation in `SKILL.md` is still required separately.

## General rules

All generated files are plain ready-to-paste prompt text. `system_prompt.md` and `glossary_extract_prompt.md` are required. `glossary_refinement_user_prompt.md` is optional and must be generated only when the user explicitly requests refinement/cleanup instructions.

- Do not add Markdown `#` headings or fenced code blocks around the prompt.
- Do not add analysis, explanations, change logs, or report text inside the files.
- Preserve exact structural labels from `references/prompt-templates.md`. Do not append a subtitle or parenthetical to `STYLE`, `CHARACTER VOICE AND PRONOUNS`, or any other heading; a decorated heading is **not** the required label and must be reported as a format failure.
- Keep sections in template order. Optional sections may be omitted only where the template explicitly marks them optional.
- Do not create `assistant_prompt.md`; its content belongs inside `<NOVEL_PROFILE>` in `system_prompt.md`.

## `system_prompt.md`

This is the combined Translation/System Prompt.

Required section order:

1. `TASK`
2. `STYLE`
3. `CHARACTER VOICE AND PRONOUNS`
4. `GENRE TERMINOLOGY`
5. `MULTILINGUAL SOURCE FRAGMENTS`
6. `NAMES AND PROPER NOUNS`
7. `COMBAT / POWER SYSTEM / TECHNICAL CLARITY` when relevant
8. `IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA`
9. `HTML AND PUNCTUATION`
10. `SOURCE FIDELITY AND CONTEXT PRIORITY`
11. `<NOVEL_PROFILE>` block
12. `FINAL CHECK`
13. `{split_marker_instruction}` as the final non-empty line

The file must start with the translator-role sentence, not a title heading. `{split_marker_instruction}` must appear literally and exactly once.

The System Prompt must require the chosen output language (Vietnamese by default) for all meaningful reader-facing prose, regardless of input language. One brief `source-to-output coverage pass` under FINAL CHECK is enough. Keep glossary display-name authority and literal technical/source matching exceptions. Do not repeat per-language residue scans or QA/retry procedures in the prompt; QA belongs to the application.

The `<NOVEL_PROFILE>` wrapper must appear exactly once after `SOURCE FIDELITY AND CONTEXT PRIORITY` and before `FINAL CHECK`.

Inside the profile, use this field order, omitting only fields the template explicitly allows to be absent:

1. `Title:` when known
2. `Genre:`
3. `Setting:`
4. `Translation Style:`
5. `Narrative Voice:`
6. `Dialogue Style:`
7. `Worldbuilding / Hierarchy Priorities:`
8. `Naming Conventions:`
9. `Pronoun / Address Conventions:`
10. `Power-System Treatment:` when present
11. `Avoid:`

Keep the embedded profile normally 60-240 words; never pad it with filler. Exceed 240 only when the novel genuinely needs extra steering, using `--allow-long-profile` for an explained exception.

Generic sections outside `<NOVEL_PROFILE>` must not contain book-specific names, plot facts, or exact term mappings.

Semantic xưng hô gate: the generic CHARACTER VOICE section must instruct silent speaker/addressee mapping in **both directions** before translation, check context-dependent hierarchy/public-private/disguise changes, preserve named title wording, and avoid permanent fixed pronoun pairs. This is a content review gate, not a Glossarion parser requirement. Do not universally ban modern/neutral pronouns, force `ta/ngươi` or `hắn/gã/ả` on every line, or erase documented family/affectionate shifts.

Vietnamese literary-craft gate: target **sense-first, non-calqued Vietnamese** while maintaining source facts, timing, actor, negation, focus, intentional repetition and emotional register. Keep scene-specific dialogue rules separate from stable glossary identities. Do not force cadence, idiom quotas or rigid onomatopoeia mappings.

Responsibility gate: `system_prompt.md` must not tell the translator to choose EPUB instead of TXT, specify file paths/chapter batch sizes, perform extraction/CSV deduplication, or execute QA/retry procedures. These are preparatory, extractor or runtime tasks. The System Prompt should use a supplied glossary rather than describe how to build one.

## `glossary_extract_prompt.md`

Required section order:

1. `OUTPUT FORMAT`
2. `TRANSLATION REQUIREMENTS`
3. `ACTIVE ENTRY TYPES`
4. `GENRE-SPECIFIC CLASSIFICATION`
5. `CHARACTERS / NAMES / TITLES / RANKS / ADDRESS`
6. `POWER SYSTEM / TECHNIQUES / ITEMS / ORGANIZATIONS`
7. `TRANSLATION_MODE / SUBTYPE / ALIASES / DESCRIPTION`
8. `EXISTING CANON AND DEDUPLICATION`
9. `HARD REJECTION RULES`
10. `COMPLETION CHECK`

Required literal placeholders for the default CSV extraction path:

`{language}`, `{fields}`, `{gender_instruction}`, `{entries}`.

Description-specific placeholders (`{description_mandatory}`, `{description_in_language}`, `{description_detailed}`, `{description_excluded_note}`) are optional. **Do not mandate or include** `{description_name_split_example}` or `{name_split_example}` for complete full-name character identities: the current app expands them into surname/given-name row splitting. Likewise, fixed examples `{description_example}` and `{example}` expand to Korean-to-English rows and should be omitted for Vietnamese or other mismatched tasks. An incompatible placeholder is a validation defect, not a missing requirement. Check the current Glossarion checkout if supplied. Do not repeat multi-line `{fields}`, `{gender_instruction}`, or `{entries}` placeholders inside later behavioral sections: each expansion is inserted in-place, not referenced by pointer.

The file must retain the dynamic-column ordering instruction and end its behavioral contract with `Do not output anything except the CSV.`

The character extraction contract must explicitly state all of the following:

- resolve canonical character identity before assigning gender or serializing rows
- output at most one character row per canonical identity
- never keep both `male` and `female` rows for the same person merely because evidence conflicts
- on unresolved gender conflict, keep one identity and use `{gender_instruction}` for unknown/empty handling rather than guessing
- allow duplicate surface `raw_name` values only for clearly established distinct homonymous people
- preserve complete canonical full names rather than automatically splitting them into surname/given-name character rows
- treat stable titles/ranks/forms of address as glossary candidates only when they are reusable canonical translation entities, not ordinary pronouns or one-off address phrases
- silently resolve who speaks to whom and verified **direction-specific** relationships before extraction; place those facts only in an active description field, never in the character's translated_name or new columns
- do not confuse a stable honorific (glossary candidate) with a context-specific speaker's self/addressee pronouns (translation-time decision)

The `GENRE-SPECIFIC CLASSIFICATION` section must be populated from analysis rather than left as generic placeholder prose. For Murim/wuxia, it must preserve the supported distinctions among names, titles/ranks/address forms, institutions/factions, martial terminology, arts/technique categories, realms/ranks, and recurring items/organizations/locations.

For Vietnamese Sino-influenced martial/cultivation genres, the extraction contract must also:

- explicitly require `Dịch 100% Hán-Việt` for recurring Sino-origin Romaja/pinyin/English-rendered names and named terms
- reject mixed/partial Hán-Việt + romanization forms such as `Dư-min` and `Thủy-ryun`; removing the hyphen alone is not enough
- require the final Hán-Việt `translated_name` to use normal spaces and contain no leftover romanized name component for the same canonical identity

## `glossary_refinement_user_prompt.md`

This file is conditional. Generate and validate it only when the user explicitly requests glossary refinement/cleanup instructions. Otherwise it should be absent. When present, it is the optional **User Prompt** for Glossarion's glossary refinement feature and must not replace or duplicate the app's generic refinement System Prompt.

Required section order:

1. `PROJECT-SPECIFIC REFINEMENT POLICY`
2. `IDENTITY AND CANON`
3. `NAMING / LOCALIZATION`
4. `CHARACTERS / TITLES / RANKS / ADDRESS`
5. `TERMINOLOGY / HIERARCHY / ENTITY DISTINCTIONS`
6. `CONFLICT RESOLUTION`
7. `FINAL PROJECT CHECK`

Requirements:

- first non-empty line begins with `Apply the following project-specific glossary refinement rules for `
- preserve literal `{entries}` so the cleanup policy respects the active refinement types
- do not include generic CSV/header/delimiter/schema output instructions; those belong to Glossarion's refinement System Prompt
- do not include actual glossary rows or hard-coded novel term mappings
- preserve complete character identities; never automatically split full names into surname/given-name character rows
- merge only confirmed duplicate identities and keep distinct homonyms separate
- resolve male/female conflicts into one canonical identity; if unresolved, keep one row with unknown/empty gender rather than guessing
- mirror the analyzed naming, terminology, hierarchy/address, institution/faction, technique/power-system, item/organization/location policy of the extraction prompt
- end with `Refine conservatively. Correct only what can be supported by the supplied glossary data.`

For Vietnamese Korean Murim / Chinese wuxia and related Sino-influenced branches, it must additionally:

- include `Dịch 100% Hán-Việt`
- reject mixed forms such as `Dư-min` and `Thủy-ryun`
- cover supported terms, titles/ranks/forms of address, sect/clan/family/alliance/cult or equivalent institution distinctions, martial-system categories, and canonical names
- forbid inventing historical Hanja/Hanzi when the refinement input does not reliably establish the mapping

## Mechanical validator

After creating the default two files, run:

```bash
python scripts/validate_prompt_pack.py <prompt-pack-directory>
```

A non-zero exit code is a hard failure. Fix every reported issue and rerun until the script prints `FORMAT VALIDATION: PASS`. If refinement was explicitly requested, generate `glossary_refinement_user_prompt.md` and run the validator with `--require-refinement`.

Use `--allow-long-profile` only when the embedded `<NOVEL_PROFILE>` genuinely requires more than 240 words. This bypasses only the maximum word-count check; all structural checks still apply.
