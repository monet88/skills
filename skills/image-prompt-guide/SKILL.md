---
name: image-prompt-guide
description: Design, rewrite, critique, and optimize prompts for image generation or editing across providers. Use for text-to-image, image-to-image, inpainting, multi-reference composition, photography, product shots, posters and typography, characters, UI mockups, diagrams, or visual-style exploration; skip it when the user only wants an already-final prompt executed unchanged.
metadata:
  author: monet88
  version: "0.1.0"
  homepage: "https://github.com/monet88/skills"
---

# Image Prompt Guide

Turn an image request into a production-ready prompt that can travel across tools. This skill writes or reviews the prompt; it does not generate an image unless the user also asks for generation and an image tool is available.

## Workflow

1. Classify the request as `generate`, `edit`, `inpaint`, or `multi-reference`. Capture the asset purpose, subject/action, canvas, composition, visual direction, exact visible text, reference roles, invariants, and output constraints. Infer ordinary omissions; ask at most one question only when the answer would materially change the result.
2. Search the bundled catalog before drafting. Resolve `<skill-dir>` as the directory containing this file, then run the smallest useful query with the available Python 3 executable:

   ```bash
   python "<skill-dir>/scripts/search.py" "fashion editorial portrait" --domain template -n 3
   python "<skill-dir>/scripts/search.py" "preserve face replace outfit" --mode edit --json
   python "<skill-dir>/scripts/search.py" "poster Vietnamese typography" --provider gemini -n 4
   ```

   Use `python` on Windows and `python3` where that is the Python 3 command. The script is offline and standard-library only. Write one dominant intent in 2-6 meaningful terms. Start without filters when the category is unclear; retry once with `--domain`, `--provider`, or `--mode` if the first result is empty or off-topic. Treat an empty result as no catalog match, not permission to invent a claimed house pattern.
3. Read [references/prompt-construction.md](references/prompt-construction.md) when the request involves editing, multiple references, exact text, multi-panel consistency, UI, infographics, technical diagrams, or when the retrieved pattern needs a fuller schema.
4. Compose one coherent brief. Put canvas/layout before surface detail when structure matters. Use concrete nouns and spatial relationships; control material, lighting, and palette separately. Label literal on-image copy and every reference image precisely. Use short, targeted avoid constraints only for likely failure modes.
5. Run the quality gate below. Revise until every applicable item is explicit and non-contradictory.

## Provider Routing

- If the user names a provider or model, use matching catalog results and preserve its syntax and supported controls. Verify current provider limits before asserting API parameters, sizes, or reference counts.
- For Gemini or Nano Banana, prefer natural-language creative briefs with a clear purpose, physical relationships, and the output specification at the end.
- For GPT Image, prefer explicit canvas/layout contracts, quoted text, and structured sections or JSON-like configuration when many visual systems interact.
- If no provider is named, write a provider-neutral prompt. Default the prompt itself to English for portability unless the user requests another language; preserve all requested visible text verbatim in its original language.

## Quality Gate

- The intended asset and audience are clear.
- Mode, canvas/aspect ratio, and composition do not conflict.
- Subject, action, environment, and spatial relationships are observable.
- Style is bounded; materials, lighting, and palette are concrete rather than praise words.
- Every visible string is quoted, positioned, and assigned a hierarchy.
- Edits state both the change and the invariants; multi-reference prompts assign one role to each input.
- Factual diagrams, historical scenes, maps, products, or current events use verified facts. Use labeled placeholders when verification is unavailable.
- Safety and rights constraints are respected. Do not disguise a real person's identity or rewrite intent to evade a provider safeguard.
- Avoid constraints are brief and tied to plausible failures.

## Output Contract

Unless the user requests another format, return:

1. `Direction`: the selected catalog pattern(s) in one line.
2. `Prompt`: one copyable fenced block with no commentary inside it.
3. `Parameters`: mode, aspect ratio/size, and provider-specific controls only when known.
4. `Reference map`: input roles and invariants, only for edit/inpaint/multi-reference tasks.

For a request that says "prompt only," return only the prompt. For critique, identify the concrete failure modes first, then provide the revised prompt.
