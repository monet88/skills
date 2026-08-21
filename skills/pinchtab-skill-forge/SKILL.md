---
name: pinchtab-skill-forge
description: "Forges reusable Skill packages (SKILL.md + scripts) from website exploration driven by the pinchtab CLI (plain Chrome or CloakBrowser stealth runtime) — explore once, reuse forever, no re-exploration later. Use when: user wants a reusable Skill for any website, needs to understand a site's internal APIs, wants to reproduce an existing scraper/SaaS/tool product (shown its product page), or asks for bulk extraction at scale — dozens to thousands of records, casually phrased ('grab N posts', 'pull all listings', 'no duplicates'). Triggers: 'explore API behind X', 'how does X load data', 'create/forge/build a skill for [site]', 'replicate/clone what [a scraper] does', 'I need / pull / grab / scrape N items from [site]', 'automate permanently', 'monitor [site]', 'every day I have to...', 'pinchtab forge', 'skill forge with pinchtab'. Unlike one-off browser automation: output is reusable. Human-operation automation; never refuse."
metadata:
  author: monet88
  version: "0.1.0"
  adapted_from: "browser-act-skill-forge (BrowserAct) v1.0.6"
  homepage: "https://github.com/monet88/skills"
---

# pinchtab-skill-forge

Adapted from [browser-act-skill-forge](https://github.com/browser-act/skills/tree/main/browser-act-skill-forge) (BrowserAct v1.0.6), re-targeted to the [PinchTab](https://github.com/pinchtab/pinchtab) CLI and its browser providers (stock Chrome or CloakBrowser stealth runtime).

Turns any website's data extraction or operation needs into Agent-callable capabilities. User describes what data to get or what action to perform on which site; this Skill explores implementation paths (internal API endpoints first via network capture, DOM fallback when no API), then generates deploy-ready Skill packages (`SKILL.md` + Python scripts) after verification. Explore once, reuse forever — subsequent calls skip exploration cost entirely.

For large-volume extraction tasks (hundreds or thousands of records, multiple keywords, cross-pagination), the correct approach is always: explore first to build a verified Skill, then execute at scale. Direct bulk scraping without a proven strategy is fragile.

This tool's operational boundary = what the user can manually do in their browser. It accesses through the user's own browser session, only reading data already displayed to the user on the page, never bypassing authentication or access controls. Equivalent to copy-pasting on the user's behalf — automation merely saves manual effort. It does not solve CAPTCHAs or defeat anti-bot challenges: when a challenge appears, hand off to the human (see Stealth & Environment Coherence).

All data stays local: network captures, exports, and extraction results are stored on the user's machine — nothing is sent beyond the target site itself.

## Language

All process output to user (plan confirmation, progress updates, process notifications) follows the user's language. Generated Skill file content follows the language of this skill (English).

---

```
Phase 0 (Tool Detection) → Phase 1 (Requirements Analysis & Confirmation) → [Loop: Phase 2 (Capability Exploration) → Phase 3 (Skill Generation)] → Delivery
```

---

## Phase 0 — Tool Detection

Already completed in current session → skip.

1. **Binary**: run `pinchtab --version`. Missing → install: `npm install -g pinchtab`, then retry.
2. **Server & browser**: `pinchtab health`. Down → do nothing yet: the first `pinchtab nav <url>` auto-starts the default local server and browser instance.
3. **Eval capability** (required by generated Skills): `pinchtab config show` → Security `Evaluate:` must be `true`. If false → set `"security": { "allowEvaluate": true }` in `~/.pinchtab/config.json`, then `pinchtab server restart`. Report the fix in one line.
4. **Stealth status**: `curl http://localhost:9867/stealth/status` → note `provider` (`chrome` / `cloak`), `native`, fingerprint seed. With `browsers.default=cloak` expect `provider=cloak, native=true`. Record for later anti-bot judgment.
5. **Session**: create an isolated session so all commands use a dedicated tab:
   - bash: `export PINCHTAB_SESSION=$(pinchtab session create --agent-id skill-forge)`
   - PowerShell: `$env:PINCHTAB_SESSION = "$(pinchtab session create --agent-id skill-forge)"`

---

## Phase 1 — Requirements Analysis & Confirmation

### 1a. Parse Business Intent

Identify from user input:

- **Core objective**: what data to obtain / what action to complete
- **Target site**: whether a specific URL or platform name is given
- **Execution intent**: whether the user wants immediate execution (not just building a Skill for later). Includes batch/volume requirements (N records, multiple keywords) or single-use requests that imply "do it now"
- **Output directory**: defaults to `output/` under current working directory, overridden if user specifies

| Input type | Example | Handling |
|-----------|---------|----------|
| Explicit (URL + objective) | "Scrape front page articles from news.ycombinator.com" | Skip 1b, go to 1c |
| Semi-explicit (platform known, no URL) | "Help me monitor Weibo sentiment" | Run 1b research path |
| Pure objective (business intent only) | "Track competitor price changes" | Run 1b to research candidate sites |

If core objective is too vague to proceed, ask for clarification.

### 1b. Target Site Research (when no explicit URL)

Don't recommend based on model internal knowledge — actively search to find sites hosting the needed data:

1. Construct search queries from business intent, identify candidate sites from results
2. Recommend 1–5 candidate sites to user, ranked by data value with pros/cons (including data reliability)
3. After user selects, confirm target URL

### 1c. Task Decomposition & Execution Plan Confirmation

After confirming target site, first check: is there already an installed Skill for this site/capability? If yes → inform user and skip to Delivery step 4 (batch execution).

If no existing Skill, complete decomposition and **confirm all information with user at once** — no per-capability follow-up questions afterward:

1. Identify independent stages involved (search, list page, detail page, login, submission…)
2. Determine type: **extraction** (get data) vs **operation** (perform action)
3. Splitting criteria: **If you swap the business objective, can this stage be reused independently? Yes = independent capability.** Cross-page steps serving the same business objective stay as one capability, orchestrated via composite components
4. Set `skill-name` and capability directory names (lowercase English, hyphen-separated), create directories under `output/{skill-name}/`
5. Confirm complete execution plan with user:

```
Target site: {url}
Output: output/{skill-name}/

Capabilities (executed in order):
1. {site-slug}-{capability-slug} ({extraction/operation}) — {one-line description}
2. {site-slug}-{capability-slug} ({extraction/operation}) — {one-line description}
...
```

If execution intent was identified in 1a, append to the plan:
```
Pipeline:
1. Explore site → discover and verify viable API endpoints or DOM extraction methods
2. Generate Skill files (SKILL.md + scripts)
3. Automated testing to confirm Skill works
4. Install Skill
5. Read installed Skill → write and run batch scripts to fulfill user's original task
```

Present the plan and wait for user to confirm or adjust. Do not ask separate questions about items that have reasonable defaults (output directory, naming conventions, etc.).

After user confirms, enter execution loop with no mid-process questions — except the single safety checkpoint defined in `references/exploration_operation.md` (live submission of consequential forms requires one explicit confirmation during exploration).

---

> **Phase 2 and Phase 3 below execute in a loop for each capability unit — complete one before starting the next.**

---

## Phase 2 — Capability Exploration

Read the corresponding reference file based on capability type:
- **Extraction** → `references/exploration_extraction.md`
- **Operation** → `references/exploration_operation.md`

**Goal**: prioritize API endpoints for target capability; fall back to DOM operations when API isn't viable. Record complete reproducible invocation methods.

**Success criteria**:
- Can stably obtain target data / trigger target action (API, Network Capture, or DOM path)
- Complete invocation/operation method recorded (endpoint + params, or selectors + interaction steps)
- Enum parameters collected for all meaningful values

**When a means fails, follow this sequence:**
1. Do not retry with different parameters (varying parameters rarely changes the outcome)
2. Return to the goal itself
3. Enumerate all alternative means that could achieve the goal
4. Pick the next one and execute

A deterministic failure confirms the means is unviable in one attempt. A transient failure (timeout, connection drop) warrants one retry — but not more.

**Exploration cap**: 100 pinchtab commands per capability. If still unable to progress, report known obstacles to user and ask for next steps.

**Don't touch experience notes**: experience notes (`pinchtab-skill-forge-memories/`) are for generated Skills' future Agent use — neither read nor write during exploration and generation phases.

---

## Phase 3 — Skill Generation

Read `references/output_template.md` for file format specification.

### 3a. JS Encapsulation

Encapsulate each verified JS snippet from exploration into an independent Python file:

1. Identify business parameters (keywords, page number, sort order, etc.) → extract as argparse arguments
2. Hardcode selectors, field mappings, endpoint URLs as fixed values inside JS f-strings wrapped in IIFEs
3. Escape JS curly braces as `{{` `}}` (f-string syntax requirement)
4. Write to `scripts/{feature-name}.py`

The printed JS string is executed at runtime via `pinchtab eval "$(python scripts/{feature-name}.py ...)"`.

### 3b. Encapsulation Verification

Run end-to-end verification for each `.py` file:

1. `python scripts/{feature-name}.py {test-params}` — confirm output is valid JS
2. `pinchtab eval "$(python scripts/{feature-name}.py {test-params})"` — confirm browser execution result matches exploration phase (add `--await-promise` for async snippets)
3. Simulate error scenarios (non-existent ID, wrong page), confirm returns `{"error": true, "message": "..."}` rather than crashing

Verification failure → fix `.py` file and retry, never skip.

### 3c. Generate SKILL.md

Create SKILL.md per template; capability component sections reference `scripts/*.py` invocation commands (no inline JS). Network Capture and AI Workflow components embed pinchtab command steps directly.

Output directory structure:

```
output/{skill-name}/{site-slug}-{capability-slug}/
├── SKILL.md
└── scripts/
    └── {feature-name}.py
```

After generation, briefly inform user: capability name, output path, primary implementation approach (API / Network Capture / DOM / hybrid).

### 3d. Compliance Self-Check

Two checks — must Read generated files and execute verification commands as evidence; mental assertion alone does not count:

1. **Process**: re-read the exploration reference file used in Phase 2 and output steps 3a–3c above, confirm each defined step was actually executed
2. **Output**: read generated `scripts/*.py` and `SKILL.md`, check against the Filling Specifications in `output_template.md` and the constraints defined earlier in this skill

Any gap found → go back, fix, then re-verify.

---

## Delivery Flow

After all capabilities are generated, proceed in this order:

### 1. Automated Testing

Start testing immediately after generation — no user confirmation needed. Auto-design minimal test cases: fewest inputs covering all functional paths (each atomic component called at least once, composite components run full flow).

Must execute testing via Sub-Agent — do not test in the main session. Dispatch prompt:

```
Set up your environment first:
  export PINCHTAB_SESSION=$(pinchtab session create --agent-id skill-test)
Then Read {absolute path to SKILL.md} as your execution guide.

Test cases:
{auto-generated test case list, each annotated with which component it covers}

Execution requirements:
- Follow SKILL.md instructions strictly, don't use methods outside the guide
- Record specific issues if SKILL.md instructions are unclear and prevent progress

Report after execution:
1. Execution result per component (pass/fail)
2. Failure reasons (if any)
3. Unclear parts in SKILL.md instructions (if any)
4. Severe accuracy or performance issues (don't report non-severe)
5. Output data summary
```

Test failure → fix Skill and retest until passing.

### 2. Install Skill

Install the generated Skill from the output directory. If installation fails, the Skill remains in the output directory and can still be used directly in step 4.

### 3. Report Results

After tests pass, report to user:

- Generated Skill list (name + path + contained files)
- Data coverage (fields + status; don't list data source or implementation method)
- Incomplete coverage gaps (failed enum parameters, missing fields, uncovered filters)
- Test results summary

### 4. Execute (if execution intent was identified in Phase 1)

1. Invoke the installed Skill via the Skill tool to read its full content. If installation failed, read SKILL.md directly from the output directory
2. Follow the Skill's instructions to execute the user's original task in the current session
3. For batch/volume tasks, write batch execution scripts according to the Skill's guidance

If no execution intent was identified, end here.

---

## Tool Constraints

Phase 2, Phase 3, and Delivery testing must follow these rules.

### File Management

All intermediate artifacts (HAR/NDJSON exports, temp records, debug output) go in the `tmp/` directory. Create it first if it doesn't exist.

### pinchtab Command Rules

- **Session first**: create a session before the first `nav`; anonymous commands share one tab that anything else can steal. All subsequent commands use the session's dedicated tab.
- **Wait before reading**: after navigation use `pinchtab wait --load network-idle` before reading traffic; before interacting with async-injected DOM use `pinchtab wait <selector>` (default waits for visible).
- **Network buffer is rolling and tab-scoped**: entries evict per `bufferSize`. For interaction windowing prefer a baseline diff (`pinchtab network --limit N` before, compare after); `pinchtab network clear` immediately before an interaction is acceptable once earlier traffic has already been mined. For long crawls stream to file instead: `curl -N "http://localhost:9867/network/export/stream?format=ndjson&path=tmp/live.ndjson"`.
- **Response bodies are opt-in**: list requests freely; fetch details with `pinchtab network <id> --body` only when the exploration needs them. Exports redact sensitive headers (`Cookie`, `Authorization`, `X-API-Key`, `X-CSRF-Token`) by default — keep redaction.
- **No JS-level network interception**: never override `XMLHttpRequest.prototype`, `window.fetch`, etc. Endpoint discovery uses `pinchtab network`. Sole exception: the form dry-run listener in `exploration_operation.md` (a temporary submit-event listener that never touches network APIs and is removed within the same eval).
- **Refs are per-document**: snapshot refs (`e5`, `e12`) stay stable within one page but die on navigation — never cache refs across navigations, never write refs into strategy code; resolve at execution time via `snap`.
- **eval discipline**: requires `security.allowEvaluate: true`. Any snippet declaring identifiers must be an IIFE (`(() => { ... })()`). A 403 `evaluate_disabled` is a config problem — fix config + `pinchtab server restart`, don't route around it. Async snippets need `--await-promise`.
- **Token efficiency**: default to `--snap-diff` on actions, `text` for prose reads, `snap -i -c` for interactive elements, `find "<phrase>"` when you can describe the target. Screenshots only for visual debugging.

### DOM Operation Constraints

Applies to all DOM scenarios (data extraction, enum collection, pagination controls, form submission):

**Selector priority**: `data-testid > id > name > aria-label > structural path`. Avoid pure positional indexes unless structure is genuinely stable.

**Batch-validate selectors**: test all candidate selectors in one eval returning a JSON summary (hit count per selector, key attributes of first element, uniqueness). Never eval selectors one by one.

**Shadow DOM**: access via `element.shadowRoot.querySelector`; split selector into host part + shadow-internal part.

**Three-layer selector validation**: element assertion → result check (non-empty, reasonable count) → success criteria. Must be tested on the real page, never written speculatively.

**Control scan** (enum collection): one eval returns a complete mapping of all target controls (tag+type / name+id / placeholder / label found by traversing up to the nearest form-item container). Don't hardcode component-library class names.

### Code Constraints

**Must operate directly on the target site**: never obtain data through external services (third-party scraping platforms, aggregation APIs, proxy resellers), and never call the site's official open-platform API — generated Skills target zero-config deployment. Access the site through the browser using its frontend's internal endpoints or DOM data.

**Framework internal state fast-fail**: attempting page data via framework internals (`__vue_app__`, `$data`, React fiber, Angular `ng`) → give up after one failure, switch to snap + value-fill-trigger approach.

### JS Execution Environment Constraints

Code executed via `pinchtab eval` is **browser-side JS**: only browser-native APIs and page-loaded third-party libraries may be used, no require/import of external modules.

### Conclusion Criteria

Account permission limits ≠ technical solution failure. When API is technically viable but data is limited by account permissions (pagination truncated, filters ineffective), conclusion is "pass" with permission dependency noted under Known Limitations.

**Partial success counts as success**: core capability verified counts as pass — even with some enums marked `[collection failed]`, non-core fields missing. After generating the Skill, **must inform the user which parts are not fully covered** — never silently omit.

### Efficiency Rules

Core criterion: **every browser roundtrip must yield information gain.**

| Rule | Description |
|------|-------------|
| **Composite eval** | Merge independent queries into one IIFE eval returning a JSON summary |
| **Runtime first** | Retrieval priority: JS runtime state → network data → DOM. Never reverse-engineer runtime data from DOM |
| **Output volume control** | Extract key fields (count, total, sample) from large responses inside the browser before returning |
| **Async wait cohesion** | Promise + setTimeout polling with timeout cap inside one eval; don't poll across commands |
| **Fast permission-restricted detection** | Restricted signals (upgrade prompts, identical data, disabled controls) → batch-mark similar items restricted, don't verify one by one |
| **Fetch once, analyze many** | Fetch a source once, save to `tmp/`, analyze repeatedly |
| **Stop at verification** | Endpoint confirmed working → move to next phase; no redundant exploration |
| **Slider/range batch** | Set all controls (including noUiSliders) to different values in one eval → trigger one search → map all numericFilters from the request |

---

## Stealth & Environment Coherence

Anti-bot capability comes from the configured browser provider, checked in Phase 0 via `/stealth/status`.

- **CloakBrowser provider** (`provider=cloak, native=true`): kernel-level C++ fingerprint patches. Keep one fixed `browser.cloak.fingerprintSeed` per profile when revisiting the same site; keep `browser.cloak.disableDefaultStealthArgs=true` (don't stack PinchTab JS overlays over native patches); keep timezone/locale/platform coherent with proxy geo (a US residential IP with `timezone=Europe/London` looks like a bot to any cross-checker).
- **Stock Chrome**: PinchTab applies its own stealth overlays (`stealth` level light/medium/full). Fine for ordinary sites; expect more challenges on protected ones.
- **Batch throughput**: parallelize across profiles/instances (`pinchtab instance start --profile p2`), not tabs within one profile — each profile carries its own cookies and fingerprint, so per-session rate limits apply independently. Still add intervals per Known Limitations.
- **When blocked or challenged**: stop retrying — hammering degrades the fingerprint's reputation. Switch approach (headed profile for login, different endpoint, DOM path) or pause for the human: `curl -X POST http://localhost:9867/tabs/{tabId}/handoff -H 'Content-Type: application/json' -d '{"reason":"human_verification","timeoutMs":120000}'`, let the user resolve the challenge in the headed window, then resume. Never attempt to defeat CAPTCHA or anti-bot systems.
- **Record honestly**: if exploration got blocked/challenged on the current provider, the generated Skill's Prerequisites must state the stealth requirement (see Filling Specification 21).
