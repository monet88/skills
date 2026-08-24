---
name: agent-browser-skill-forge
description: "Forges reusable Skill packages from website exploration driven by the installed agent-browser CLI. Use when a user wants to explore a site's internal APIs, build a reusable website extraction or operation Skill, reproduce a browser-visible workflow, automate recurring website work, or turn one-off scraping into a verified reusable capability. Preserves the browser-act-skill-forge lifecycle while using isolated agent-browser sessions, live runtime guidance, a trusted configuration boundary, and a private .agent-forge workspace."
---

# agent-browser-skill-forge

Turns website extraction and operation needs into reusable Agent-callable Skills. It keeps the proven forge lifecycle while using `agent-browser` as the exploration/control plane.

The forge is private by default. Raw network evidence, auth material, generated private clients, and test artifacts stay under `.agent-forge/` until the user explicitly exports accepted output.

## Language

All process output follows the user's language. Generated Skill files are written in English unless the user requests otherwise.

---

`Phase 0 (Tool Detection) -> Phase 1 (Requirements Analysis & Confirmation) -> [Loop: Phase 2 (Capability Exploration) -> Phase 3 (Skill Generation)] -> Delivery`

---

## Phase 0 - Tool Detection and Trusted Runtime Bootstrap

Already completed for the current forge run -> skip.

1. Locate this Skill's `scripts/forge-runtime.py`.
2. From the target workspace, bootstrap a private run:

```text
python <skill-root>/scripts/forge-runtime.py bootstrap --root "<workspace-root>" --task "<short-task-slug>"
```

Bootstrap returns JSON containing `run_id`, `session`, `config`, `version`, and `core_guidance`.

The bootstrap contract is security-sensitive:
- It writes `.agent-forge/` to the workspace `.gitignore` before the first `.agent-forge` artifact is created.
- It verifies live runtime truth using `agent-browser --version` and `agent-browser skills get core --full` through a forge-owned config.
- If live verification fails unexpectedly, it runs `agent-browser doctor --offline --quick` and reports diagnostics.
- It creates an isolated named session. The unnamed/default session is forbidden for forge work.
- Default trusted config uses Chromium (`engine: chrome`) with no plugins.
- Project-level `./agent-browser.json` is not inherited by forge-controlled commands.

3. Read the returned `core_guidance` file before using agent-browser primitives. Live installed guidance wins over copied command syntax.
4. Keep the returned `run_id` for the entire forge run.

### Forge-controlled agent-browser commands

After bootstrap, run browser commands only through the trusted runtime wrapper:

```text
python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- <agent-browser-command>
```

The wrapper always supplies the forge-owned `--config` and isolated `--session`, strips ambient `AGENT_BROWSER_*` startup overrides, and rejects command-line startup flags that could escape the trusted boundary.

Do not bypass this wrapper for forge-controlled exploration merely because raw `agent-browser` works. Raw invocation may auto-discover an unreviewed project config.

### Optional providers, plugins, and stealth

Chromium is the default and has no provider/plugin dependency. If ordinary Chromium is insufficient, an optional provider/plugin configuration may be used only after the user explicitly chooses it or explicitly approves a reviewed installed configuration.

After approval, bootstrap a new run with the reviewed configuration:

```text
python <skill-root>/scripts/forge-runtime.py bootstrap --root "<workspace-root>" --task "<short-task-slug>" --trusted-config "<approved-config.json>"
```

Never silently copy `./agent-browser.json` into the trusted workspace. `plugin add` is not allowed inside a forge-controlled run.

### Runtime refs are ephemeral

Snapshot refs exist only in the live browser state. Use the pattern `snapshot -> resolve target -> act -> re-snapshot after material page/tab/dialog/DOM changes`. Never persist a concrete snapshot ref in generated Skill strategy files, scripts, manifests, or provenance.

## Phase 1 - Requirements Analysis & Confirmation

### 1a. Parse Business Intent

Identify:
- core objective: data to obtain or action to perform;
- target site: explicit URL/platform or a site still needing research;
- execution intent: build-only versus execute-now, including volume/batch needs;
- output/export request: accepted output remains private until explicit export.

If the objective is too vague to explore safely, ask one focused clarification. Otherwise use reasonable defaults.

### 1b. Target Site Research

When no explicit target URL exists, research candidate sites instead of guessing from memory. Rank 1-5 candidates by usefulness and reliability, then let the user select.

### 1c. Task Decomposition and Plan Confirmation

Decompose the workflow into reusable capability units. Classify each unit as extraction or operation and present one complete plan before exploration begins.

Default accepted output location during forging:

```text
.agent-forge/output/<skill-name>/
```

Do not export generated output into the source tree until the user explicitly requests export.

---

## Phase 2 - Capability Exploration

Read exactly one reference for the current capability:
- extraction -> `references/exploration_extraction.md`
- operation -> `references/exploration_operation.md`

Use the current run's trusted wrapper for every agent-browser command. Phase 2 runs one capability at a time.

## Phase 3 - Skill Generation

Read `references/output_template.md` before generating capability output.

Every generated capability must declare its actual runtime classification:
- `DIRECT_API_VERIFIED`
- `BROWSER_SESSION_API`
- `DOM_ONLY`
- `HYBRID`

Observed network traffic is evidence, not proof of a reusable direct API. Keep raw evidence and any private client under `.agent-forge/`.

Generated browser-dependent strategy must resolve element refs at runtime. Do not copy refs observed during exploration into reusable artifacts.

---

## Delivery

1. Validate generated package structure and behavior through its public Skill interface.
2. Keep accepted output under `.agent-forge/output/<skill-name>/` until export is explicit.
3. When the user requests installation, install from the accepted private output directory.
4. When execution intent was part of Phase 1, execute only after the generated capability has passed its required verification.

## Private Workspace Contract

A forge run owns:

```text
.agent-forge/
|-- runs/<run-id>/
|   |-- runtime.json
|   `-- core-guidance.txt
|-- trusted/<run-id>.agent-browser.json
`-- output/<skill-name>/
```

Later phases may add HAR, auth, evidence, client, and test artifacts only inside this boundary unless the user explicitly exports accepted output.
