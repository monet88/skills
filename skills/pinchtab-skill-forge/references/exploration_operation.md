# Operation-Type Capability Exploration

This file is read during Phase 2 execution (operation-type capabilities only).

**Goal**: Capture how the target operation is executed, confirm it can be triggered in a controlled manner, and record the complete submission parameters. Prefer API direct connection; use DOM automation for submission when necessary.

All browser interaction runs through the `pinchtab` CLI in the session created in Phase 0. JS snippets run via `pinchtab eval` as IIFEs returning `JSON.stringify(...)`.

**Pass Criteria** (API direct connection path):
- Captured request (dry-run payload or live network capture) is the expected non-GET request
- All required fields in the request body have clear sources and can be parameterized
- No dynamic credential blocking
- Enumeration parameter retrieval methods have been determined (partial `[collection failed]` still counts as passing)

**Pass Criteria** (DOM fallback path):
- All required form fields can be filled (via script or AI intervention)
- Submission can be triggered
- Live capture confirms the expected submission request was sent with expected structure
- Enumeration parameter retrieval methods have been determined (partial `[collection failed]` still counts as passing)

---

## Exploration Decision Tree

```
Navigate → Initial traffic observation → Safety verification → API feasible?
  ├── Yes → Record API information
  └── No → [DOM fallback submission]

Verification failure fallback: [API direct] → [DOM fallback submission] → [AI Workflow] → Report obstacles

All paths ultimately → [Enumeration collection]
```

---

## Navigation and Initial Observation

```
pinchtab nav {target URL} --snap --block-images
pinchtab wait --load network-idle --idleFor 800
pinchtab network --filter {domain keyword}
```

Record two types of information:
- **Enumeration prefetch requests**: requests returning dropdown options, category lists (for later enum collection)
- **Form initialization requests**: configuration/state requests made during page load, which may contain CSRF tokens, form field configurations

---

## Safety Verification Protocol

> **Dry-run vs live capture distinction**: The dry-run captures **request intent without sending anything** (zero side effects; works for classic `<form>` submissions only). Live capture observes an **actually-sent request** and requires one explicit user confirmation for consequential operations. They serve different risk levels — always attempt dry-run first.

Operation-type verification must capture request details while minimizing real side effects. PinchTab has no offline mode, so zero-side-effect capture is best-effort:

### Execution Flow

1. **Fill the entire form via one eval** (supplement with `pinchtab screenshot` if control purpose is unclear): eval using the setter pattern (`HTMLInputElement.prototype` value setter + input event) to batch-fill all inputs with unique values → select a non-default item for select/dropdowns → do NOT click submit yet. Do not fill field by field.
2. **Dry-run attempt** (classic forms): one eval attaches a temporary capture-phase submit listener that calls `preventDefault()`, serializes the form to JSON, removes itself, and returns the payload — then clicks submit inside the same eval:
   ```bash
   pinchtab eval "(() => {
     const form = document.querySelector('{form selector}');
     let payload = null;
     const handler = (e) => {
       e.preventDefault();
       payload = Object.fromEntries(new FormData(form).entries());
     };
     form.addEventListener('submit', handler, { capture: true, once: true });
     try {
       (form.requestSubmit ? form.requestSubmit() : form.submit.call(form));
       // note: form.submit() bypasses submit events; prefer requestSubmit or clicking the real submit button
     } finally {
       form.removeEventListener('submit', handler, { capture: true });
     }
     return JSON.stringify({ dryRun: !!payload, payload });
   })()"
   ```
   If clicking the programmatic path doesn't fire handlers, click the real submit button instead: `pinchtab click {submit ref}` after attaching the listener in a separate eval, then read the payload from a follow-up eval.
3. **Wait 1–2s** for async event handlers.
4. **Read the captured intent**: dry-run payload gives endpoint-agnostic body structure. For endpoint URL + method, check whether a request actually fired (`pinchtab network --filter {domain keyword}` — a blocked/prevented submit sends nothing).
5. **Live capture fallback** (SPA handlers that bypass form submit events, or when dry-run yields nothing): **STOP and ask the user once** — "Submit this form for real? ({what the operation does})". On explicit approval: window the traffic (`pinchtab network clear`), click submit, wait 1–2s, then extract non-GET requests:
   ```
   pinchtab network --filter {domain keyword}
   pinchtab network {requestId} --body
   ```
6. **Leave immediately after live capture**: navigate to another page to prevent retry logic from re-sending requests.

GET-form searches are side-effect-free reads — skip step 5's confirmation and submit directly.

### Information Extracted

For each non-GET request/payload, record:
- Endpoint URL + HTTP method (POST/PUT/PATCH/DELETE)
- Request body structure (field names, types, required/optional)
- **Input conditions at capture time**: what values were filled that triggered this request (different inputs may produce different structures; recording them helps verify generality)

### GraphQL Mutation Identification

Request body contains a `query` field starting with `mutation` → GraphQL write operation. Extract mutation name and variables structure.

---

## Operation Feasibility Assessment

Based on captured request details, select the strategy path:

**API direct connection feasible** (all of the following):
- All required fields have clear sources and can be parameterized
- Serialization is transparent (request body reproducible directly from parameters, no opaque encoding)
- No dynamic credentials found

→ Use API submission strategy; record endpoint URL + request structure.

> **Fallback**: scripted verification discovers dynamic credentials or opaque encoding missed during analysis → fall back to [DOM fallback submission].

**API incompatible** (any of the following):
- Frontend dynamically generated Tokens, Nonces, or HMAC signatures
- Request body contains opaque encoding (not reproducible from form fields)

→ Fall back to DOM operation submission below.

---

## DOM Fallback Submission

Let the page's native JS handle credential generation; automate only form filling and submission triggering.

### Step 1 — Control Locating

**When captured-body field names are available (preferred)**: locate controls by field name (`name`/`id` usually match), single batch eval, skipping full scan:

```bash
pinchtab eval "(() => {
  const fields = ['{field_name_1}', '{field_name_2}'];
  return JSON.stringify(fields.map(f => {
    const el = document.querySelector('[name=\"' + f + '\"], [id=\"' + f + '\"]');
    return el ? { field: f, tag: el.tagName, type: el.type, found: true } : { field: f, found: false };
  }));
})()"
```

**When no field information (fallback)**: full scan of the form returning a complete control mapping (traverse up to nearest container for label text; don't hardcode component-library class names):

```bash
pinchtab eval "(() => JSON.stringify(
  Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
    tag: el.tagName, type: el.type, name: el.name, id: el.id, placeholder: el.placeholder
  }))
))()"
```

### Step 2 — Assess Scriptability

Evaluate each field individually:
- Value fixed or parameterizable → **[Script]**: fill via eval
- Requires real-time judgment (dynamic dropdowns, captchas, complex interactions) → **[AI intervention]**: Agent performs visual operations

All fields AI-intervened → produce AI Workflow strategy (Step 3b).

**Multi-step forms (wizards / stepped flows)**: page state changes per step; re-scan visible controls at each step, recording state dependencies between steps so the complete sequence is reproducible in the generated Skill.

### Step 3a — Scripted Submission Verification (when [Script] steps exist)

Use the Safety Verification Protocol above: dry-run first; if dry-run cannot intercept (SPA handler), obtain the one-time user confirmation and verify live. Batch-fill snippet:

```javascript
// [Script] Batch fill all fields (setter pattern triggers framework reactive updates)
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
[
  ['{selector_1}', '{param_value_1}'],  // Element assertion: el.name === '{field_name_1}'
  ['{selector_2}', '{param_value_2}'],  // Element assertion: el.name === '{field_name_2}'
].forEach(([sel, val]) => {
  const el = document.querySelector(sel);
  setter.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
});
```

Then trigger submission and confirm from the captured request that it fired with expected structure.

> **Fallback**: expected request not captured (framework ignoring setter, selector invalid, submission not triggered) → upgrade failed fields to [AI intervention], re-execute Step 3a (remaining script fields) + 3b (upgraded AI fields) mixed. All fields fail → entirely Step 3b.

### Step 3b — AI Workflow (when all fields require AI intervention)

The Agent walks through the operation flow step by step like a user.

**Writing standards**:
1. Each step uses pinchtab subcommands in abstract form (no session/server setup — Agent adds environment at runtime), followed by supplementary context, ending with `→ expected result`
2. Element references use only visual descriptions resolved via snapshots; CSS selectors are **prohibited**
   - ✗ `eval "document.querySelector('button[type=submit]').click()"`
   - ✓ `snap -i -c` locate the blue "Submit" button at the bottom of the form → `click {ref}`
3. Record state checkpoints after key steps (`pinchtab url`, `pinchtab title`, visible characteristics)
4. Submission steps must include the complete safety sequence:
   fill-all eval → dry-run attempt → if interception impossible, explicit user confirmation → `pinchtab network clear` → click submit → wait 1–2s → `pinchtab network --filter ...` + `<id> --body` → immediately navigate away
5. Human-verification walls mid-flow: handoff/resume (see SKILL.md Stealth section); never defeat challenges.

Example:
```
1. snap -i -c locate {visually described input field} → fill {ref} "{param_value}"
2. screenshot → confirm input filled (checkpoint)
3. snap -i -c locate the "Submit" button at the bottom of the form
4. attach dry-run listener (eval) → click {ref}
   → payload captured? record it : ask user once → network clear → click {ref} → wait 2s
   → network --filter {domain keyword} → network {id} --body → nav away immediately
```

> **Failure**: both scripted and AI Workflow fail to trigger the submission correctly → report obstacles and attempted paths to the user, ask next steps.

---

## Parameter Enumeration Collection (Required)

During verification you **must proactively explore** every enumeration-type control on the page (dropdowns, selectors, radio groups) to determine the **data source and retrieval method** for their options. Do not record specific values — values change; retrieval methods are durable.

Priority order `API > DOM > AI`:

1. **Read current page traffic independently**: `pinchtab network --filter {domain keyword}` for requests returning enumeration lists. If buffer moved on (navigated away), navigate back first
2. **Expand/interact with the control**, observe async requests → record as above. Search-enabled controls: enter a keyword to trigger the search API
3. **API endpoint exists** → record endpoint URL + method + response structure; verify independent invocation feasibility
4. **Independent invocation infeasible** → record hybrid approach: prerequisites from page + how obtained + then how to call the API
5. **No API endpoint** → eval reads option values from DOM (native `<select>` reads `.options`; component-library controls try instance properties, else expand and read rendered results); record selectors and method
6. **DOM unreliable too** → **[AI]** approach: describe visual interaction operations

#### Conditional Enumeration (Cascading Linkage)

When cascading exists between enumeration controls (selecting A makes B's options appear/change), record the dependency chain (A→B→C) and each level's retrieval method.

#### Writing to Generated Skill

In the generated SKILL.md's "Enum Parameters" section, layer each enumeration by `[API]` > `[DOM]` > `[AI]`. `[API]` and `[DOM]` must provide executable code; `[AI]` describes interaction operations. Cover: retrieval method per enumeration + cascade dependency order. Operation steps retain inline comments `// {param_name} enumeration retrieval: ...`.

Enumerations that cannot be collected are marked `[collection failed]` and continue without blocking exploration.
