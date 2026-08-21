# Generated Skill File Template

This file is read during Phase 3 execution. Create the output Skill directory according to this specification.

---

## Directory Structure

```
output/{skill-name}/{site-slug}-{capability-slug}/
├── SKILL.md
└── scripts/
    └── {capability-name}.py
```

**Naming Rules**:
- `site-slug`: Target site's primary domain, lowercase, without `www.` and TLD (e.g., `github`, `notion`, `jira`)
- `capability-slug`: Short English description of the capability, kebab-case (e.g., `list-issues`, `create-task`, `search-users`)
- `scripts/*.py` filenames also kebab-case (e.g., `search-products.py`)
- Only lowercase letters, digits, and hyphens allowed; no underscores

JS code is encapsulated in Python files under `scripts/`; SKILL.md invokes them via pinchtab. Non-JS content (Network Capture steps, AI Workflow, text descriptions) remains inline in SKILL.md.

---

## SKILL.md Template

````markdown
---
name: {site-slug}-{capability-slug}
description: "{Function statement — site name + capability + input/output overview}. Use when user mentions {site name variants}, {data type keywords}, or says {trigger phrases covering casual/formal/abbreviated expressions — as many as needed for full coverage}. Also applies to {adjacent scenarios that aren't obvious but should trigger}."
---

# {site-name} — {capability-name}

> {one-line description: input → output}

## Language

All process output to user (progress updates, process notifications) follows the user's language.

## Objective

{what this capability aims to achieve, one sentence}

## Prerequisites

- Target page is already open in the browser: `{full URL of the target page}`
- {e.g., already logged in, user avatar or username visible on the page} (when login is required)
- {Only when recorded during forging: stealth browser runtime required (CloakBrowser) — stock Chromium was blocked/challenged during exploration}

<!-- Assembly guidance: Prerequisites only describe website state (page opened, logged in), runtime needs actually encountered during forging (stealth browser), and dependencies (e.g., browser extensions) — not connection methods or server management; those are decided by the caller. -->

## Pre-execution Checks

<!-- Assembly guidance: Pre-execution checks include only the following fixed items; do not add custom checks beyond them. -->

### 1. Tool Readiness

If pinchtab has been confirmed available in the current session → skip this step.

1. `pinchtab --version` → missing → install via `npm install -g pinchtab`
2. Eval capability: `pinchtab config show` → Security `Evaluate:` must be `true`; if false set `"security": {"allowEvaluate": true}` in `~/.pinchtab/config.json`, then `pinchtab server restart`
3. Session: bash `export PINCHTAB_SESSION=$(pinchtab session create --agent-id {capability-name})` / PowerShell `$env:PINCHTAB_SESSION = "$(pinchtab session create --agent-id {capability-name})"`

The first `pinchtab nav <url>` auto-starts the local server if it isn't running.

### 2. Login Verification (when prerequisites include login requirement)

If login status for the target site has been confirmed in the current session → skip this step.

Otherwise: open the target site and observe login status:
- Logout/sign-out entry, user avatar, or username exists (`pinchtab snap -i -c` / `pinchtab text`) → logged in, continue
- Login/register entry with no logout entry → not logged in, inform the user that login is needed first, assist the human through the login flow (headed window or handoff); never enter credentials yourself

User refuses or cannot log in → terminate execution.

## Capability Components

> This Skill's operational boundary = what the user can manually do in their browser. It only reads data already displayed to the user on the page, never bypasses authentication or access controls. Its role is equivalent to copy-pasting on the user's behalf — automation merely saves time. JS code is encapsulated in Python files under `scripts/`, invoked via `pinchtab eval "$(python scripts/xxx.py {params})"`. `$(...)` works in both bash and PowerShell; the bash tool is recommended for execution. Async snippets need `pinchtab eval --await-promise`.

Below are all atomic capabilities discovered and verified during the exploration phase, listed by command template with parameters. Simply invoke them as needed — no need to read `scripts/*.py` source code or re-verify. Only inspect scripts when execution fails for troubleshooting. Combine freely as needed during execution.

### API: {capability description, e.g., "get product list"}

`pinchtab eval "$(python scripts/{capability-name}.py '{param1}' --param2 {param2})"`

Parameters:
- {param1}: {description}
- --param2: {description}, default {default-value}

Output example:
```json
{
  "{field-name}": "{example-value}",  // {description}
  "{field-name}": 0,                  // {description}
  "{field-name}": null                // {description}, null when no data
}
```

### API: {capability description, e.g., "submit order"}

`pinchtab eval "$(python scripts/{capability-name}.py '{param1}' --field1 '{value1}' --field2 '{value2}')"`

Parameters:
- {param1}: {description}
- --field1: {description}
- --field2: {description}

Output example: {same annotated JSON shape as above}

### Network Capture: {capability description, e.g., "get search results"} (parameters injected via URL navigation)

Parameters are injected via URL; API responses are read from captured traffic (requests contain dynamic signatures, cannot be fetched directly):

1. `pinchtab nav {URL pattern, e.g., https://example.com/search?q={keyword}&page={page}}`
2. `pinchtab wait --load network-idle`
3. `pinchtab network --filter {endpoint keyword}`
4. `pinchtab network {requestId} --body`

Endpoint characteristic: URL contains `{characteristic path, e.g., /api/search}`

Error handling: when no matching request is found, check page status (blocked by anti-bot? login needed? correct page?), rule issues out, then retry once. The buffer is rolling — read soon after navigation.

Output example: {same annotated JSON shape as above}

### Network Capture: {capability description, e.g., "get filtered results"} (parameters injected via UI operations)

Parameters are injected via UI operations; API responses are read from captured traffic:

1. {UI operation steps using refs, e.g., `pinchtab fill {ref} {keyword}`, `pinchtab select {ref} {option}`}
2. Trigger request ({e.g., `pinchtab click` on the search button})
3. `pinchtab wait --load network-idle`
4. `pinchtab network --filter {endpoint keyword}`
5. `pinchtab network {requestId} --body`

Endpoint characteristic: URL contains `{characteristic path}`

Error handling: same as above.

Output example: {same annotated JSON shape as above}

### DOM: {data area description, e.g., "product list"} (data extraction type)

<!-- Assembly guidance: If target data is asynchronously injected (lazy loading, extensions), prepend `pinchtab wait "{target-selector}"` before extraction to wait for elements. -->

Extract: `pinchtab eval "$(python scripts/{extraction-capability-name}.py)"`

Output example: {same annotated JSON shape as above}

Pagination: `pinchtab eval "$(python scripts/{pagination-capability-name}.py)"`

[AI Intervention] {step requiring visual judgment, e.g., "confirm new data loaded"}:
`snap -i -c` confirm page change → re-run extraction script

### DOM: {control description, e.g., "submit form"} (operation type)

<!-- Assembly guidance: If form controls are asynchronously rendered, prepend `pinchtab wait "{control-selector}"` before filling. -->

Fill and submit: `pinchtab eval "$(python scripts/{operation-capability-name}.py '{param1}' --field '{value}')"`

Parameters:
- {param1}: {description}
- --field: {description}

[AI Intervention] {step requiring dynamic judgment, e.g., selecting a dynamic dropdown item}:
{judgment basis: what signal on the page determines the operation}
→ `snap -i -c` locate by visual description → `click {ref}`

### AI Workflow: {capability description, e.g., "browse products and extract prices"} (pure visual, used when static scripts cannot cover)

Each step uses pinchtab subcommands (abstract form; Agent adds session/environment at runtime); element references use only visual descriptions resolved via snapshots — **no CSS selectors**; record state checkpoints after key steps:

1. `nav {url}` → page loaded, `title` is "{expected-title}"
2. `snap -i -c` locate {visual description, e.g., "product card area with price labels mid-page"} → `text {ref}`, extract `{field-name}`
3. `scroll down` → wait for more products (checkpoint: new items appear)
4. `text` extract `{field-list}` from returned content

Output example: {same annotated JSON shape as above}

### Composite: {full capability description, e.g., "get complete product data (API + DOM supplement)"}

<!-- Assembly guidance: Used when a single atomic component cannot provide complete data; may combine across pages (list capture + detail extraction + merge). Entirely same-page JS combinations merge into one Python script; when navigation or non-JS steps are involved, list steps sequentially. Atomic components remain for individual invocation. -->

{When all-JS combination}:

`pinchtab eval "$(python scripts/{composite-capability-name}.py '{param1}' --param2 {param2})"`

Parameters:
- {param1}: {description}
- --param2: {description}

Output example: {same annotated JSON shape as above}

{When cross-page / contains non-JS steps combination}:

1. `pinchtab nav {page-A URL}` → `pinchtab wait --load network-idle` → `pinchtab eval "$(python scripts/{capability-A}.py '{param}')"`
2. `pinchtab network --filter {keyword}` → `pinchtab network {requestId} --body`
3. For each `{item}` from step 1/2:
   a. `pinchtab nav {page-B URL pattern}` → `pinchtab eval "$(python scripts/{capability-B}.py '{item}')"`
4. Merge: associate by `{association-field}`

Output example: {same annotated JSON shape as above}

## Enum Parameters

<!-- Assembly guidance: Group by parameter; priority: API > DOM > AI. What code can obtain must not be left to AI. One endpoint covering multiple parameters merges into one block. -->

[API] {param-name} — `pinchtab eval "$(python scripts/enum_{param-name}.py)"`

[DOM] {param-name} — `pinchtab eval "$(python scripts/enum_{param-name}.py)"`

[AI] {param-name}: {description of what requires Agent interaction to obtain, no JS, not encapsulated}

Cascade dependency: {param A} → {param B} (obtain A first, then B)

{param-name} [collection failed]: {failure reason}

## Pagination

<!-- Assembly guidance: Required for list-type data; delete for non-list types. Keep only types verified during exploration; delete the rest. -->

**API Pagination**: `{pagination-param-name}`, type: `{page-number / cursor}`, start value: `{start-value}`. Next page value source: `{increment / response field path}`. Termination: `{termination-condition}`.

**URL Pagination**: URL pattern `{URL pattern}`, next-page link selector: `{selector}`. Termination: `{termination-condition}`.

**DOM Pagination**: Click "{control description}" (`{selector}` or snapshot ref), wait then re-extract (`pinchtab wait {item-selector}`). Termination: `{termination-condition}`.

**AI Pagination**: Agent-driven visual pagination. Each page: `snap -i -c` judge state → paginate → wait → re-extract. Termination signal: `{termination-signal}`.

## Success Criteria

`{quantifiable condition expression; purely descriptive criteria prohibited}`

Quantifiable dimension references:
- Data count: `result count >= 1`
- Field completeness: `core field non-null rate = 100%`
- Data consistency: `matches the first N items displayed on the page`
- Operation result: `response status 200 with no error field`

## Known Limitations

- {e.g., rate limited to 60 requests per minute}
- {e.g., can only query data under own account}
- {Only when forging was blocked on stock Chromium: requires stealth browser runtime (CloakBrowser)}

## Execution Efficiency

- **Batch orchestration**: write a bash script looping through the command templates serially within a single session; do not parallelize tabs within one profile (triggers rate limits). Add intervals per "Known Limitations". For throughput, start additional profiles/instances (`pinchtab instance start --profile p2`) — each carries independent cookies and fingerprint, so per-session limits apply separately
- **Test before batch execution**: after writing a batch script, test with 1–2 items first; only then run the full batch. Never skip testing
- **Reduce redundant pre-operations**: when multiple steps share prerequisite state, complete them in batch under that state
- **Error resumption**: save results item by item; on failure resume from the breakpoint rather than starting over

## Experience Notes

<!-- Assembly guidance: Required universal section; output in English, only replace {skill-name} and {site}-{capability} in the path -->

Path: `{working-directory}/pinchtab-skill-forge-memories/{skill-name}-{site-slug}-{capability-slug}.memory.md` (working directory is determined by the Agent running the Skill, typically the project root or current working directory)

**Before execution**: if the file exists, read it first — it records unexpected situations from past executions (e.g., a strategy became ineffective); adjust strategy order accordingly.

**After execution**: if an unexpected situation occurred (strategy ineffective, page redesigned, anti-bot upgraded, better path discovered), append one line:
`{YYYY-MM-DD}: {what happened} → {conclusion}`

Normal execution does not write to the file. Do not record what keywords were used or how many results were returned — those are task outputs, not experience.
````

<!-- Assembly guidance: The Experience Notes section is a universal template; replace path variables without modifying semantics. Strategy implementation details belong inline in their corresponding strategy sections, not in experience notes. -->

---

## Python Wrapper File Template

Each `scripts/*.py` file follows this structure:

```python
import argparse
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser()
    parser.add_argument('{positional-param}')                          # {description}
    parser.add_argument('--{named-param}', default='{default-value}')  # {description}
    args = parser.parse_args()

    js = f"""
    (() => {{
      try {{
        // Original JS verified during exploration phase
        // Business parameters injected via f-string: {args.positional_param}, {args.named_param}
        return JSON.stringify({{ /* normal result */ }});
      }} catch(e) {{
        return JSON.stringify({{ error: true, message: e.message }});
      }}
    }})()
    """
    print(js)

if __name__ == '__main__':
    main()
```

<!-- Assembly guidance: Python files only handle parameterized assembly of JS strings. Verified JS goes into the f-string as-is; only business parameters (keywords, page numbers, sort order) are replaced with argparse parameters. Selectors, field mappings, endpoint URLs are hardcoded directly in the JS. The printed string is consumed by `pinchtab eval`. Async snippets (fetch/promise) stay inside the IIFE returning a promise — the caller adds `--await-promise`. -->

---

## Filling Specifications

1. **No placeholders left behind**: all `{...}` replaced with real values; blanks not allowed
2. **Code must be runnable**: JS strings in `scripts/*.py` must execute directly in the browser console; Python execution stdout must be valid JS wrapped in an IIFE
3. **Use placeholders for runtime variables**: keywords, business parameters, pagination offsets use `{param-name}`, not hardcoded values. Typical usage demos go in a separate "Usage Example" block outside strategy code
4. **Description entirely in English** (every word — function statement, trigger phrases, scenarios). Three parts: function statement (site + capability + I/O), trigger scenarios (keyword-rich English phrases covering site name variants and data keywords; casual, formal, abbreviated), scope expansion (adjacent non-obvious triggers). Site name first for matching priority; under 1024 characters; no markdown formatting; third person; err toward being "pushy" (agents tend to under-trigger)
5. **Limitations must be real**: only document limitations actually encountered during exploration; no speculation
6. **Add/remove components as needed**: each API / Network Capture / DOM entry added or removed based on actual exploration results
7. **Enum priority order**: `[API]` before `[DOM]` for the same parameter; single method → list only that one
8. **Mark collection failures**: `{param-name} [collection failed]: {reason}`; never blank
9. **Delete sections as needed**: delete "Enum Parameters" when no enums; delete "Pagination" when not list-type
10. **Enums don't duplicate capability components**: reference existing components instead ("retrieval method: see API component above: {component-name}")
11. **No task-specific instance data or origin references**: Skills are reusable templates — no search keywords, URL lists, usernames from this exploration; no references to materials provided by the user. When reproducing capabilities of an existing scraper/SaaS platform (Apify, Octoparse, Bright Data, ScrapingBee, Phantombuster, Diffbot…), the generated Skill must NOT mention the source platform anywhere
12. **Strip assembly guidance**: all HTML comments (`<!-- ... -->`) are generation guidance; they must not appear in generated output
13. **One JS snippet per .py file**: each independent snippet is one `scripts/*.py` file, filename kebab-case describing function
14. **Python only does assembly**: `.py` files make no network requests, touch no filesystem, call no pinchtab; they only output JS strings via `print()`
15. **Parameter names align with business semantics**: argparse names use business terms (keyword, page, sort), not technical terms (selector, xpath)
16. **Output format must be defined**: every data-returning component provides annotated JSON examples for consistent output across executions
17. **Component titles reflect implementation method accurately**: API = fetch call; Network Capture = read from captured traffic; DOM = DOM APIs; AI Workflow = visual operations; Composite = multi-component orchestration. Labels match reality
18. **JSON output compact and efficient**: key-value pairs over name/value arrays (use `{"Brand": "xxx", "Weight": "30 lbs"}`, not `[{"name": "Brand", "value": "xxx"}]`)
19. **JS must include error handling**: all JS wrapped in try/catch with structural validation (selector hits empty, source unreachable, results empty, structure mismatch). On error uniformly return `{"error": true, "message": "..."}`. Individual null field values are normal data, not errors
20. **Network Capture must guide error handling**: explain what to do when the target request isn't found (wait/retry once, check page status) and how to judge anomalous responses
21. **Stealth requirements recorded honestly**: add the "stealth browser runtime required" prerequisite line only when exploration was actually blocked/challenged on stock Chromium; ordinary sites carry no such line
