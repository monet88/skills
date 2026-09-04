# Prompt Construction Reference

Use only the sections that match the current request. The search catalog supplies the closest pattern; this file supplies the construction grammar.

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
REGION: Modify only [mask or spatial region], if applicable.
OUTPUT: [canvas, crop, fidelity, and finish].
AVOID: [identity drift, geometry drift, edge halos, clipping, text corruption, or other likely defects].
```

Name each reference by index and one role. State how the references interact. Repeat identity, text, geometry, and brand invariants on iterative edits because they otherwise tend to drift.

## Exact Text and Posters

- Put every literal string in quotation marks and preserve spelling, punctuation, accents, and case.
- Specify language, font character, position, size hierarchy, alignment, and line breaks where important.
- Allocate fixed zones before describing imagery: headline, subject, support copy, CTA, legend, and fine print.
- Distinguish readable copy from decorative letterforms.
- For dense layouts, finalize the copy before image generation and keep paragraphs out of the image.

Poster shape:

```text
Design a [ratio] [poster/cover/ad]. Reserve [zone] for the headline "..." in [type style], [zone] for the subject, and [zone] for supporting copy "...". Establish [largest-to-smallest hierarchy]. [Visual scene and art direction]. Text must be crisp and readable at the intended viewing distance. Avoid garbled characters, fake sponsor marks, and unreadable microtext.
```

## UI, Infographics, and Technical Figures

Treat these as layout specifications:

- Name the artifact and device/canvas first.
- Define fixed regions, panels, grids, modules, and their reading order.
- Provide exact labels, values, axes, legends, buttons, and states.
- Define visual semantics: what colors, line styles, arrows, thickness, and icons mean.
- Require consistent alignment and scales across repeated panels.
- Prefer a restrained palette, generous spacing, and publication/product-grade legibility.

For defensive security diagrams, make benign and unsafe flows visually distinct while keeping any example payload inert and explanatory.

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

## Provider Notes

### Gemini and Nano Banana

- Use a purpose anchor such as campaign, editorial, field guide, storyboard, or product mockup.
- Prefer natural prose and explicit physical/spatial relationships over comma-separated tag soup.
- Put the requested output resolution and aspect ratio at the end.
- For multiple inputs, describe the relationship among them and the new scenario.

### GPT Image

- Put canvas, ratio, and layout before detailed subject rendering when structure matters.
- Quote exact text and specify typography hierarchy.
- JSON-like configuration is useful for complex product, food, UI, or multi-system visuals.
- Edit prompts should name the transformation first and preserve invariants explicitly.

Provider capabilities and limits change. Verify current documentation before promising exact sizes, quality flags, reference counts, or endpoint behavior.
