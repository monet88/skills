---
name: video-clone
description: Clone, remix, or reverse-engineer an existing video while swapping face, hair, body, or background using Create mode (First+Last frame / dynamic duration) instead of Video Edit. Orchestrates yt-upload, /watch (Gemini 1:1 motion analysis), ffmpeg keyframe extraction, gptimg clean swaps, flow/vids dynamic-duration rendering, audio muxing, and optional VeoWatermarkRemover. Use when asked to clone a video, swap face/body/background in a video, or recreate a reference video's motion 1:1.
---

# Video Clone (Create Mode + Dynamic Duration)

Recreate a reference video 1:1 with a swapped face, hair, body, or background without Video Edit mode (which Google Vids/Flow blocks for human face-swap).

## Prerequisites

- **ShardBrowser Launcher** running locally (`127.0.0.1:40325`) with a profile in the shared Pool (`vids pool list --json`) signed into `chatgpt.com` and `flow.google.com`.
- CLIs on `PATH`: `yt-upload`, `ffmpeg`, `ffprobe`, `gptimg`, `flow`, `vids`, plus the `/watch` skill (`GEMINI_API_KEY`) and optional `VeoWatermarkRemover` (`remove-video-watermark.ps1`).

## Workflow

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

Render each segment with its exact dynamic duration using **Omni 1.2 Flash**:

- **First + Last frame (`3–10s`):**
  ```powershell
  flow video `
    --first-frame swapped\seg1_first.png `
    --last-frame swapped\seg1_last.png `
    --aspect 9:16 `
    --duration 6 `
    --prompt "<chronological 1:1 motion prompt from Step 1; keep exact face, outfit, props, and background unchanged>" `
    --output clips\seg1.mp4 `
    --json
  ```
- **Single-frame long shots (`11–15s`):** use `flow video --first-frame ... --duration <11..15>` or `vids animate --input ... --duration <3..15>` (or split into two chained First+Last clips sharing a swapped mid-frame).
- Run sequentially on a single ShardX profile, or pass `--strategy round-robin` when the Pool has multiple profiles.

**Done when:** Every `clips/segN.mp4` returns `ok: true` and `ffprobe` confirms the expected duration.

### Step 5 — Stitch Segments & Mux Original Audio (`ffmpeg`)

```powershell
ffmpeg -y -i clips\seg1.mp4 -i clips\seg2.mp4 -i clips\seg3.mp4 -i input.mp4 `
  -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" `
  -map "[v]" -map "3:a" -c:v libx264 -crf 18 -preset fast -c:a aac -shortest `
  cloned_raw.mp4
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

- **Rate limits (`PUBLIC_ERROR_UNUSUAL_ACTIVITY`):** If Flow flags rapid probing/requests on a single profile, wait ~15 minutes or rotate to another Pool profile instead of retrying in a tight loop.
- **Resolution:** Flow First+Last frame outputs `720x1280` (`9:16`); upscale afterward if `1080x1920` is required.
- **Keep clean images:** Never feed watermarked frames into Flow or Vids.
