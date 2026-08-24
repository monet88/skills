# Extraction Capability Exploration

This reference is used during Phase 2 for extraction capabilities.

## Runtime Boundary

All browser commands must use the current forge run:

```text
python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- <agent-browser-command>
```

Never invoke raw `agent-browser` for forge-controlled exploration. The wrapper owns trusted config and the isolated named session.

## Goal

Prioritize discovering API endpoints and confirming data accessibility through structured network evidence and verified direct replay. When direct HTTP cannot be independently constructed or verified, fall back to browser-session network capture, then DOM extraction.

Every extraction capability must be classified as exactly one of:
- `DIRECT_API_VERIFIED`: Endpoint replayed outside browser with parameter variation; steady-state runtime needs no browser.
- `BROWSER_SESSION_API`: Response is structured, but request relies on browser session, dynamic tokens, or page signatures.
- `DOM_ONLY`: No viable API; data extracted from rendered DOM or embedded SSR state.
- `HYBRID`: Composed workflow using more than one of the above.

---

## Exploration Decision Tree

```text
Start HAR Capture → Navigate → Read traffic → Found candidate API?
  ├── Yes → Test Transparency & Completeness
  │     ├── Transparent & Complete → [API Verification (Direct Replay)]
  │     │     ├── Passes with Parameter Variation → DIRECT_API_VERIFIED (Emit Python Client)
  │     │     └── Fails Direct Replay → [UI Trigger + Network Capture] (BROWSER_SESSION_API)
  │     ├── Transparent but Incomplete → [UI Completion] → [API Verification]
  │     └── Opaque / Signed / Session-bound → [UI Trigger + Network Capture] (BROWSER_SESSION_API)
  └── No → [DOM Extraction] (DOM_ONLY)

Verification failure fallback: [API Verification] → [UI Trigger + Network Capture] → [DOM Extraction] → Report Obstacle

List capabilities → [Pagination Verification] (Verify page 2 differs from page 1)
All extraction paths → [Enumeration Collection] (Layered [API] > [DOM] > [AI])
Stop HAR Capture → Offline Endpoint & Schema Analysis
```

---

## Navigation and Endpoint Discovery

1. **Start HAR Capture**:
   Always begin HAR recording before performing target interactions so durable evidence is captured:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- network har start
   ```

2. **Navigate to Target Page**:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- open <target-url>
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- wait --load networkidle
   ```

3. **Inspect Structured Network Output**:
   Filter tracked requests by domain or API keyword:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- network requests --json
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- network requests --filter api
   ```

4. **Request Detail Lookup via Real requestId**:
   Always use the actual returned `requestId` from the network requests list rather than a display ordinal:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- network request <requestId> --json
   ```

5. **Stop HAR Recording**:
   Save the HAR to the private run directory for offline analysis:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- network har stop .agent-forge/runs/<run-id>/capture.har
   ```

---

## Endpoint Evaluation

Evaluate candidate endpoints for two properties:

### 1. Transparency
Can the request parameters and headers be independently constructed outside the browser?
- **Transparent**: Query parameters and JSON bodies use clear, reconstructible values (e.g. `?q=query&page=1&sort=date`). Proceed to evaluate parameter completeness.
- **Opaque / Signed**: Contains dynamic HMACs, encrypted request payloads, one-time anti-CSRF signatures, or device fingerprints. Fall back to **[UI Trigger + Network Capture]** (`BROWSER_SESSION_API`).

### 2. Parameter Completeness
Do the observed parameters cover all settable options in the UI?
- **Complete**: Query string or POST body covers the required filters and pagination. Proceed to **[API Verification]**.
- **Incomplete**: Endpoint parameters do not match visible controls on the page. Proceed to **[UI Completion]**.

---

## UI Completion

Let the page UI expose all settable parameters in one interaction:

1. **Scan Form Controls**:
   Extract structured controls from the active DOM:
   ```text
   python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- eval --stdin <<'EOF'
   JSON.stringify(Array.from(document.querySelectorAll('input, select, textarea, [role="combobox"]')).map(el => ({
     tag: el.tagName,
     type: el.type,
     name: el.name,
     id: el.id,
     placeholder: el.placeholder,
     value: el.value,
     options: el.tagName === 'SELECT' ? Array.from(el.options).map(o => ({ text: o.textContent.trim(), value: o.value })) : undefined
   })))
   EOF
   ```

2. **Batch-Fill Unique Test Values**:
   Fill each input with a unique incrementing value (e.g. 1001, 1002) to map POST fields back to UI controls.

3. **Trigger Request and Compare Traffic**:
   Submit the form/filter, inspect newly added network requests using `network requests --json`, and map parameters.

---

## API Verification (Direct Replay)

Observed traffic is evidence, not proof. An endpoint is marked `DIRECT_API_VERIFIED` only after direct replay outside the browser passes.

### Verification Criteria
1. **Replay Outside Browser**:
   Construct an independent HTTP request (using Python `urllib.request` or `forge-runtime.py verify-endpoint`) without launching agent-browser. Include only minimum required headers (`User-Agent`, `Accept`, `Authorization` or required cookies).
2. **Meaningful Parameter Variation**:
   Execute at least two requests with different business parameters:
   - Query variation: `q=termA` vs `q=termB` (responses must reflect different relevant items).
   - Pagination variation: `page=1` vs `page=2` (records on page 2 must not duplicate page 1).
3. **Quantifiable Success Criteria**:
   - HTTP status code is 200 (or expected success).
   - Content-Type matches JSON/API.
   - Required data keys and types are present.
   - Result count and key field values match expectations.

When all criteria pass, classify as `DIRECT_API_VERIFIED` and generate a standalone Python client.

> **Fallback**: If direct replay fails (e.g. 401/403 due to session tokens or browser-only signatures), do not force a direct classification. Fall back immediately to **[UI Trigger + Network Capture]** (`BROWSER_SESSION_API`).

---

## UI Trigger + Network Capture (BROWSER_SESSION_API)

When the API response is structured but request construction requires browser session state or JavaScript signing:

1. **Parameter Injection via URL Navigation**:
   If the page reflects parameters in the URL (e.g. `https://example.com/search?q={keyword}`):
   ```text
   agent-browser open "https://example.com/search?q={keyword}&page={page}"
   agent-browser wait --load networkidle
   agent-browser network requests --filter <endpoint-keyword>
   agent-browser network request <requestId> --json
   ```

2. **Parameter Injection via UI Operations**:
   If parameters must be set through UI controls:
   ```text
   agent-browser snapshot -i
   agent-browser fill @ref "{keyword}"
   agent-browser click @ref
   agent-browser wait --load networkidle
   agent-browser network requests --filter <endpoint-keyword>
   agent-browser network request <requestId> --json
   ```

3. **Verify Parameter Variation & Pagination**:
   Confirm modifying injected parameters alters the captured response accordingly.

---

## DOM Extraction (DOM_ONLY)

When no viable API endpoint exists:

1. **Check SSR Embedded State**:
   Inspect HTML for embedded JSON payloads (`__NEXT_DATA__`, `__NUXT__`, `window.__INITIAL_STATE__`, or `application/ld+json`). If present, extract directly via `eval --stdin`.

2. **Candidate Selector Evaluation**:
   Test selectors in batch:
   ```text
   agent-browser eval --stdin <<'EOF'
   const selectors = ['.product-card', '.item-row', 'article'];
   JSON.stringify(selectors.map(sel => {
     const els = document.querySelectorAll(sel);
     return { selector: sel, count: els.length, sampleText: els[0]?.textContent?.slice(0, 60) };
   }))
   EOF
   ```

3. **Static Extraction Script**:
   Write a clean extraction script returning structured JSON:
   ```text
   python scripts/<capability>.py | agent-browser eval --stdin
   ```

4. **AI Workflow (When Static Scripts Cannot Cover)**:
   For dynamic visual workflows, describe steps using abstract agent-browser commands and semantic locators (`snapshot -i`, `find role`, `click @ref`), never hardcoding ephemeral refs.

---

## Pagination Verification (Required for Lists)

Every list extraction capability must prove pagination:

1. **API Pagination**:
   Verify page 1 vs page 2 (`page=1` vs `page=2`, or `offset=0` vs `offset=20`, or cursor `next_token`):
   - Confirm item count > 0 for both pages.
   - Confirm first item ID on page 2 != first item ID on page 1.
   - Determine and record termination condition (`items.length == 0`, `has_more: false`, or next cursor missing).

2. **URL / DOM Pagination**:
   - URL pagination: navigate to page 2 URL, extract items, assert non-duplication.
   - DOM pagination: click next button (`find text "Next" click`), wait for DOM update, extract items, assert non-duplication.

Record pagination details in the generated `SKILL.md` under **Pagination Parameters**.

---

## Enumeration Collection

Proactively discover filter and dropdown options to enable parameterized execution:

1. **Hierarchy of Acquisition Methods**:
   `[API]` > `[DOM]` > `[AI]`
   - `[API]`: Dedicated endpoint returns option list (e.g. `/api/categories`).
   - `[DOM]`: Options read from `<select>` or dropdown list elements.
   - `[AI]`: Dynamic or visual menu requiring agent interaction.

2. **Cascading / Conditional Enumerations**:
   When option list B depends on selection A (e.g. Category -> Subcategory), record the dependency order.

3. **Handling Failures**:
   If an enumeration cannot be collected, mark it as `[collection failed]` (lowercase) in the generated Skill and continue.

---

## Agent-Browser Native Runtime Vocabulary

Use live agent-browser commands only. Never use BrowserAct vocabulary:

| Purpose | Agent-Browser Command |
|---|---|
| Open URL | `agent-browser open <url>` |
| Interactive snapshot | `agent-browser snapshot -i` |
| Semantic locator | `agent-browser find role <role> click --name "<name>"` |
| Wait load | `agent-browser wait --load networkidle` |
| Wait URL | `agent-browser wait --url "<pattern>"` |
| Wait text | `agent-browser wait --text "<text>"` |
| Network requests | `agent-browser network requests --json` |
| Request detail | `agent-browser network request <requestId> --json` |
| Clear network | `agent-browser network requests --clear` |
| HAR recording | `agent-browser network har start` / `agent-browser network har stop <path>` |
| Offline mode | `agent-browser set offline on` / `agent-browser set offline off` |
| Tab management | `agent-browser tab` / `agent-browser tab <tabId>` / `agent-browser tab new <url>` |
| Dialog handling | `agent-browser dialog status` / `agent-browser dialog accept [text]` / `agent-browser dialog dismiss` |
| JavaScript eval | `python scripts/<feature>.py <args> \| agent-browser eval --stdin` |
| Close browser | `agent-browser close` |

---

## Ref Discipline

- Snapshot refs (@ref) exist only in active browser memory.
- Never write concrete snapshot refs into generated `SKILL.md`, scripts, manifests, or provenance files.
- Browser-dependent scripts must use stable selectors, semantic `find`, or dynamically resolve refs at runtime.

## Evidence and Privacy Boundary

- Raw HAR recordings, auth cookies, tokens, and exploration logs must reside under `.agent-forge/runs/<run-id>/`.
- Never commit `.agent-forge/` artifacts into git.
- Manifest and provenance files store hashes and redacted metadata, never raw secret credentials.

