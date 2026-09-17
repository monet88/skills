# Prompt Construction Reference

Use only the sections that match the current request. The search catalog supplies the closest pattern; this file supplies the construction grammar. For reverse prompting from a supplied image, use [reverse-prompting.md](reverse-prompting.md) instead.

## Universal Brief

Select the fields that materially control the result and write them as one coherent brief:

```text
PURPOSE: What asset this is and where it will be used.
CANVAS: Aspect ratio, orientation, resolution, and safe areas.
SUBJECT: Identity, count, defining visible traits, and priority.
ACTION: The exact moment, pose, motion, or physical interaction.
ENVIRONMENT: Location, time, weather, atmosphere, and concrete props.
COMPOSITION: Framing, viewpoint, subject placement, depth layers, and negative space.
VISUAL DIRECTION: Medium, production context, bounded style anchors, and finish.
MATERIALS: Specific surfaces, texture, wear, translucency, or fabric behavior.
LIGHTING: Source, direction, softness, color temperature, contrast, and shadows.
PALETTE: Dominant colors, accent colors, and saturation/value relationships.
TEXT: Exact quoted copy, language, type character, position, hierarchy, and readability.
OUTPUT: Final aspect ratio, resolution, background/format needs, and variant count.
AVOID: A short list of likely defects or unwanted defaults.
```

Use 5-12 concrete scene nouns and a few decisive controls instead of adjective stacks such as “beautiful, stunning, professional, 8K.” One dominant capture or rendering context is stronger than several conflicting camera or style systems.

## Generation

Use this order when starting from text:

```text
Create a [asset type] for [purpose/audience].
[Canvas and layout contract].
[Subject] [specific action] in [environment with spatial relationships].
[Composition and viewpoint].
[Medium/style], with [materials], [lighting], and [palette].
[Exact text contract, if any].
[Output specification].
Avoid [targeted failure modes].
```

For reasoning-first image models, write natural prose that reads like a creative director's brief. A useful six-part frame is subject, composition, action, location/atmosphere, style/optics, then output specification.

## Edit and Inpaint

Edit prompts are change contracts, not fresh scene descriptions:

```text
TASK: [single intended transformation].
INPUTS: Image 1 = [base/destination role]; Image 2 = [reference role]; ...
CHANGE: Replace/change/add/remove [target] with [desired result and local integration].
PRESERVE: Keep [identity, pose, geometry, camera, lighting, background, text, brand details] unchanged.
REBUILD: [contact shadow, reflection, occlusion] left stale by the change.
REGION: Modify only [mask or spatial region], if applicable.
OUTPUT: [canvas, crop, fidelity, and finish].
AVOID: [identity drift, geometry drift, edge halos, clipping, text corruption, or other likely defects].
```

Name each reference by index and one role. State how the references interact. Repeat identity, text, geometry, and brand invariants on iterative edits because they otherwise tend to drift. Drift is expected across turns, so treat the preserve list as part of every turn rather than a one-time instruction; when a region must stay pixel-identical, composite the approved edit into the original instead of relying on prompting alone.

Common edit shapes worth naming explicitly:

- **Marked region:** when the user marks, masks, or comments on a region, treat that mark as the region contract, say what may change inside it, and re-state that everything outside stays untouched.
- **Sketch or drawing to render:** the drawing owns layout, proportions, and perspective; the prompt owns materials, light, and finish. Forbid new elements and text.
- **Transparent cutout:** ask for the isolated subject and for an alpha background, forbid drop shadow, halo, checkerboard, and background fill, and name the thin geometry (cords, hair, perforations) that fringes first. Keep PNG without lossy compression and re-state transparency on follow-up turns.
- **Multi-turn chains:** evaluate the whole sequence of edits, not just each step, and restate the invariants whenever drift appears.
- **Upscale or restore:** separate resolution from repair, state the target size, forbid invented detail, and name the specific damage to fix.
- **Localized copy:** quote each replaced string with its target language and hold layout, type character, and artwork fixed; expect longer target strings to need a smaller size rather than a new layout.

## Exact Text and Posters

- Put every literal string in quotation marks and preserve spelling, punctuation, accents, and case.
- Specify language, font character, position, size hierarchy, alignment, and line breaks where important.
- Allocate fixed zones before describing imagery: headline, subject, support copy, CTA, legend, and fine print.
- Distinguish readable copy from decorative letterforms.
- For dense layouts, finalize the copy before image generation and keep paragraphs out of the image.
- For hero posters, design for three viewing distances: the silhouette or theme reads first, the narrative or campaign promise second, and texture, small labels, and background detail only on close inspection.

Poster shape:

```text
Design a [ratio] [poster/cover/ad]. Reserve [zone] for the headline "..." in [type style], [zone] for the subject, and [zone] for supporting copy "...". Establish [largest-to-smallest hierarchy]. [Visual scene and art direction]. Text must be crisp and readable at the intended viewing distance. Avoid garbled characters, fake sponsor marks, and unreadable microtext.
```

## UI, Infographics, and Technical Figures

Treat these as layout specifications:

- Name the artifact and device/canvas first. Slides, report pages, dashboards, charts, and diagrams are artifacts, not concept art: prompt them like a spec.
- Define fixed regions, panels, grids, modules, and their reading order.
- Provide exact labels, values, axes, legends, buttons, and states.
- Define visual semantics: what colors, line styles, arrows, thickness, and icons mean.
- Require consistent alignment and scales across repeated panels.
- Prefer a restrained palette, generous spacing, and publication/product-grade legibility.

For defensive security diagrams, make benign and unsafe flows visually distinct while keeping any example payload inert and explanatory.

## Multilingual and CJK Layouts

- Name the script explicitly when it varies: `Simplified Chinese` or `Traditional Chinese`, Latin, Cyrillic, or a mixed layout.
- Supply every string exactly, in its original language and spelling.
- Define the layout modules and hierarchy that hold each language block.
- Require neat readable text without garbled characters, stray English, or pinyin unless the design calls for it.
- For calligraphic or brush-signage work, name the style (`brush style`, `calligraphy-style labels`, `rice-paper texture`) and avoid decorative glyph clutter.

## Illustration Style Control

- Fix one primary style direction and at most two supporting techniques; the primary controls medium, line, and modeling.
- Describe line language, shape and anatomy language, value structure, palette, and texture distribution instead of stacking artist names.
- Do not combine contradictory treatments: flat vector with heavy oil buildup, no outline with thick closed contours, hard cel bands with continuous watercolor bleed, or matte paper with plastic specular highlights.
- Keep reusable characters, products, and marks original; convert recognizable references into technique.

## Multi-Panel and Character Consistency

- State the exact panel count and grid shape.
- Assign a role, beat, camera view, or state to every panel.
- Lock character identity, proportions, costume, palette, line treatment, and environment motifs across panels.
- Character sheets should name required front/side/back views, expressions, parts, scale, and palette.
- Storyboards should name shot size, viewpoint, camera movement, duration, and continuity relationship.

## Category Mini-Schemas

- **Photography:** purpose + capture context + subject/action + location/time + ordinary imperfections + lighting + crop.
- **Fashion editorial:** garment silhouette/material + pose + location + editorial composition + one optics context + skin/fabric texture + ratio.
- **Product/food:** hero product + material/label invariants + environment + surface + lighting rig + condensation/particles/motion + commercial hierarchy.
- **Architecture/interior:** room/building type + viewpoint/lens feel + spatial layout + materials + light direction + human scale + realistic shadows.
- **Brand system:** original mark/wordmark + palette + typography + packaging/touchpoints + grid + presentation board hierarchy.
- **Illustration:** original subject + medium + line/brush behavior + shape language + palette + scene density + publication context.
- **Data visualization:** chart family + dataset/labels/units + encoding rules + scale + legend + annotations + accessibility/readability.
- **Anime/manga:** style anchor + original characters + action or pose + environment + palette + line and cel-shading direction + IP boundary.
- **Gaming:** game-camera context + HUD elements + playable scene detail + screenshot or monitor realism.
- **Retro/cyberpunk:** board or grid format + named subcharacters and artifacts + two or three neon accents + wet reflective materials + original designs.
- **Tattoo:** tattooable placement + linework and shading tradition + color tradition + negative-space gaps + flash-sheet presentation + no real skin photo.
- **Isometric miniature:** precise isometric angle + tile or footprint logic + named buildings and props + tiny figures + cutaway interiors + ambient occlusion + floating presentation.
- **3D collectible:** reference identity anchors + toy material + base + packaging + studio lighting + collectible scale.
- **Document/publishing:** page size + column grid + contents + figure and caption system + heading hierarchy + page rhythm.
- **History/classical:** single period + clothing system + period objects + deliberate scroll, album, or poster format + restrained medium.

## Provider Notes

Provider capabilities and limits change. Verify against the provider's current documentation before promising exact sizes, quality flags, reference counts, or endpoint behavior; the notes below are the construction defaults, not a parameter reference.

### Gemini and Nano Banana

- Start the prompt with a strong verb naming the primary operation, then write connected natural prose.
- Text-to-image formula: subject + action + location/context + composition + style, with the output specification at the end.
- Multimodal formula: reference images + relationship instruction + new scenario.
- Prefer positive framing: describe the scene you want (`empty street`) instead of the thing to exclude (`no cars`).
- Control the camera and the finish with photography vocabulary: viewpoint and shot size, `f/1.8` shallow depth of field, wide-angle or macro, device character, then lighting (three-point softbox, chiaroscuro, golden-hour backlight) and grading or film stock.
- Use quotes for every rendered string, name the typeface character, and state a target language when localizing; the model handles multilingual rendering well, so write the prompt in one language and ask for the text in another.
- For dense copy, settle the wording in conversation first and then request the image with that exact text.
- When the model can search, use the shape: search or source request + analytical task + visual translation.

### GPT Image 2.5

- Resolve the model before tuning anything: Flare favors speed, Sunburst favors quality. Establish that quality is met, then test the faster model with identical prompt, references, and dimensions.
- Put canvas, ratio, and layout before detailed subject rendering when structure matters; use labeled sections (scene, subject, details, constraints) for complex briefs.
- The measured `quality` level and the prompt are separate levers: compare quality levels before rewriting the prompt, and reserve `xhigh`/`max` for an unmet requirement.
- Quote exact text with its position and typography, say how many times it should appear, and ask for no extra text.
- A JSON config block is a core pattern for complex product, food, UI, or multi-system visuals; resolve every placeholder before generation.
- Camera and lens language is a cue for appearance, not a physical simulation; describe visible details, scale, and atmosphere instead of mood words.
- Edits: say `change only X`, list the details to preserve, name the physics to rebuild, and state exclusions. Restate constraints every turn; composite locally when a region must be pixel-identical.
- Transparent work: request the alpha channel explicitly, use PNG or WebP, forbid drop shadows and halos, and inspect edges on hair, glass, and thin geometry.
- For people and actions, specify framing and interaction: `full body visible, feet included`, gaze direction, and how hands contact objects.
