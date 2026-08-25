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

After all capabilities are generated, proceed in this order:

### 1. Automated Independent Black-Box Testing

Every generated capability must be tested by an independent test agent or harness that receives only:
- the generated Skill package directory (under `.agent-forge/output/<skill-name>/` or exported destination);
- declared runtime prerequisites (Python 3.8+ for direct API; `agent-browser` for browser paths);
- minimal test cases covering all advertised components.

Forge internals, exploration logs, raw HAR files, and coordinator context are not provided to the independent tester.

#### Sub-Agent Test Execution
Dispatch testing via an independent sub-agent using this prompt template:

```
Read {path to generated SKILL.md} as your execution guide.

Test cases:
{minimal test case list, annotating which advertised atomic/composite component each covers}

Execution requirements:
- Follow SKILL.md instructions strictly; do not assume unstated coordinator capabilities or private forge internals.
- For DIRECT_API_VERIFIED: verify by running `client.py` and importing `APIClient` in Python; steady-state testing must not launch agent-browser.
- For BROWSER_SESSION_API / DOM_ONLY / HYBRID: execute via documented agent-browser commands using only standard shell pipelines.
- Record specific issues if instructions are unclear, missing, or require coordinator-specific syntax.

Report after execution:
1. Component results (pass/fail per component)
2. Failure reasons (if any)
3. Unclear parts in SKILL.md instructions (if any)
4. Severe accuracy or performance issues (if any)
5. Output summary (sanitized; never leak raw credentials or secrets)
```

#### Test Execution Rules
- **Component Coverage**: The independent tester must execute each advertised atomic component at least once and execute composite flows end-to-end where applicable.
- **Steady-State Runtime Independence**: For `DIRECT_API_VERIFIED`, test verification imports/runs the generated `client.py` against the verified endpoint without starting `agent-browser`.
- **Secret Redaction**: Test reports must sanitize all outputs; credentials and authorization tokens must never appear in test output logs.
- **No Waiving on Failure**: If a black-box test fails, the generated package files and instructions must be corrected and retested until passing. Do not waive test failures.

### 2. Canonical Skill Installation

Install the generated Skill using the repository's canonical Skill UX:

```bash
npx skills add ".agent-forge/output/<skill-name>" --agent <agent-name> --copy -y
```

Or via the runtime helper:

```bash
python <skill-root>/scripts/forge-runtime.py install-skill --package-dir ".agent-forge/output/<skill-name>" --agent <agent-name>
```

- **Installation Failure Safety**: If installation fails (e.g. invalid target agent or environment issue), report the error clearly. Installation failure must not delete, mutate, or destroy the accepted private output in `.agent-forge/output/<skill-name>/`.

### 3. Report Results

After black-box tests pass and installation completes, report to the user:
- Generated Skill name, path, and bundle files.
- Data coverage: verified fields and endpoints.
- Coverage gaps: uncollected enum parameters (marked `[collection failed]`), missing non-core fields, or unsupported filters.
- Test results summary (components verified, pass/fail status).

### 4. Execute on User Task (when Phase 1 had execution intent)

When the original request included execution intent:
1. Use the installed Skill (or directly execute from the verified private output directory if installation was skipped or failed) to perform the user's task in steady state.
2. Follow the Skill's documented CLI commands or Python import interface.
3. Do not re-enter forge exploration unless deterministic revalidation (`revalidate-skill`) fails with unrecoverable schema drift or architectural change.

---

## Coordinator-Agnostic Instruction Contract

Generated runtime instructions in `SKILL.md`, `README.md`, and scripts must remain completely coordinator-agnostic:
- Assume only standard filesystem + standard shell + Python 3.8+ (and `agent-browser` for browser-dependent paths).
- Must never require ChatGPT-, Claude-, Codex-, Antigravity-, AGY-, OpenCode-, or other coordinator-specific orchestration syntax (e.g. `@agent`, `Subagent:`, `manage_task`, `call_mcp_tool`, `ask_user_question`).
- Must be immediately portable and runnable by any independent agent or developer in a standard terminal.

## Experience & Revalidation Notes Lifecycle

- **Read at Reuse**: Experience notes and revalidation guidance in generated `SKILL.md` are read only when executing or maintaining the Skill.
- **Evidence-Based Updates**: Update notes only when meaningful drift, rate limits, or newly verified endpoint behaviors are observed during real execution.
- Notes must never be used as a substitute for verifiable execution evidence.

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
