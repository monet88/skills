# @monet88/skills

A curated collection of production-ready skills for AI coding agents (Claude Code, Cursor, Antigravity, Eve, Codex, etc.).

## Installation

### 1. Using `skills` CLI (Recommended)

Install directly via the standard agent skills manager:

```bash
# Add all skills to the current project
npx skills@latest add monet88/skills

# Install globally (user-level across all projects)
npx skills@latest add monet88/skills -g

# Install a specific skill only
npx skills@latest add monet88/skills --skill agent-browser-skill-forge

# Target a specific agent (e.g., claude-code, cursor)
npx skills@latest add monet88/skills --agent claude-code
```

List available skills in this repo without installing:
```bash
npx skills@latest add monet88/skills --list
```

---

### 2. Manual Installation

Clone this repository and copy the desired skill folder from `skills/<skill-name>` into your agent's skills directory:

| Agent | Global Skills Path | Project-level Skills Path |
| :--- | :--- | :--- |
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **Antigravity / Gemini** | `~/.gemini/antigravity/skills/` | `.gemini/skills/` |
| **Cursor** | `~/.cursor/skills/` | `.cursor/skills/` |

---

## Included Skills

| Skill | Description |
| :--- | :--- |
| [`agent-browser-skill-forge`](skills/agent-browser-skill-forge) | Forges reusable skill packages and direct API clients from website exploration via `agent-browser`. |
| [`ask-impeccable`](skills/ask-impeccable) | Coordinator for Impeccable UI/UX workflows executed inside coding workers. |
| [`image-prompt-guide`](skills/image-prompt-guide) | Design, rewrite, critique, and optimize prompts for image generation and editing models, including reverse-engineering a prompt from a reference image. |
| [`kvpn`](skills/kvpn) | Operate the Kaspersky VPN Unlimited user-space rotating proxy (`kvpn`), WireGuard locations, split-tunnel exclusions, and Windows System Proxy. |
| [`novel-prompt`](skills/novel-prompt) | Create, audit, and optimize Glossarion prompt packs (`system_prompt.md`, `glossary_extract_prompt.md`, optional `glossary_refinement_user_prompt.md`) for Vietnamese fiction translation across Murim, wuxia, xianxia, fantasy, LitRPG, showbiz, Japanese LN and hybrids. |
| [`video-clone`](skills/video-clone) | Clone, remix, or motion-transfer an existing video via Google Flow V2V (`flow edit`, 3–15s) or Create mode (`flow video` First+Last + `gptimg` face-swap) with `360p`/`720p` generation and `1080p` upscaling. |
| [`vids`](skills/vids) | Generate, edit, animate, extend, or upscale AI videos and generate/edit images via `vids`, `flow` (Omni 1.2 V2V + `p0UkFb` upscale), and `gptimg` backed by the shared ShardBrowser pool. |

---

## Development & Testing

Run the test suite:

```bash
npm test
```
