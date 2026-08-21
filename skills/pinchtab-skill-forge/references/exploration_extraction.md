# Extraction Capability Exploration

This file is read during Phase 2 execution (extraction capabilities only).

**Goal**: Prioritize discovering API endpoints and confirming data accessibility; when requests cannot be independently constructed, use UI triggers + network capture to obtain structured responses; fall back to DOM extraction only when both approaches are infeasible.

All browser interaction below runs through the `pinchtab` CLI in the session created in Phase 0 (`PINCHTAB_SESSION` set). JS snippets run via `pinchtab eval` and must be IIFEs returning `JSON.stringify(...)`.

**Pass Criteria** (API path):
- `fetch()` reproduction verification passes, returned data matches page display (item count, key field values)
- List data pagination works (page 2 data does not duplicate page 1)
- Enumeration parameter acquisition methods are determined (passes even if some are marked `[collection failed]`)

**Pass Criteria** (UI trigger + Network Capture path):
- Target API requests can be stably triggered via URL navigation or UI operations
- Response data read from `pinchtab network <id> --body` is structured with complete field coverage
- Parameters can be injected via URL query string or UI controls
- List data pagination works

**Pass Criteria** (DOM path):
- Target data can be stably extracted from DOM with complete field coverage
- List data pagination works (different data is extracted after pagination)

---

## Exploration Decision Tree

```
Navigate → Read traffic → Found API with target data?
  ├── Yes → Can request be independently constructed?
  │     ├── Yes → Parameters complete?
  │     │     ├── Yes ──────────────→ [API Verification]
  │     │     └── No → [UI Completion] → [API Verification]
  │     └── No ──────────────────→ [UI Trigger + Network Capture]
  └── No → [DOM Extraction]

Verification failure fallback: [API Verification] → [UI Trigger + Network Capture] → [DOM Extraction] → [AI Workflow] → Report obstacle

List type → [Pagination Verification]
All paths ultimately → [Enumeration Collection]
```

---

## Navigation and Endpoint Discovery

Navigate to the target page, wait for loading to complete, then read traffic:

```
pinchtab nav {target URL} --snap --block-images
pinchtab wait --load network-idle --idleFor 800
pinchtab network --filter {domain keyword}
```

Extract the most distinctive keyword from the target URL (e.g., `github`, `notion`, `jira`) to cover both the main domain and API subdomains while excluding third-party tracking noise. If no match, drop `--filter` to see all traffic.

When page-load traffic yields no match (SPA scenarios), perform one target interaction (search, toggle filter, scroll to load), then read newly added traffic. To attribute requests to that single interaction precisely:

- Preferred (non-destructive): note the baseline first — `pinchtab network --limit 100` — interact, then compare for new entries.
- Acceptable once earlier traffic has already been mined: `pinchtab network clear` immediately before the interaction, interact, then `pinchtab network --filter ...`.

After finding candidate endpoints:

```
pinchtab network {requestId} --body
```

Record: URL, method, response structure. Also note whether initial traffic contains **enumeration prefetch requests** (returning dropdown options, category lists) for priority use in later enumeration collection. Browser extensions also make requests in the page context — filtering by extension keywords can reveal API data provided by them. The buffer is rolling: read soon after interactions; for long crawls stream to a file instead (`curl -N "http://localhost:9867/network/export/stream?format=ndjson&path=tmp/live.ndjson"`).

---

## Endpoint Evaluation

After obtaining an endpoint, determine two things:

**Transparency**: Can request parameters be independently constructed?
- Parameter names clear and parameterizable → Transparent, evaluate parameter completeness
- Contains opaque encoding, dynamic tokens, serialized structures → Opaque, but response data still structured → Enter **[UI Trigger + Network Capture]** (let the site's own JS handle signing; inject parameters via URL navigation or UI operations; read responses from network)

**Parameter Completeness** (only for transparent endpoints): Do observed parameters cover all settable options in the UI?
- URL contains filter parameters (e.g., `?minPrice=10&maxPrice=50`) → Read directly, usually complete
- **Check page URL and Referer header**: after the first interaction, the current page URL or request Referer may already contain the complete parameter mapping — decoding it is faster than analyzing the request body
- Endpoint parameters clearly fewer than visible controls → Incomplete, enter **[UI Completion]**

Both satisfied → proceed directly to **[API Verification]**.

---

## UI Completion

Let the page UI help you complete all unknown parameters at once. Goal: **set all controls to non-default values before triggering search, exposing all parameters in one search.**

1. One eval to scan all form controls, returning a structured map (checkbox/radio labels + checked state, all select options — for associating enum values in step 6):
   ```bash
   pinchtab eval "(() => JSON.stringify(Array.from(document.querySelectorAll('input, select, textarea, [role=\"combobox\"]')).map(el => {
     const b = { tag: el.tagName, type: el.type, name: el.name, id: el.id, ph: el.placeholder, val: el.value };
     if (el.type === 'checkbox' || el.type === 'radio') {
       b.checked = el.checked;
       b.label = (el.labels?.[0] || el.closest('label') || el.parentElement)?.textContent?.trim()?.slice(0, 50) || '';
     }
     if (el.tagName === 'SELECT')
       b.opts = Array.from(el.options).map(o => ({ t: o.textContent.trim(), v: o.value }));
     return b;
   })))()"
   ```
   When control purpose is hard to determine from returned info, supplement with one `pinchtab screenshot`. Unclear labels don't block progress — step 6's unique-value mapping will automatically associate controls with API parameters.
2. One eval to batch-fill all text/number inputs, **filling each control with a unique value** (incrementing numbers 1001, 1002, 1003…) to enable precise reverse lookup of which POST parameter corresponds to which control:
   ```bash
   pinchtab eval "(() => {
     const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
     const fills = [ ['{selector1}', '1001'], ['{selector2}', '1002'] ];
     fills.forEach(([sel, val]) => {
       const el = document.querySelector(sel);
       if (el) { setter.call(el, val); el.dispatchEvent(new Event('input', {bubbles: true})); }
     });
     return 'filled: ' + fills.length;
   })()"
   ```
3. Select non-default options for remaining controls:
   - checkbox / radio: one eval to batch-check (`querySelectorAll('input[type=checkbox]:not(:checked)').forEach(el => el.click())`)
   - Native `<select>`: eval to set `.value` + trigger `change` event — or use `pinchtab select {ref} {value}`
   - Component-library dropdowns: try one eval via component instance; **if it fails, use `pinchtab click` interaction**
   - Range sliders (noUiSlider etc.): eval batch-set (`slider.noUiSlider.set([min, max])`) together with other controls in the same round — don't test each slider individually
4. Window the traffic (baseline or `clear`, see above), then trigger one complete request: `pinchtab click {ref}` on search/apply/confirm
5. `pinchtab wait --load network-idle`, then read newly added requests for the complete parameter structure:
   ```
   pinchtab network --filter {domain keyword}
   pinchtab network {requestId} --body
   ```
6. Compare before/after requests, confirm all parameters are covered; use step 1's DOM label/value mapping to associate enum values in the POST body (checkbox value ↔ POST array elements, select option value ↔ POST field values), producing a "control label → API parameter name:value" mapping table for direct use in enumeration collection

---

## API Verification

### fetch() Reproduction

Use `pinchtab eval --await-promise` to call the discovered endpoint from inside the page (same-origin, cookies included), confirming data accessibility:

```bash
pinchtab eval --await-promise "(async () => {
  const r = await fetch('{endpoint}?page=1&limit=20');
  const d = await r.json();
  return JSON.stringify({ total: d.total, count: d.items?.length, sample: d.items?.[0] });
})()"
```

Batch similar verification actions (validity of multiple parameters, reachability of multiple endpoints) into a single eval, comparing return differences.

> **DOM Supplement**: If the API response cannot cover all target fields, supplement with DOM extraction for missing fields, combining both in the capability component.

> **Fallback**: fetch() returns unexpected results (HTTP error, CORS rejection, response structure mismatch, empty data) → fall back to [UI Trigger + Network Capture].

---

## UI Trigger + Network Capture

Enter this path when API response data is structured and usable, but the request contains dynamic signatures, tokens, or parameters that cannot be independently constructed. Core idea: let the site's own JS handle signing and authentication, inject business parameters via URL or UI, and read structured responses from captured traffic.

### Determine Parameter Injection Method

From requests already observed, identify which are business parameters (keywords, page numbers, filters):

1. **Check page URL**: does the current URL query string contain business parameters (e.g., `?q=keyword&page=2`)? Yes → inject via URL navigation
2. **Not in URL**: parameters are in the request body → inject via UI control operations (fill search box, select filters, click search)

Both may coexist.

### Verification: URL Navigation Injection

Construct a URL with business parameters, navigate, then read the response from traffic:

```
pinchtab nav {target URL with parameters}
pinchtab wait --load network-idle
pinchtab network --filter {endpoint keyword}
pinchtab network {requestId} --body
```

Confirm response matches expectations (field structure, data count). Repeat with modified parameters to confirm changes are reflected.

### Verification: UI Operation Injection

Window the traffic, operate UI controls, then capture the generated request:

1. `pinchtab network clear` (earlier traffic already mined at this point)
2. Operate UI controls to inject parameters — `pinchtab fill {ref} {value}` / `pinchtab select {ref} {value}` / `pinchtab click {ref}` on filters
3. Trigger the request (click search / submit)
4. `pinchtab wait --load network-idle`
5. `pinchtab network --filter {endpoint keyword}` → `pinchtab network {requestId} --body`
6. Confirm response contains target data

For interactions whose window spans many unrelated requests, export instead of reading inline: `curl "http://localhost:9867/network/export?format=har&body=true&output=file&path=tmp/window.har"` after the interaction, then extract the target entry from the file.

### Record

- Endpoint URL characteristics (for locating target requests in traffic)
- Parameter injection method (URL pattern / UI operation steps)
- Response structure (field names, types, nesting relationships)

> **Fallback**: cannot stably trigger target requests, or response incomplete/unusable → fall back to [DOM Extraction].

---

## DOM Extraction

Enter this path when no API endpoint exists for target data, or when UI Trigger + Network Capture also cannot obtain structured data.

When target data is absent from current DOM, means to make it appear (try in order):
1. `pinchtab nav` to a sub-page/detail-page URL containing the data
2. Click a "Show all" / "See more" link that navigates to the data
3. Tab or section navigation within the page (`pinchtab snap -i -c` then `click {ref}`)
4. Keyboard-driven scroll to trigger lazy loading (`pinchtab press End`)
5. `pinchtab scroll 1500`

Before selector extraction, check whether the page already embeds structured data (SSR frameworks often embed full page data as JSON in HTML). One eval scans candidates:

```bash
pinchtab eval "(() => {
  const keys = Object.keys(window).filter(k => /state|data|init|preload|nuxt|next/i.test(k)).slice(0, 20);
  const scripts = [...document.querySelectorAll('script[type=\"application/json\"], script[type=\"application/ld+json\"]')].length;
  return JSON.stringify({ globals: keys.map(k => ({ k, size: ((typeof window[k]==='object'&&window[k])?JSON.stringify(window[k]).length:0) })), jsonScripts: scripts });
})()"
```

When found, extract directly — more stable than selectors and more complete.

### Locate Target Data Elements

One eval to batch-test candidate selectors, returning a JSON summary — do not eval them individually:

```bash
pinchtab eval "(() => {
  const selectors = ['{candidate1}', '{candidate2}', '{candidate3}'];
  return JSON.stringify(selectors.map(sel => {
    const els = document.querySelectorAll(sel);
    return { sel, count: els.length, sample: els[0]?.textContent?.slice(0, 50) };
  }));
})()"
```

Refresh the page and re-test, comparing before/after to confirm stability.

### Write Static Extraction Script

After determining selectors, one eval completes all field extraction:

```javascript
// [Script] Extract list data
// Selector: '{list item selector}' (batch match + result check: items.length > 0)
const items = Array.from(document.querySelectorAll('{list item selector}')).map(el => ({
  '{field name}': el.querySelector('{sub-selector}')?.textContent.trim(),
  '{field name}': el.querySelector('{sub-selector}')?.getAttribute('{attribute}')
}));
return JSON.stringify(items)
```

(inside an IIFE; this becomes the body of a `scripts/*.py` file in Phase 3)

When steps require real-time judgment (dynamic loading, conditional rendering) → mark as **[AI Intervention]**: Agent performs visual operations before extraction.

### AI Workflow Alternative (When Static Script Cannot Cover)

If interaction is too complex (CAPTCHA walls, complex dynamic rendering, visual judgment), organize as AI Workflow.

**Writing Standards**:
1. Each step uses pinchtab subcommands in abstract form (no `PINCHTAB_SESSION` setup, no server management — Agent adds environment at runtime), followed by supplementary context, ending with `→ expected result`
2. Element references use only visual descriptions resolved through snapshots; **CSS selectors are forbidden in AI Workflow steps**
   - ✗ `eval "document.querySelector('button[type=submit]').click()"`
   - ✓ `snap -i -c` locate the blue "Submit" button at the bottom of the form → `click {ref}`
3. Record state checkpoints after key steps: `pinchtab url`, `pinchtab title`, visible element characteristics
4. Data extraction steps specify which command and which fields: `pinchtab text` / `text --full` / `eval "{extraction script}"`
5. Human-verification walls: pause via handoff (`curl -X POST http://localhost:9867/tabs/{tabId}/handoff ...`), user resolves in the headed window, then resume. Never attempt to defeat challenges.

> **Failure**: DOM selectors unstable, data incomplete, AI Workflow also cannot cover → report obstacles and attempted paths to the user, ask next steps.

---

## Pagination Verification (Required for List Data)

Skip for non-list types.

### API Pagination

Check pagination parameters in existing traffic (`page` / `offset` / `cursor` / `next_token`). Combine with fetch reproduction into one compound eval verifying endpoint reachability + pagination effectiveness simultaneously:

```bash
pinchtab eval --await-promise "(async () => {
  const r1 = await (await fetch('{endpoint page 1}')).json();
  const r2 = await (await fetch('{endpoint page 2}')).json();
  return JSON.stringify({
    p1_count: r1.{list field}?.length,
    p2_count: r2.{list field}?.length,
    different: r1.{list field}?.[0]?.{unique id} !== r2.{list field}?.[0]?.{unique id}
  });
})()"
```

(Cursor type: take `{cursor field}` from r1's response for the second request.)

### URL Pagination

Data is server-rendered; pagination navigates to a new URL. Extract the next-page URL pattern from the current URL or next link:

```bash
pinchtab eval "(() => JSON.stringify({ nextUrl: document.querySelector('{next page link selector}')?.href }))()"
```

`pinchtab nav {nextUrl}` → re-run extraction → confirm data differs.

### DOM Pagination

In-page click or scroll triggers pagination (no navigation):

```
pinchtab click {next-page ref}
pinchtab wait {item selector}
→ re-run extraction script, confirm page 2 data differs from page 1
```

### AI Pagination

When scripts cannot reliably judge pagination timing or termination (infinite scroll load completion, inconsistent triggers, challenge interruptions): Agent drives pagination visually per AI Workflow standards, confirming page 2 differs from page 1.

### Record

| Pagination Type | Characteristics / Trigger | Record |
|---------|----------------|------|
| API Pagination | `?page=2`, `?cursor=` request params | Param name + type (page/cursor) + next value source + termination condition |
| URL Pagination | Navigation to new URL, data in HTML | URL pattern + next-link selector + termination condition |
| DOM Pagination | Click button / scroll, no navigation | Trigger method + selector/ref + termination condition |
| AI Pagination | Script can't judge timing/termination | Visual operation description + termination signal |

> Network-capture-path pagination reuses the same mechanisms — trigger method identical, only data is read from `pinchtab network` instead of DOM or fetch.

---

## Enumeration Collection

During verification you **must proactively explore** every enumeration control on the page (dropdowns, selectors, radio groups) to determine the **data source and acquisition method** for their options. Don't record specific values — values change; recording acquisition methods is durable.

Priority order `API > DOM > AI`:

1. **Read current page traffic independently**: `pinchtab network --filter {domain keyword}` for requests returning enumeration lists. If buffer moved on, navigate back to the target page first
2. **Expand/interact with the control** (`pinchtab click {ref}`), observe whether async requests fire → record as above. Search-enabled controls (input + linked dropdown): enter a keyword to trigger the search API
3. **API endpoint found** → record endpoint URL + method + response structure; verify independent invocation feasibility. Verify enum values UI-first once, then batch-verify via API — never guess values then confirm via UI
4. **Independent invocation infeasible** → record hybrid method: prerequisites from page + how obtained + then how to call the API
5. **No API endpoint** → eval to read option values from DOM (native `<select>` reads `.options`; component-library controls try instance properties, else expand and read rendered results); record selectors and method
6. **DOM unstable too** → **[AI]** approach: describe the visual interaction operations the Agent performs

#### Conditional Enumeration (Cascading Linkage)

When cascading exists between enumeration controls (selecting A makes B's options appear/change), record the dependency chain (A→B→C) and each level's acquisition method.

#### Writing to Generated Skill

In the generated SKILL.md's "Enum Parameters" section, layer each enumeration's approach by `[API]` > `[DOM]` > `[AI]`. `[API]` and `[DOM]` must provide executable code; `[AI]` describes the Agent's interaction operations. Cover: acquisition method per enumeration + cascade dependency order. Operation steps retain inline comments `// {param_name} enumeration retrieval: ...`.

Mark uncollectable enumerations `[collection failed]` (always lowercase) and continue — do not block exploration.
