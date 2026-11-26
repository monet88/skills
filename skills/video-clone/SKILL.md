---
name: video-clone
description: Clone, remix, or motion-transfer an existing video while swapping character, face, hair, style, or background via Google Flow V2V (`flow edit`, 3-15s) or Create mode (`flow video` First+Last frame + `gptimg` for human face-swap). Orchestrates `flow edit`/`flow video` (`360p`/`720p`) + `--upscale 1080p`/`flow upscale`, `yt-upload`, `/watch`, `ffmpeg`, `gptimg`, audio muxing, and optional VeoWatermarkRemover. Use when asked to clone a video, motion-transfer a clip, swap face/character/style/background, or recreate a reference video's motion 1:1.
---

# Video Clone (V2V Motion Transfer & Create Mode)

Recreate a reference video 1:1 with a swapped character, face, hair, style, or background.

## Choose Mode (Pick First)

| Mode | When to Use | Path & Limits |
|---|---|---|
| **Mode A — V2V Motion Transfer (`flow edit`)** | Swapping character, costume, style, prop, or background while preserving 1:1 original motion, camera, and timing directly from the source video. | `3–15s` per `--start`/`--end` slice, up to 5 `--ref` images, gen `360p` (1/3 credits) or `720p` + `--upscale 1080p`. Fall back to Mode B if Flow refuses or drifts on direct human face-swap. |
| **Mode B — Create Mode (`gptimg` + `flow video` First+Last)** | Strict human face/hair swap (where Google Flow/Vids V2V refuses human portraits) or full frame-locked scene redesign. | `yt-upload` + `/watch` → `ffmpeg` keyframes → `gptimg` swaps → `flow video` (`3–10s` First+Last or `3–15s` 1-frame, `360p`/`720p` + `--upscale 1080p`). |

## Prerequisites

- **ShardBrowser Launcher** running locally (`127.0.0.1:40325`) with a profile in the shared Pool (`vids pool list --json`) signed into `chatgpt.com` and `flow.google.com`.
- CLIs on `PATH`: `yt-upload`, `ffmpeg`, `ffprobe`, `gptimg`, `flow`, `vids`, plus the `/watch` skill (`GEMINI_API_KEY`) and optional `VeoWatermarkRemover` (`remove-video-watermark.ps1`).

---

## Mode A — V2V Motion Transfer (`flow edit`)

1. **Inspect source duration & plan segments (`ffprobe`):**
   - Measure total duration with `ffprobe`. Split clips `>15s` evenly into `3–15s` segments so no tail segment is `<3s` (e.g. `16s` → `0..8` and `8..16`; `flow edit` fails fast on segments `<3s` or `>15s`).
2. **Confirm swap spec with user (unless already specified):**
   - Swap prompt, up to 5 watermark-free `--ref` images, and resolution (`--resolution 360p` for 1/3-credit drafts vs `--resolution 720p --upscale 1080p` for final).
3. **Render segments (`flow edit`):**
   ```powershell
   flow edit `
     --input input.mp4 `
     --ref char.png `
     --start 0 --end 10 `
     --aspect 9:16 `
     --resolution 360p `
     --prompt "<describe the swap while preserving original subject motion, framing, and lighting>" `
     --output clips\seg1.mp4 `
     --json
   ```
   - To upgrade an approved `360p` or `720p` draft directly to `1080p` without re-generating (0 credits for `≤10s`, `1–5` credits for `11–15s`), pass its **original** `media_id` to `flow upscale`:
     ```powershell
     flow upscale --media-id <orig_media_id> --resolution 1080p --output clips\seg1_1080p.mp4 --json
     ```
   - Or render final directly with `--resolution 720p --upscale 1080p` (`flow video --ref-video input.mp4` aliases single-clip V2V without `--start`/`--end`).

**Done when:** Every `clips/segN.mp4` returns `ok: true`, `ffprobe` confirms expected duration (`3–15s`) and resolution, and visual inspection passes (switch to Mode B if Flow refuses human face-swap). Proceed to **Shared Finish (Step 5 & Step 6)**.

---

## Mode B — Strict Human Face-Swap: Create Mode (`gptimg` + `flow video`)

### Step 1 — Upload & Analyze 1:1 Motion (`yt-upload` + `/watch`)

Upload the source video as `unlisted` so Gemini watches it server-side and plans natural scene cuts with dynamic durations:

```powershell
yt-upload input.mp4 --title "clone-source-analysis" --privacy unlisted
# -> https://youtu.be/<id>

python "<WATCH_SKILL_DIR>/scripts/watch.py" "https://youtu.be/<id>" --question "Analyze this video for 1:1 recreation in Create mode (First+Last frame). Divide it into smooth, natural segments aligned to scene cuts with dynamic durations (3-10s per First+Last segment; split any single shot >10s at a clean mid-pose). For each segment output: exact sharpest first_ts, last_ts, integer duration_s, and a second-by-second motion breakdown (posture, weight/hip shifts, torso rotation, hand/prop motion, head tilts, gaze, expressions, hair sway, camera framing)."
```

*(If Gemini returns `INVALID_MEDIA`, wait 30–60s for YouTube transcoding and retry.)*

**Done when:** Every segment has explicit `first_ts`, `last_ts`, integer `duration_s` (`3–10s` for First+Last; `3–15s` if 1-frame only), and a chronological 1:1 motion prompt.

### Step 2 — Extract Sharp Keyframes (`ffmpeg`)

Extract each keyframe with its own `-ss` invocation (chaining multiple `-ss -i` in one `ffmpeg` call without `-map` duplicates input 0). For two contiguous segments inside the same continuous shot, reuse the previous segment's `last` image as the next segment's `first` image so cuts stay seamless.

```powershell
@(@(1.2,"seg1_first"),@(7.2,"seg1_last"),@(10.8,"seg2_first"),@(18.8,"seg2_last")) | ForEach-Object {
  ffmpeg -y -ss $_[0] -i input.mp4 -frames:v 1 "frames\$($_[1]).png" -loglevel error
}
```

**Done when:** Every extracted PNG is visually inspected and sharp (no motion blur or mid-blink; nudge `±0.2s` if blurry).

### Checkpoint A — Confirm Swap Spec with User (Before `gptimg`)

Before running `gptimg`, pause and present the planned segments (`duration_s` + extracted keyframes) and confirm with the user (skip only if already fully specified in the request):
- Which **face / hair / body / background** reference image(s) or changes to apply.
- What must stay **100% unchanged** (outfit, props, lighting, background).
- Whether the segment cuts and dynamic durations look right.

### Step 3 — Swap Face / Hair / Body / Background (`gptimg`)

Save all swapped keyframes into one dedicated folder (e.g. `<work_dir>/swapped/`), running `gptimg` per keyframe (opens a fresh ChatGPT chat per image to prevent cross-shot drift):

```powershell
gptimg image `
  --prompt "Swap the face and hair of the person in image 2 with the person in image 1. Keep 100% of the outfit, accessories, pose, expression, camera angle, lighting, and background from image 2 unchanged. Output vertical 9:16." `
  --ref face.jpg frames\seg1_first.png `
  --aspect 9:16 `
  --effort xhigh `
  --output swapped\seg1_first.png `
  --json
```

- When swapping **background or body** too, pass a fixed reference image in `--ref` (or describe one identical scene across all keyframes) so lighting and floor perspective stay consistent across cuts.
- Keep outputs watermark-free; images with an AI sparkle watermark (e.g. Gemini) are frequently dropped silently by Google Flow.

**Done when:** Every swapped PNG is saved in `<work_dir>/swapped/`, is watermark-free, and is visually verified for identity, outfit, and scene consistency.

### Checkpoint B — User Review Before Video Render (Before `flow` / `vids`)

Pause and share the `<work_dir>/swapped/` folder and clickable links to all swapped keyframes with the user. Ask whether they want to review/approve (or re-swap any frame) before spending Flow/Vids credits on Step 4. Proceed to Step 4 only after the user confirms.

### Step 4 — Render Dynamic-Duration Clips (`flow video` / `vids animate`)

Render each segment with its exact dynamic duration using **Omni 1.2 Flash** (`--resolution 360p` for cheap drafts, or `--resolution 720p --upscale 1080p` for final; approved drafts can also upgrade via `flow upscale --media-id <orig_id> --resolution 1080p`):

- **First + Last frame (`3–10s`):**
  ```powershell
  flow video `
    --first-frame swapped\seg1_first.png `
    --last-frame swapped\seg1_last.png `
    --aspect 9:16 `
    --duration 6 `
    --resolution 720p `
    --upscale 1080p `
    --prompt "<chronological 1:1 motion prompt from Step 1; keep exact face, outfit, props, and background unchanged>" `
    --output clips\seg1.mp4 `
    --json
  ```
- **Single-frame long shots (`11–15s`):** use `flow video --first-frame ... --duration <11..15>` or `vids animate --input ... --duration <3..15>` (or split into two chained First+Last clips sharing a swapped mid-frame).
- Run sequentially on a single ShardX profile (built-in `--min-interval 15` pacing spaces requests automatically), or pass `--strategy round-robin` when the Pool has multiple profiles.

**Done when:** Every `clips/segN.mp4` returns `ok: true` and `ffprobe` confirms the expected duration.

---

## Shared Finish

### Step 5 — Stitch Segments & Mux Original Audio (`ffmpeg`)

- **Multi-segment clips:**
  ```powershell
  ffmpeg -y -i clips\seg1.mp4 -i clips\seg2.mp4 -i clips\seg3.mp4 -i input.mp4 `
    -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" `
    -map "[v]" -map "3:a" -c:v libx264 -crf 18 -preset fast -c:a aac -shortest `
    cloned_raw.mp4
  ```
- **Single-segment Mode A clip** (replace generated audio with original audio without re-encoding video):
  ```powershell
  ffmpeg -y -i clips\seg1.mp4 -i input.mp4 -map 0:v -map 1:a -c:v copy -c:a aac -shortest cloned_raw.mp4
  ```

**Done when:** `ffprobe` confirms video (`h264`), audio (`aac`), expected total duration, and non-zero file size.

### Step 6 — Optional: Remove Veo / Flow Watermark (`VeoWatermarkRemover`)

Inspect one frame from `cloned_raw.mp4` first. **Run this step only if a visible `"Veo"` wordmark or Gemini diamond is present in the bottom-right corner** (e.g. non-Ultra / `vids` outputs). Skip on watermark-free Flow AI Ultra outputs to avoid false-positive removal.

```powershell
pwsh -File "<VEO_WATERMARK_REMOVER>/remove-video-watermark.ps1" -InputVideo "cloned_raw.mp4" -OutputVideo "cloned_clean.mp4"
```

*(Optional: upload the final MP4 with `yt-upload` for review; confirm with user before deleting the temporary `unlisted` source video via `yt-upload --delete`.)*

**Done when:** Final MP4 is visually watermark-free and passes `ffprobe` with matching duration and audio.

## Guardrails

- **Rate limits (`PUBLIC_ERROR_UNUSUAL_ACTIVITY`):** `flow` enforces `--min-interval 15` (15s spacing per profile), caches already-upsampled clips via `as29s`, and marks `UNUSUAL_ACTIVITY` profiles into a 15-minute cooldown; avoid tight manual retry loops (`--min-interval 0`).
- **Resolution & Upscaling:** Generation supports `360p` (1/3 credits for drafts) and `720p` (default). Post-generation `--upscale 720p|1080p|4k` (or `flow upscale`) upgrades to `1080p` (`0` credits `≤10s`, `1–5` credits `11–15s`; direct `360p → 1080p` supported) or `4k` (`50–75` credits Ultra). Always pass the **original** `media_id` — Flow rejects `*_upsampled` IDs as input.
- **`flow edit` hard bounds:** Segment duration must be `3–15s` (fails fast `<3s`), with at most `5` `--ref` images.
- **Keep clean images:** Never feed watermarked frames into Flow or Vids.
