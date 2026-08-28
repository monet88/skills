# Generated Skill Output Contract

This reference is used during Phase 3 to generate reusable Skill packages. Generated output remains private under `.agent-forge/output/<skill-name>/` until the user explicitly exports it.

---

## Directory Structure

Each generated capability package must contain a `SKILL.md` entrypoint plus only the scripts, references, client files, manifests, and provenance required by the verified implementation.

```text
.agent-forge/output/<skill-name>/
├── SKILL.md
├── README.md
├── endpoint-manifest.json
├── provenance.json
├── client.py                  # Standalone client when any endpoint is DIRECT_API_VERIFIED
├── models.py                  # Typed data models when schema is observed
└── scripts/
    └── <feature>.py           # Python JS-emitter for browser-dependent paths
```

### Naming Conventions
- `<skill-name>`: Root folder for the skill suite, kebab-case (e.g. `github-issue-extractor`, `store-product-scraper`).
- `<site-slug>-<capability-slug>`: Specific capability identifier (e.g. `store-list-products`).
- Filenames use lowercase letters, digits, and hyphens (`client.py`, `scripts/extract-items.py`). No spaces or uppercase.

## Reusable Strategy Rules

- Do not include task-specific usernames, search terms, one-off URLs, secret values, or raw capture data.
- Do not persist concrete snapshot refs. Browser-dependent paths must resolve targets again at execution time.
- Do not label an observed endpoint as direct unless direct replay plus meaningful parameter variation passed.
- Keep browser dependency only for classifications that actually require browser/session state.
- For `DIRECT_API_VERIFIED`, the steady-state runtime must be usable without launching agent-browser.

## Package Refinement and Rebuild Semantics

- **Refinement by Default**: Invocations of `generate-skill` against an existing skill directory refine the package rather than wiping it. Endpoints and components are merged by stable identity (`id` or `path`+`method`), preserving unaffected endpoints and helper scripts in `scripts/`. Provenance records `refined: true`.
- **Corrupted Package Safety (`FRESH_REQUIRED`)**: If target package files are structurally corrupted or unparseable, generation fails with error code `FRESH_REQUIRED` requiring an explicit `--fresh` run.
- **Explicit Clean Rebuild (`--fresh`)**: Passing `--fresh` performs a clean, from-scratch rebuild of the skill package directory.
- **Non-Interactive Execution Invariant**: Forge execution is strictly non-interactive. Interactive commands and flags (`chat`, `--confirm-interactive`, `--confirm-actions`) are blocked. Human questions or confirmations route through the coordinator/host layer.

## Error Envelope and Outcome Checks

Generated scripts and strategies must return structured JSON envelopes for predictable automation:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

On failure:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable description",
    "details": {}
  }
}
```

Generated JS must return the defined error envelope for expected structural failures instead of crashing.

## Enum Parameters Layering

In generated `SKILL.md`, document parameter retrieval under `Enum Parameters` layered by priority:
1. `[API]`: Direct endpoint URL, method, and response path.
2. `[DOM]`: Semantic selector and evaluation method.
3. `[AI]`: Interaction instructions when code retrieval is impossible.
Include inline comments `// {param_name} enumeration retrieval: ...` within generated scripts/strategies.

## Browser-Side JavaScript

When a generated browser-dependent script emits JavaScript, make the Python file assemble only browser-side JS and business parameters. The canonical cross-shell execution forms are:

**POSIX (Bash / Zsh):**
```bash
python scripts/{feature}.py [options] | agent-browser eval --stdin
```

**Windows (PowerShell / Command Prompt):**
```bash
python scripts/{feature}.py [options] > temp_eval.js
cmd.exe /c "agent-browser eval --stdin < temp_eval.js"
```

---

## SKILL.md Specification

Every generated capability package contains a `SKILL.md` as its primary public interface:

````markdown
---
name: {site-slug}-{capability-slug}
description: "{Capability summary — site name + capability + input/output overview}. Use when the user asks to {trigger phrases covering casual/formal keywords}."
---

# {site-name} — {capability-name}

> Classification: `{DIRECT_API_VERIFIED | BROWSER_SESSION_API | DOM_ONLY | HYBRID}`
> {one-line input → output description}

## Language

All process output follows the user's language. Code comments, logs, and output schemas remain in English.

## Objective

{Single sentence describing the capability's goal.}

## Prerequisites

- For `DIRECT_API_VERIFIED`: Python 3.8+ (no browser required).
- For `BROWSER_SESSION_API` / `DOM_ONLY`: `agent-browser` installed and target page accessible.
- Authentication: {Declared auth requirements, e.g. active login session or API token}.

## Pre-execution Checks

1. **Prerequisite Verification**:
   Verify declared dependencies are present (Python for direct API; `agent-browser` and named session for browser paths).
2. **Session / Auth Verification**:
   If authentication is required, confirm active session before running.

## Capability Components

### {DIRECT_API_VERIFIED Component} (when direct HTTP was verified)

`python client.py {command} [options]`

Parameters:
- `--query <string>`: Search query or filter keyword.
- `--page <int>`: Page number (default: 1).
- `--limit <int>`: Items per page (default: 20).

Output example:
```json
{
  "items": [
    {
      "id": "item-123",
      "title": "Example Item",
      "price": 19.99,
      "category": "electronics"
    }
  ],
  "page": 1,
  "total": 42,
  "has_more": true
}
```

### {BROWSER_SESSION_API / DOM_ONLY Component} (when browser is required)

**POSIX (Bash / Zsh):**
```bash
python scripts/{feature}.py [options] | agent-browser eval --stdin
```

**Windows (PowerShell / Command Prompt):**
```bash
python scripts/{feature}.py [options] > temp_eval.js
cmd.exe /c "agent-browser eval --stdin < temp_eval.js"
```

Parameters:
- `--query <string>`: Search filter.
- `--page <int>`: Target page.

Output example:
```json
{
  "items": [
    {
      "title": "Example Item",
      "url": "https://example.com/items/123"
    }
  ],
  "page": 1
}
```

## Enum Parameters

| Parameter | Type | Source & Acquisition Method | Options / Values |
|---|---|---|---|
| `category` | string | `[API]` `/api/categories` -> `[item.slug]` | `electronics`, `books`, `home` |
| `status` | string | `[DOM]` `<select id="status">` options | `open`, `closed`, `all` |
| `sort` | string | `[API]` `/api/sort-options` | `price_asc`, `price_desc`, `newest` |

*Note: Uncollectable enum options are marked `[collection failed]`.*

## Pagination Parameters

| Parameter | Type | Mechanism | Termination Condition |
|---|---|---|---|
| `page` | integer | Query parameter `?page={n}` | `items.length == 0` or `page * limit >= total` |

## Quantifiable Success Criteria

- HTTP status 200 or clean script execution.
- Response contains expected top-level key `items` (Array).
- Array length > 0 on valid queries.
- Each item contains required fields (`id`, `title`).

## Error Envelope

When a structural failure occurs, the generated client or script returns:
```json
{
  "error": true,
  "code": "ELEMENT_NOT_FOUND | AUTH_EXPIRED | RATE_LIMITED | INVALID_RESPONSE",
  "message": "Human-readable diagnostic description"
}
```

## Recovery & Revalidation Lifecycle

1. **Fast Path**: Execute the known verified implementation (`python client.py` for direct/hybrid APIs, or `python scripts/{feature}.py` for browser extraction).
2. **Revalidation**: On unexpected failure (e.g. 401/403 or missing selector), revalidate using `python <agent-browser-skill-forge-root>/scripts/forge-runtime.py revalidate-skill --package-dir .` to test known endpoints/selectors.
3. **Drift Repair**: Update parameters/headers or refresh auth tokens if expired.
4. **Re-exploration**: Only enter forge re-exploration if the target website architecture fundamentally changed.

## Experience Notes

- Record notable observations, timing hints, or rate limits here.
````

---

## Standalone Python Client Template (`client.py`)

For any package containing at least one `DIRECT_API_VERIFIED` endpoint, emit a zero-setup Python client:

```python
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "{base_url}"


class APIClient:
    def __init__(self, base_url=BASE_URL, auth_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("{AUTH_ENV_VAR}")
        if not self.auth_token:
            self._discover_auth()

    def _discover_auth(self):
        client_path = Path(__file__).resolve()
        for ancestor in client_path.parents:
            if ancestor.name == ".agent-forge":
                auth_file = ancestor / "auth.json"
                if auth_file.exists():
                    try:
                        auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                        self.auth_token = auth_data.get("token") or auth_data.get("auth_token")
                    except Exception:
                        pass
                return

    def _request(self, path, params=None, data=None, method="GET"):
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url += f"?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        encoded_data = json.dumps(data).encode("utf-8") if data else None
        if encoded_data:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return {"error": True, "code": "AUTH_EXPIRED", "message": f"Authentication token expired or unauthorized (HTTP {exc.code})"}
            return {"error": True, "code": f"HTTP_{exc.code}", "message": f"HTTP request failed with status {exc.code}"}
        except Exception as exc:
            return {"error": True, "code": "REQUEST_FAILED", "message": "HTTP request failed due to client connection error"}

    def {operation_name}(self, **kwargs):
        # Render path, query, and body arguments from the verified endpoint manifest.
        path = "{endpoint_path}"
        params = {query_params}
        data = {body_data}
        return self._request(path, params=params, data=data, method="{http_method}")


def main():
    parser = argparse.ArgumentParser(description="{capability_name} standalone client")
    {cli_argument_definitions}
    args = parser.parse_args()

    client = APIClient()
    result = client.{operation_name}({cli_call_arguments})
    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Generation rules for `client.py`:
- Emit one method per `DIRECT_API_VERIFIED` endpoint, including direct components inside `HYBRID` packages.
- Derive method names, HTTP methods, path/query/body parameters, and CLI flags from verified endpoint metadata; do not hard-code a task-specific operation.
- For explicit endpoint arrays, do not invent an `extract_items` operation. A compatibility alias is allowed only for the intentional flat-spec legacy path.
- File-based zero-setup auth discovery is allowed only when `client.py` itself is inside a `.agent-forge` ancestor. Exported clients outside that private boundary must use explicit or environment-provided auth.


### Verified Auth Renewal & Bounded Retry Template

When `auth_renewal` is backed by a verified receipt, `client.py` includes `_renew_auth(self)` with bounded single-retry semantics:

```python
    def _renew_auth(self):
        """Renew authentication using the verified renewal endpoint.
        Bounded to a single renewal attempt."""
        if not self.refresh_token:
            self._discover_auth()
        if not self.refresh_token:
            return False
        # Call renewal endpoint and update self.auth_token + .agent-forge/auth.json
        ...
```

On 401/403 triggers, `_request(..., _is_retry=False)` invokes `self._renew_auth()` and retries once with `_is_retry=True`. If the retry or renewal fails, it returns `{"error": True, "code": "AUTH_EXPIRED", "message": "Authentication token expired and renewal failed"}`.

#### Manifest & Provenance Schema (`auth_renewal`)

```json
{
  "type": "refresh_endpoint",
  "trigger_statuses": [401, 403],
  "endpoint": {
    "path": "/api/auth/refresh",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "body_template": {"refresh_token": "{refresh_token}"}
  },
  "token_mapping": {
    "source_field": "access_token",
    "target_header": "Authorization",
    "target_format": "Bearer {token}"
  },
  "receipt_id": "rcpt_...",
  "receipt_hash": "...",
  "receipt_version": "1.0"
}
```
---

## Python JS-Emitter Template (`scripts/<feature>.py`)

For browser-dependent paths (`BROWSER_SESSION_API` / `DOM_ONLY`):

```python
import argparse
import json
import sys


def build_js(query=None, limit=20):
    query_json = json.dumps(query)
    limit_json = json.dumps(limit)
    return f"""
(() => {{
  try {{
    const query = {query_json};
    const limit = {limit_json};
    const rows = Array.from(document.querySelectorAll('.item-card, .list-row'));
    if (!rows.length) {{
      return JSON.stringify({{ error: true, code: "ELEMENT_NOT_FOUND", message: "No item elements found in DOM" }});
    }}
    const items = rows.slice(0, limit).map(row => ({{
      title: row.querySelector('.title, h3, a')?.textContent?.trim() || '',
      url: row.querySelector('a')?.href || '',
      price: row.querySelector('.price')?.textContent?.trim() || null
    }}));
    return JSON.stringify({{ items, count: items.length }});
  }} catch (err) {{
    return JSON.stringify({{ error: true, code: "EXTRACTION_FAILED", message: err.message }});
  }}
}})()
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", default=None)
    parser.add_argument("--limit", "-l", type=int, default=20)
    args = parser.parse_args()
    sys.stdout.write(build_js(query=args.query, limit=args.limit))


if __name__ == "__main__":
    main()
```

---

## endpoint-manifest.json Schema

```json
{
  "skill_name": "example-skill",
  "target_origin": "https://example.com",
  "generated_at": "2026-08-24T12:00:00Z",
  "endpoints": [
    {
      "id": "list-items",
      "method": "GET",
      "path": "/api/v1/items",
      "classification": "DIRECT_API_VERIFIED",
      "parameters": {
        "query": { "type": "string", "in": "query", "name": "q", "required": false },
        "page": { "type": "integer", "in": "query", "name": "page", "default": 1 },
        "limit": { "type": "integer", "in": "query", "name": "limit", "default": 20 }
      },
      "verification": {
        "status": "PASSED",
        "verified_at": "2026-08-24T12:00:00Z",
        "tested_variations": [
          { "params": { "page": 1 }, "status": 200, "item_count": 20 },
          { "params": { "page": 2 }, "status": 200, "item_count": 20 }
        ]
      }
    }
  ]
}
```

---

## provenance.json Schema

```json
{
  "forge_version": "0.1.0",
  "agent_browser_version": "agent-browser 0.34.0",
  "target_origin": "https://example.com",
  "timestamp": "2026-08-24T12:00:00Z",
  "har_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "capabilities": [
    {
      "name": "example-list-items",
      "classification": "DIRECT_API_VERIFIED",
      "steady_state_runtime": "python",
      "verified_endpoint": "/api/v1/items"
    }
  ],
  "verification_summary": {
    "direct_api_count": 1,
    "browser_session_count": 0,
    "dom_only_count": 0,
    "all_passed": true
  }
}
```

---

## Delivery & Black-Box Testing Specification

### 1. Independent Sub-Agent Tester Protocol

Independent testing runs in an isolated sub-agent or harness session. The tester receives ONLY:
1. The path to the generated Skill package (`.agent-forge/output/<skill-name>/` or exported destination).
2. Declared environment prerequisites (Python 3.8+ / `agent-browser`).
3. Minimal test cases covering all advertised components.

Forge internal state (e.g. `runtime.json`, `.agent-forge/runs/`, raw HAR files) and coordinator history are withheld.

### 2. Standardized Sub-Agent Prompt

```text
Read {path_to_skill_package}/SKILL.md as your execution guide.

Test cases:
{test_cases_json_or_list}

Execution requirements:
- Follow SKILL.md instructions strictly; do not assume coordinator-specific capabilities.
- For DIRECT_API_VERIFIED: verify by executing `client.py` and importing `APIClient` in Python; steady-state testing must not start agent-browser.
- For BROWSER_SESSION_API / DOM_ONLY: execute via documented agent-browser commands using only standard shell pipelines.
- Record specific issues if instructions are unclear or missing.

Report after execution:
1. Component results (pass/fail per component)
2. Failure reasons (if any)
3. Unclear parts in SKILL.md instructions (if any)
4. Severe accuracy or performance issues (if any)
5. Output summary (sanitized; never leak raw secrets)
```

### 3. Structured Test Report Schema

```json
{
  "package_dir": ".agent-forge/output/example-skill",
  "all_passed": true,
  "components": [
    {
      "name": "list_items",
      "classification": "DIRECT_API_VERIFIED",
      "steady_state_runtime": "python",
      "status": "PASSED",
      "import_check": true,
      "cli_check": true,
      "output_summary": {
        "item_count": 5,
        "sample_keys": ["id", "title", "price"]
      }
    }
  ],
  "unclear_instructions": [],
  "severe_issues": [],
  "failures": []
}
```

### 4. Canonical Installation UX

```bash
# Project-level skill installation
npx skills add ".agent-forge/output/<skill-name>" --agent <agent-name> --copy -y
```

Installation failure must be reported clearly and must never delete or corrupt the accepted package in `.agent-forge/output/<skill-name>/`.
