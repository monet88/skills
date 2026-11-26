---
name: vids
description: Generate, edit, animate, or extend AI videos and generate/edit images via Google Vids (`vids` CLI), Google Flow (`flow` CLI), and ChatGPT (`gptimg` CLI) backed by the shared ShardBrowser profile pool. Use whenever the user asks to create/edit/animate/extend video or generate/edit images with Google Vids, vids.new, Google Flow, flow.google.com, or ChatGPT (`gptimg`).
---

# Google Vids, Flow & ChatGPT Image CLIs (`vids` + `flow` + `gptimg`)

Synchronous CLIs backed by the shared **ShardBrowser (`shardx`)** profile pool (`fill-first` default, `--strategy round-robin` optional). Always pass `--json` when calling from an agent.

## Which Tool to Pick

| Need | CLI | Notes |
|---|---|---|
| **`extend`**, **`animate`**, **`create` with `--avatar`**, or `vids.new` UI V2V `edit` (≤10s, native 1080p) | `vids` | Drives `vids.new` UI. `vids edit` rejects human face-swap `--ref` (stalls at 27%); non-face background `--ref` works. |
| **Image (`T2I`, `I2I`)**, **`T2V` / `I2V` / `R2V` (up to 10 `--ref`)**, **V2V `edit` / Motion Transfer** (`3–15s`, up to 5 `--ref`, gen `360p`/`720p`), + **post-gen `720p`/`1080p`/`4K` upscale** | `flow` | Drives `flow.google.com` (`Omni 1.2` / `Veo` / `Nano Banana`). `flow edit` supports `--start`/`--end` slicing (`3–15s`) and `--resolution 360p` (1/3 credits); `--upscale 1080p` / `flow upscale` is free `≤10s` (`1–5` credits `11–15s`; `4k` = `50–75` credits Ultra; direct `360p → 1080p` supported). |
| **Human face/hair swap & image editing (`T2I`, `I2I`)** via ChatGPT | `gptimg` | Drives `chatgpt.com` (good for face/hair swap where Google Flow/Vids refuses human portraits). |

## Prerequisites

- **ShardBrowser Launcher** running locally (`127.0.0.1:40325`).
- Shared pool uses ShardX tag `vids` (`vids pool add <name>`), falling back to the default profile if untagged.

## `vids` Commands (Google Vids)

- **Input video limit for `edit` / `extend`:** **Max 10 seconds** (H.264 + AAC MP4 recommended; `vids` rejects >10.5s videos up front). For longer videos, split into ≤10s H.264 segments first with `ffmpeg`, process each segment, then concat + mux original audio:
  ```bash
  ffmpeg -y -ss 0 -i input.mp4 -t 10 -c:v libx264 -preset fast -crf 23 -c:a aac seg1.mp4
  ```

```bash
vids create --prompt "..." --aspect 9:16 --resolution 720p --duration 10 --avatar KoreaGirl --output out.mp4 --json
vids edit --input clip.mp4 --prompt "..." --ref bg.png --aspect 9:16 --resolution 720p --output edited.mp4 --json
vids animate --input frame.png --prompt "..." --aspect 9:16 --resolution 720p --output anim.mp4 --json
vids extend --input clip.mp4 --prompt "..." --aspect 16:9 --resolution 720p --output extended.mp4 --json

# Design & save a custom avatar (4-step wizard)
vids avatar create --name KoreaGirl --gender Female --age "Young adult" --race "East Asian" --outfit Casual --details "..." --voice Nyla --json
```

## `flow` Commands (Google Flow)

```bash
# Image (T2I, or I2I when --ref is passed)
flow image --prompt "..." --aspect 9:16 --output out.jpg --json
flow image --prompt "..." --ref base.jpg style.jpg --aspect 9:16 --output edited.jpg --json

# Video (T2V / I2V 1-frame / R2V up to 10 --ref: --duration 3..15; First+Last: --duration 3..10; gen 360p|720p + optional --upscale 720p|1080p|4k)
flow video --prompt "..." --aspect 9:16 --duration 12 --resolution 360p --output t2v_draft.mp4 --json
flow video --prompt "..." --first-frame start.jpg --last-frame end.jpg --aspect 9:16 --duration 5 --resolution 720p --upscale 1080p --output fl_1080p.mp4 --json
flow video --prompt "..." --ref img1.jpg img2.jpg --aspect 9:16 --duration 10 --output r2v.mp4 --json

# Video-to-Video Edit / Motion Transfer (Omni 1.2 jIps6, 3..15s segment, up to 5 --ref images, 360p = 1/3 credits)
# Note: `flow video --ref-video <clip>` aliases this same V2V mode (single video, up to 5 --ref).
flow edit --input source.mp4 --ref char.png --prompt "..." --start 0 --end 10 --aspect 9:16 --resolution 360p --output edited_draft.mp4 --json

# Post-gen Download / Upscale (`720p`/`1080p` free <=10s, 1-5 credits 11-15s; `4k` = 50-75 credits Ultra; direct 360p -> 1080p works)
# Always pass the original media_id (not *_upsampled). Built-in --min-interval 15 pacing + UNUSUAL_ACTIVITY 15-min cooldown + as29s cache reuse prevent burst rate-limits.
flow upscale --media-id <orig_id> --resolution 1080p --output out_1080p.mp4 --json
```

## `gptimg` Commands (ChatGPT Image)

```bash
# Text-to-image or multi-ref image editing (e.g. face/hair swap)
gptimg image --prompt "..." --aspect 9:16 --output out.png --json
gptimg image --prompt "..." --ref face.jpg target.png --aspect 9:16 --model "GPT-6" --effort xhigh --output swapped.png --json
```

## Shared Pool & Rotation

```bash
vids pool list --json   # or: flow pool list --json / gptimg pool list --json
vids pool add <profile>
vids pool remove <profile>
vids pool reset
```

- Default: `--strategy fill-first`. Pass `--strategy round-robin` to rotate, or `--profile <name>` to pin one account.