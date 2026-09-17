---
name: image-prompt-guide
description: Design, rewrite, critique, and optimize prompts for image generation or editing across providers, including reverse-engineering a prompt from a supplied image. Use for text-to-image, image-to-image, inpainting, multi-reference composition, photography, product shots, posters and typography, characters, UI mockups, diagrams, or visual-style exploration; skip it when the user only wants an already-final prompt executed unchanged.
metadata:
  author: monet88
  version: "0.2.0"
  homepage: "https://github.com/monet88/skills"
---

# Image Prompt Guide

Turn an image request into a production-ready prompt that can travel across tools. This skill writes or reviews the prompt; it does not generate an image unless the user also asks for generation and an image tool is available.

## Workflow

1. Classify the request as `generate`, `edit`, `inpaint`, `multi-reference`, or `reverse`. Capture the asset purpose, subject/action, canvas, composition, visual direction, exact visible text, reference roles, invariants, and output constraints. Infer ordinary omissions; ask at most one question only when the answer would materially change the result. Use `reverse` when the user supplies an image and wants a prompt that reproduces or imitates it.
2. Search the bundled catalog before drafting. Resolve `<skill-dir>` as the directory containing this file, then run the smallest useful query with the available Python 3 executable:

   ```bash
   python "<skill-dir>/scripts/search.py" "fashion editorial portrait" --domain template -n 3
   python "<skill-dir>/scripts/search.py" "preserve face replace outfit" --mode edit --json
   python "<skill-dir>/scripts/search.py" "poster Vietnamese typography" --provider gemini -n 4
   ```

   Use `python` on Windows and `python3` where that is the Python 3 command. The script is offline and standard-library only. **Pass the user's request in their own language**: the script translates every query into English first (Vietnamese, Chinese, Japanese, Korean, Spanish, French, German, Portuguese, and Indonesian domain terms are covered) and then matches the English catalog. The JSON output reports both `query` (as written) and `query_used` (the English form), and the text output prints the English query when it differs. Write one dominant intent in 2-6 meaningful terms. Start without filters when the category is unclear; retry once with `--domain`, `--provider`, or `--mode` if the first result is empty or off-topic. A result must match at least half of the query's translated terms, so an empty result is a real no-match: fall back to the construction grammar in step 3 rather than inventing a claimed house pattern, and add the missing term to `TRANSLATIONS` in the script when a language keeps missing. Each record's `source` is either `author` (skill-owned guidance), `<owner>/<repo> <path>` (upstream provenance), or a documentation URL.
3. Read [references/prompt-construction.md](references/prompt-construction.md) when the request involves editing, multiple references, exact text, multi-panel consistency, UI, infographics, technical diagrams, or when the retrieved pattern needs a fuller schema. For a `reverse` request, read [references/reverse-prompting.md](references/reverse-prompting.md) instead and keep the analysis internal unless the user asks to see it.
4. Compose one coherent brief. Put canvas/layout before surface detail when structure matters. Use concrete nouns and spatial relationships; control material, lighting, and palette separately. Label literal on-image copy and every reference image precisely. Use short, targeted avoid constraints only for likely failure modes.
5. Run the quality gate below. Revise until every applicable item is explicit and non-contradictory.

## Provider Routing

- If the user names a provider or model, use matching catalog results and preserve its syntax and supported controls. Verify current provider limits before asserting API parameters, sizes, or reference counts.
- For Gemini or Nano Banana, prefer natural-language creative briefs that open with a strong verb, keep positive framing instead of negative lists, and place the output specification at the end.
- For GPT Image 2.5, prefer explicit canvas/layout contracts, quoted text, labeled sections or a JSON config block when many visual systems interact, and a resolved model choice between the speed and quality variants.
- If no provider is named, write a provider-neutral prompt. Default the prompt itself to English for portability unless the user requests another language; preserve all requested visible text verbatim in its original language.

## Quality Gate

- The intended asset and audience are clear.
- Mode, canvas/aspect ratio, and composition do not conflict.
- Subject, action, environment, and spatial relationships are observable.
- Style is bounded; materials, lighting, and palette are concrete rather than praise words.
- Every visible string is quoted, positioned, and assigned a hierarchy.
- Edits state both the change and the invariants; multi-reference prompts assign one role to each input.
- Edits name the single change, the inventory that must survive, and the physical consequences to rebuild.
- Negative phrasing is provider-appropriate: brief avoid lines for GPT Image 2.5, positive framing for Gemini and Nano Banana.
- Provider settings are kept outside the prompt body and a model choice is resolved before quality tuning.
- Reverse prompts lead with the 3-5 reproduction-critical anchors, state the medium boundary, and invent no identity, brand, location, or camera metadata the image does not show.
- Factual diagrams, historical scenes, maps, products, or current events use verified facts. Use labeled placeholders when verification is unavailable.
- Safety and rights constraints are respected. Do not disguise a real person's identity or rewrite intent to evade a provider safeguard.
- Avoid constraints are brief and tied to plausible failures.

## Output Contract

Unless the user requests another format, return:

1. `Direction`: the selected catalog pattern(s) in one line.
2. `Prompt`: one copyable fenced block with no commentary inside it.
3. `Parameters`: mode, aspect ratio/size, and provider-specific controls only when known.
4. `Reference map`: input roles and invariants, only for edit/inpaint/multi-reference tasks.

5. `Verify`: after a generation is available, check the output against the prompt: requested text accurate and legible, diagram labels and relationships correct, identities, product shapes, labels, and reference details intact, only the requested change made, and an actual alpha channel when transparency was required rather than a painted backdrop. Report mismatches as prompt revisions rather than re-rolling blindly.

For a request that says "prompt only," return only the prompt. For critique, identify the concrete failure modes first, then provide the revised prompt. For a `reverse` request, return `Direction`, the prompt, and the medium boundary; show the dimensional analysis only when the user asks for it.
