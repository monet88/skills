# Operation Capability Exploration

This reference is used during Phase 2 for website operations that create, update, delete, submit, publish, purchase, or otherwise produce side effects.

**Goal**: Capture how the target operation is executed, confirm it can be triggered in a controlled manner, and record the complete submission parameters. Prefer API direct connection; use DOM automation for submission when necessary.

**Pass Criteria** (`DIRECT_API_VERIFIED` path):
- Offline HAR captures the expected non-GET request with complete URL, method, headers, and body structure.
- All required fields in the request body have clear sources and can be parameterized.
- No dynamic browser-bound credentials (nonces, dynamic HMAC signatures, page-locked tokens) block standalone replay.
- Direct replay verification passes without launching a browser.
- Parameter enumeration retrieval methods have been determined (partial `[collection failed]` still passes).

**Pass Criteria** (`BROWSER_SESSION_API` path):
- Request structure is known from HAR or session network capture.
- Invocation requires live browser session state, cookies, or browser-bound session tokens.
- Invocation works reliably via browser-side fetch or evaluated script within the named session.
- Parameter enumeration retrieval methods have been determined.

**Pass Criteria** (`DOM_ONLY` / `HYBRID` fallback path):
- All required form fields can be filled (via script setter pattern or dynamic UI interaction).
- Dialogs (alerts, confirmations, prompts) are handled deterministically via runtime dialog commands.
- Submission triggers the expected request captured in offline HAR or verified in-page outcome.
- Parameter enumeration retrieval methods have been determined.

---

## Runtime Boundary

Run every browser command through the current forge run's trusted runtime wrapper:

```text
python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- <agent-browser-command>
```

Never invoke raw `agent-browser` for forge-controlled exploration. The wrapper owns the trusted config, strips ambient overrides, and enforces the isolated named session.
### Non-Interactive Execution Contract

Forge execution is strictly non-interactive. Interactive commands (`chat`) and confirmation flags (`--confirm-interactive`, `--confirm-actions`) are rejected by `forge-runtime exec`. Human decisions, questions, or confirmations route through the coordinator/host layer, never agent-browser stdin.

### Refinement by Default vs Explicit Fresh Mode

When generating or updating operation capabilities with `generate-skill`:
- Existing packages in `.agent-forge/output/<skill-name>/` are refined by default, merging updated endpoints by stable identity (`id` or `path`+`method`) and preserving unaffected endpoints and helper scripts.
- Corrupted packages trigger `FRESH_REQUIRED` error.
- Pass `--fresh` for an explicit clean rebuild.


### Ephemeral Ref Discipline

Snapshot refs (such as runtime ref handles) are ephemeral runtime handles valid only for the immediate page state. Never persist a concrete snapshot ref into generated Skill strategy files, scripts, manifests, provenance, or examples. Dynamic flows must re-snapshot and resolve targets at execution time.

---

## Exploration Decision Tree

```text
Navigate → Initial traffic observation → Zero-side-effect HAR safety verification → Feasibility Assessment
  ├── Direct API verified (clean replay, no browser-bound auth) → DIRECT_API_VERIFIED
  ├── Browser session required (cookies/tokens bound to session) → BROWSER_SESSION_API
  ├── DOM automation required (complex UI/JS validation/custom controls) → DOM_ONLY
  └── Multi-stage / mixed (UI auth + API write or API enum + DOM submit) → HYBRID

Verification failure fallback: [DIRECT_API] → [BROWSER_SESSION_API] → [DOM_ONLY] → [AI Workflow] → Report obstacles

All paths ultimately → [Parameter Enumeration Collection]
```

---

## Navigation and Initial Observation

Navigate to the target page, wait for loading to settle, and inspect initial network traffic:

```text
agent-browser open <target-url>
agent-browser wait --load networkidle
agent-browser network requests --type xhr,fetch --filter <keyword>
```

Record two types of information:
- **Enumeration prefetch requests**: Requests returning dropdown options, categories, tags, or search suggestions (for later enum collection).
- **Form initialization requests**: Configuration, metadata, or state requests containing CSRF tokens, form schemas, or session IDs.

---

## Safety Verification Protocol (Zero Side Effects via Offline Mode)

> **Offline HAR Recording vs. Network Traffic Monitoring**: Safety verification uses **offline mode plus HAR capture** to intercept request intent with zero side effects before any write reaches the server. Network traffic monitoring observes **already-sent requests** during read/extraction exploration. The two serve distinct risk levels and are not interchangeable.

Operation exploration must capture complete request details **without triggering live side effects** whenever possible.

### Execution Flow

1. **Start HAR recording**:
   ```text
   agent-browser network har start --content all
   ```
2. **Switch to offline mode**:
   ```text
   agent-browser set offline on
   ```
3. **Fill form controls**:
   Use batch filling via the JavaScript setter pattern to trigger reactive framework updates (React, Vue, Svelte, Angular):
   ```javascript
   const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
   [
     ['#field1', 'val1'],
     ['#field2', 'val2'],
   ].forEach(([sel, val]) => {
     const el = document.querySelector(sel);
     if (el) {
       setter.call(el, val);
       el.dispatchEvent(new Event('input', { bubbles: true }));
       el.dispatchEvent(new Event('change', { bubbles: true }));
     }
   });
   ```
   For dropdowns, select non-default options. For checkboxes/radios, toggle checked state. Alternatively use live agent-browser primitives (`fill`, `select`, `check`, `uncheck`, `click`) resolved from an immediate `snapshot -i`.
4. **Trigger submission**:
   Click the submit button or invoke `form.requestSubmit()`. Because offline mode is active, the browser constructs and attempts to send the request, recording it in the HAR buffer while network dispatch is prevented.
5. **Handle dialogs if triggered**:
   If the submit action triggers a confirmation dialog:
   ```text
   agent-browser dialog status
   agent-browser dialog accept
   ```
6. **Wait 1–2s for event dispatch**:
   ```text
   agent-browser wait 1000
   ```
7. **Stop HAR recording to run-local private directory**:
   ```text
   agent-browser network har stop .agent-forge/runs/<run-id>/<operation-name>.har
   ```
8. **Restore online mode and neutralize page**:
   ```text
   agent-browser set offline off
   agent-browser open about:blank
   ```
   Immediately navigating away prevents browser retry loops from transmitting pending requests once online.

---

## Information Extracted from HAR

Inspect the captured `.har` file (e.g. using `forge-runtime.py har-inspect`) to extract:
- **Endpoint URL and HTTP Method**: POST, PUT, PATCH, DELETE.
- **Headers**: `Content-Type`, `Authorization`, custom CSRF/signature headers.
- **Request Body Structure**: JSON schema, form-urlencoded keys, multipart fields, or raw payloads.
- **Input Conditions at Capture Time**: The exact test values filled during capture, establishing how form inputs map to request parameters.
- **Query Parameters**: Any URL query string parameters accompanying the write.

### GraphQL Mutation Identification

If the request body contains a `query` field starting with `mutation`, classify as a GraphQL write operation. Extract:
- Mutation operation name (e.g. `mutation CreateItem(...)`).
- Variable definitions and types.
- Query document structure and expected response selection set.

---

## Live-Submission Fallback Boundary

If offline HAR capture cannot prove the request structure (e.g., custom client-side validation prevents submit when offline, or server-side token handshake is strictly required):

1. **Do not silently perform a consequential live action**.
2. **Obtain one explicit user confirmation** before the single live submission required for verification.
3. State clearly:
   - Target URL and endpoint.
   - Operation intent and payload values.
   - Potential real-world side effects.
4. If approved: clear request history (`agent-browser network requests --clear`), perform the single submission, extract the captured request (`agent-browser network requests --type xhr,fetch` and `agent-browser network request <requestId>`), verify outcome, and immediately navigate away.

---

## Operation Feasibility Assessment & Classification

Classify the capability into exactly one category:

### 1. `DIRECT_API_VERIFIED`
- All required request fields have identifiable sources and can be parameterized.
- Serialization is transparent (JSON, standard form-urlencoded, or multipart).
- Auth/CSRF tokens can be obtained or refreshed programmatically outside a browser (e.g. API keys, bearer tokens, standard login session requests).
- **Direct replay verification**: Replay the request independently (e.g. via Python `urllib` / `requests`) with safe/test parameters to prove reproducibility. The steady-state runtime must run without launching `agent-browser`.

### 2. `BROWSER_SESSION_API`
- Endpoint is a clean HTTP/REST/GraphQL API, but requires browser-bound state (HTTP-only session cookies, browser fingerprinting, dynamic session tokens).
- Invocation executes via browser-side `fetch()` / XHR inside the named agent-browser session.

### 3. `DOM_ONLY`
- No clean API endpoint exists, request payload uses opaque/encrypted blobs, or dynamic frontend JavaScript logic is required to complete the operation.
- Automates UI controls using semantic locators and live agent-browser primitives (`snapshot -i`, `fill`, `select`, `check`, `click`, `press`).
- Handles dialogs with `agent-browser dialog accept|dismiss`.

### 4. `HYBRID`
- Combines browser interaction and API calls (e.g. UI authentication / session initialization followed by direct API writes, or API enum retrieval combined with DOM submission).

> **Replay Safety Rule**: Direct-operation replay is only considered verified when auth/CSRF/signatures reproduce reliably outside the browser. If auth cannot be decoupled from browser state, preserve a `BROWSER_SESSION_API` or `DOM_ONLY` implementation.

---

## DOM Fallback Submission Workflow

When DOM automation is required:

### Step 1 — Control Locating
- **HAR field-guided (preferred)**: Use field names discovered from HAR analysis to locate controls (`[name="..."]`, `[id="..."]`, aria labels).
- **Semantic scanning (fallback)**: Query form controls and locate accessible labels, placeholders, and roles:
  ```javascript
  Array.from(document.querySelectorAll('input, select, textarea, button')).map(el => ({
    tag: el.tagName, type: el.type, name: el.name, id: el.id, placeholder: el.placeholder, text: el.innerText
  }))
  ```

### Step 2 — Assess Scriptability
- Fixed or parameterizable inputs → **[Script]**: Fill via eval setter pattern or direct `agent-browser fill` commands.
- Interactive widgets (date pickers, drag-and-drop, rich editors) → **[UI Interaction]**: Use `agent-browser select`, `click`, `press`, `upload`.
- Multi-step wizards / stepped forms: Re-scan visible controls after each step and record state transitions.

### Step 3 — Scripted Submission & AI Workflow
- Batch-fill controls.
- Handle dialog confirmations: `agent-browser dialog accept`.
- Verify submission outcome from DOM success message, redirect URL, or response toast.

---

## Agent-Browser Live Runtime Contract for Operations

Generated Skills and exploration scripts must use the verified agent-browser CLI contract:

- **Dialogs**:
  - `agent-browser dialog status` (check if dialog is open)
  - `agent-browser dialog accept [text]` (accept alert/confirm/prompt)
  - `agent-browser dialog dismiss` (dismiss/cancel dialog)
- **Input & Selection**:
  - `agent-browser fill <sel> <text>` (clear and fill input/textarea)
  - `agent-browser type <sel> <text>` (type into element)
  - `agent-browser select <sel> <val...>` (select dropdown option)
  - `agent-browser check <sel>` / `agent-browser uncheck <sel>` (toggle checkbox)
  - `agent-browser click <sel>` / `agent-browser dblclick <sel>`
  - `agent-browser press <key>` (Enter, Tab, Escape, etc.)
  - `agent-browser upload <sel> <file...>` (file upload)
- **Tabs**:
  - `agent-browser tab list`
  - `agent-browser tab new [url]`
  - `agent-browser tab <tN|label|target>` (switch tab)
  - `agent-browser tab close [tN|label|target]`
- **Waits**:
  - `agent-browser wait <sel|ms>`
  - `agent-browser wait --load <networkidle|load|domcontentloaded>`
  - `agent-browser wait --url <pattern>`
  - `agent-browser wait --fn <expr>`
  - `agent-browser wait --text <text>`
  - `agent-browser wait --download <path>`
- **Offline Mode**:
  - `agent-browser set offline on`
  - `agent-browser set offline off`
- **HAR & Network**:
  - `agent-browser network har start [--content all]`
  - `agent-browser network har stop <path>`
  - `agent-browser network requests [--clear] [--filter <pattern>] [--type <types>] [--method <method>]`
  - `agent-browser network request <requestId>`
- **JavaScript Execution via Stdin**:
  - `python scripts/<feature>.py <args> | agent-browser eval --stdin` (POSIX) or `python scripts/<feature>.py <args> > temp_eval.js && cmd.exe /c "agent-browser eval --stdin < temp_eval.js"` (Windows)

---

## Parameter Enumeration Collection

Every enumeration-type control (dropdown, select, radio group, category picker) must be explored to determine option data sources:

Priority order: `[API] > [DOM] > [AI]`

1. **Network traffic inspection**: Look for API responses containing enum lists (`agent-browser network requests --type xhr,fetch`).

2. **Interactive discovery**: Expand dropdowns or type into searchable inputs to observe async search requests.
3. **DOM option extraction**: For static `<select>` or custom lists, extract values via eval (`Array.from(select.options).map(o => ({ value: o.value, text: o.text }))`).
4. **Conditional / Cascading Linkages**: When selecting parent option A alters available options in child B, document the cascade dependency chain (`A -> B -> C`) and retrieval logic for each level.
5. **Skill Documentation**: Layer each enum in the generated Skill under `Enum Parameters` by `[API]`, `[DOM]`, or `[AI]` with executable code or interaction guidance. Uncollectible enums are marked `[collection failed]` without halting exploration.

---

## Expected Outcome Checks & Error Envelopes

Generated operation Skills must include explicit outcome verification:
- **HTTP status verification**: 200/201/204 response codes.
- **Response envelope verification**: Verify ID, status, or created object in JSON payload.
- **DOM / UI verification**: Verify success notification, toast, updated table row, or URL redirection.
- **Standard error envelope**: Scripts must return structured error objects:
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_FAILED",
      "message": "Required parameter 'email' is invalid",
      "details": {}
    }
  }
  ```
- **Permission & Account Limitations**: 401 Unauthorized, 403 Forbidden, read-only account constraints, or missing administrative scopes must be reported as **Prerequisites & Limitations**, never misclassified as technical forge implementation failures when the operation flow is otherwise verified.

---

## Black-Box Delivery & Execution

- The generated Skill package in `.agent-forge/output/<skill-name>/` must be fully self-contained.
- An independent black-box runner requires only the generated package and declared prerequisites.
- Unless the user explicitly requested live consequential execution, test execution must use harmless/dry-run parameters or verifiable non-destructive operations.
