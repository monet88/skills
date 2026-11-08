# Prompt Architecture

Use two core outputs by default: one combined translation prompt plus one glossary extraction prompt. Add the glossary refinement prompt only when the user explicitly requests refinement/cleanup instructions.

## 1. Combined Translation/System Prompt

Purpose: provide one ready-to-paste Glossarion System Prompt containing both durable translation behavior and concise novel-specific steering.

Structure it as two layers inside `system_prompt.md`:

1. Concise reusable translation core: fidelity, sense-first style, scene-local address, approved glossary names, genre terminology, HTML, and one lightweight source-to-output coverage check. Do not duplicate the application QA/retry workflow or mention source file types and batch settings.
2. Brief embedded `<NOVEL_PROFILE>`: only source-supported title, setting, voice, dialogue register, hierarchy, novel-specific name exceptions and pitfalls; normally 60-220 words, without a synopsis or glossary dump.

Keep book-specific names, plot facts, exact term mappings, and other novel canon inside `<NOVEL_PROFILE>` only. Do not scatter them through reusable sections.

Source/edition choice, chapter batching, glossary persistence and post-translation QA are Glossarion workflow responsibilities, not System Prompt instructions. The user should be able to paste `system_prompt.md` directly into Glossarion's System Prompt field and leave the separate Assistant Prompt field empty. `<NOVEL_PROFILE>` is Novel Prompt's organization convention, **not** a required Glossarion parser tag.

## 2. Glossary Extraction Prompt = analysis-driven genre extractor

Purpose: tell Glossarion how to identify reusable canonical entities for the detected genre and original-language family.

This prompt is not the glossary itself. Build its classification and localization rules from the chapter analysis rather than using a one-size-fits-all ontology. It should define entity classification, canonical identity, translation/localization/transliteration behavior, titles/ranks/forms of address, original-script alias handling, rejection rules, deduplication, and custom-field behavior.

For Vietnamese Korean Murim / Chinese wuxia and related Sino-influenced martial genres, explicitly cover supported distinctions among personal names, titles/ranks/address forms, sects/clans/families/alliances/cults, factions, martial terminology, internal/external arts, movement/footwork/lightness skills, weapon arts, named techniques/forms, realms/ranks, organizations, locations, items, medicines, poisons, and formations. Require Hán-Việt/localized Vietnamese display names instead of default raw romanization while keeping `raw_name` source-faithful for matching.

For other genres, substitute only the ontology supported by `genre-guidance.md` and the supplied sample.

## 3. Glossary Refinement User Prompt = optional project-specific cleanup policy

Generate this file only when the user explicitly requests glossary refinement/cleanup instructions. Otherwise omit it from the pack.

Purpose when requested: paste into Glossarion's optional glossary-refinement User Prompt field while leaving Glossarion's generic refinement System Prompt generic.

Carry only project-specific semantic rules justified by analysis:
- original-language family and target-language localization policy
- canonical identity and duplicate resolution
- full-name preservation and alias handling
- gender-conflict handling
- names, terminology, hierarchy, titles/ranks/forms of address
- institution/faction distinctions
- power-system/technique/item/location distinctions
- Hán-Việt normalization for Vietnamese Sino-influenced projects

Do not duplicate the generic CSV/schema/output-format contract. Do not embed actual glossary rows or novel-specific term mappings.

## Priority during translation

Use this conceptual priority:

1. Current source text: what actually happens and what is actually said.
2. Embedded `<NOVEL_PROFILE>`: style and interpretation conventions for this book.
3. Established glossary: approved canonical translations and identity mappings.
4. Character/relationship context: pronouns and forms of address.
5. Previous translated context: continuity support.

Never let prior context override explicit current-source evidence.

## Priority during glossary refinement

Use this conceptual priority:

1. Existing approved/user canon and directly supported identity evidence.
2. Explicit source-script/Hanzi/Hanja information already present in glossary rows or aliases.
3. Stable project localization policy from the Refinement User Prompt.
4. Conservative deduplication and metadata cleanup.

Do not invent new entities or unsupported historical name etymologies during refinement.
