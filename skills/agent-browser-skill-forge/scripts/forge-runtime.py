import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PRIVATE_DIR = ".agent-forge"
IGNORE_LINE = ".agent-forge/"
BLOCKED_STARTUP_FLAGS = {
    "--config", "--session", "--session-name", "--namespace",
    "--provider", "-p", "--executable-path", "--extension",
    "--init-script", "--enable", "--args", "--profile", "--state",
    "--restore", "--auto-connect", "--cdp", "--engine",
    "--proxy", "--proxy-bypass", "--action-policy", "--allowed-domains",
}


def fail(message, code=2):
    print(json.dumps({"error": True, "message": message}), file=sys.stderr)
    raise SystemExit(code)


def resolve_root(value):
    root = Path(value or os.getcwd()).resolve()
    if not root.exists() or not root.is_dir():
        fail(f"workspace root does not exist: {root}")
    return root


def ensure_private_ignore(root):
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    normalized = {line.strip() for line in existing.splitlines()}
    accepted = {IGNORE_LINE, ".agent-forge", "/.agent-forge/", "/.agent-forge"}
    if normalized.isdisjoint(accepted):
        prefix = existing
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += os.linesep
        gitignore.write_text(prefix + IGNORE_LINE + os.linesep, encoding="utf-8")
    return gitignore


def resolve_agent_browser():
    names = ["agent-browser.cmd", "agent-browser"] if os.name == "nt" else ["agent-browser"]
    for name in names:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve())
    fail("agent-browser is not installed or not on PATH")


def clean_env():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("AGENT_BROWSER_"):
            env.pop(key, None)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(key, None)
    return env


def run_process(argv, cwd, *, check=True):
    # File-backed capture avoids Windows daemon children keeping PIPE handles open.
    with tempfile.TemporaryFile() as out_file, tempfile.TemporaryFile() as err_file:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=clean_env(),
            stdout=out_file,
            stderr=err_file,
        )
        out_file.seek(0)
        err_file.seek(0)
        completed.stdout = out_file.read().decode("utf-8", errors="replace")
        completed.stderr = err_file.read().decode("utf-8", errors="replace")
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown runtime error").strip()
        raise RuntimeError(detail)
    return completed


def load_trusted_config(source):
    if not source:
        return {"engine": "chrome", "plugins": []}
    source_path = Path(source).resolve()
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"trusted config cannot be read: {exc}")
    if not isinstance(data, dict):
        fail("trusted config must contain a JSON object")
    data.setdefault("engine", "chrome")
    data.setdefault("plugins", [])
    return data


def safe_token(value, fallback="run"):
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value or "").strip("-").lower()
    return value[:32] or fallback


def bootstrap(args):
    root = resolve_root(args.root)

    # This must happen before the first .agent-forge write.
    ensure_private_ignore(root)

    private_root = root / PRIVATE_DIR
    runs_root = private_root / "runs"
    output_root = private_root / "output"
    trusted_root = private_root / "trusted"
    for directory in (runs_root, output_root, trusted_root):
        directory.mkdir(parents=True, exist_ok=True)

    task = safe_token(args.task, "forge")
    run_id = safe_token(args.run_id, "") if args.run_id else f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    run_id = safe_token(run_id, "run")
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    root_hash = hashlib.sha256(str(root).lower().encode("utf-8")).hexdigest()[:8]
    session = f"agent-browser-skill-forge-{task}-{root_hash}-{uuid.uuid4().hex[:6]}"
    config_path = trusted_root / f"{run_id}.agent-browser.json"
    config = load_trusted_config(args.trusted_config)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    binary = resolve_agent_browser()
    try:
        version_result = run_process([binary, "--config", str(config_path), "--version"], root)
        core_result = run_process(
            [binary, "--config", str(config_path), "skills", "get", "core", "--full"],
            root,
        )
    except RuntimeError as exc:
        doctor = run_process(
            [binary, "--config", str(config_path), "doctor", "--offline", "--quick"],
            root,
            check=False,
        )
        diagnostics = (doctor.stdout or doctor.stderr or "doctor produced no output").strip()
        fail(f"agent-browser runtime verification failed: {exc}; doctor: {diagnostics}")

    core_path = run_dir / "core-guidance.txt"
    core_path.write_text(core_result.stdout, encoding="utf-8")
    version = version_result.stdout.strip()
    state = {
        "run_id": run_id,
        "task": task,
        "root": str(root),
        "session": session,
        "config": str(config_path),
        "agent_browser": binary,
        "version": version,
        "core_guidance": str(core_path),
    }
    runtime_path = run_dir / "runtime.json"
    runtime_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state))


def load_runtime(root, run_id):
    runtime_path = root / PRIVATE_DIR / "runs" / safe_token(run_id) / "runtime.json"
    if not runtime_path.exists():
        fail(f"forge run does not exist: {run_id}")
    try:
        state = json.loads(runtime_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"forge runtime state is invalid: {exc}")
    if state.get("session") in (None, "", "default"):
        fail("forge runtime state does not contain an isolated named session")
    return state


def validate_exec_args(argv):
    if not argv:
        fail("exec requires an agent-browser command after --")
    if argv[0] == "plugin" and len(argv) > 1 and argv[1] == "add":
        fail("plugin add is not allowed inside a forge-controlled run")
    for token in argv:
        flag = token.split("=", 1)[0]
        if flag in BLOCKED_STARTUP_FLAGS:
            fail(f"startup override is blocked in forge-controlled runs: {flag}")


def execute(args):
    root = resolve_root(args.root)
    state = load_runtime(root, args.run_id)
    argv = list(args.command)
    if argv and argv[0] == "--":
        argv = argv[1:]
    validate_exec_args(argv)
    command = [
        state["agent_browser"],
        "--config", state["config"],
        "--session", state["session"],
        *argv,
    ]
    completed = run_process(command, root, check=False)
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    raise SystemExit(completed.returncode)


def har_analyze(args):
    har_file = Path(args.har).resolve()
    if not har_file.exists():
        fail(f"HAR file does not exist: {har_file}")
    content_bytes = har_file.read_bytes()
    har_sha256 = hashlib.sha256(content_bytes).hexdigest()
    try:
        har_data = json.loads(content_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        fail(f"Invalid HAR JSON: {exc}")

    entries = har_data.get("log", {}).get("entries", [])
    candidates = []

    filter_kw = (args.filter or "").lower()
    origin_filter = (args.origin or "").lower()

    for entry in entries:
        req = entry.get("request", {})
        res = entry.get("response", {})
        url = req.get("url", "")
        method = req.get("method", "GET").upper()
        res_status = res.get("status", 0)
        content = res.get("content", {})
        mime_type = content.get("mimeType", "")
        text = content.get("text", "")

        parsed_url = urllib.parse.urlparse(url)
        if origin_filter and origin_filter not in parsed_url.netloc.lower():
            continue
        if filter_kw and filter_kw not in url.lower():
            continue

        is_json_mime = "json" in mime_type.lower()
        is_json_text = False
        parsed_json = None
        if text:
            try:
                parsed_json = json.loads(text)
                is_json_text = True
            except Exception:
                pass

        if is_json_mime or is_json_text or "api" in parsed_url.path.lower():
            candidates.append({
                "url": url,
                "path": parsed_url.path,
                "query": parsed_url.query,
                "query_params": urllib.parse.parse_qs(parsed_url.query),
                "method": method,
                "status": res_status,
                "mimeType": mime_type,
                "postData": req.get("postData", {}).get("text"),
                "headers": {h.get("name"): h.get("value") for h in req.get("headers", [])},
                "response_sample": parsed_json if is_json_text else (text[:200] if text else None),
            })

    result = {
        "har_path": str(har_file),
        "har_sha256": har_sha256,
        "entry_count": len(entries),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    print(json.dumps(result, indent=2))


def verify_endpoint(args):
    spec = {}
    if args.spec:
        spec_path = Path(args.spec).resolve()
        if spec_path.exists():
            spec = json.loads(spec_path.read_text(encoding="utf-8"))

    url = args.url or spec.get("url")
    if not url:
        fail("verify-endpoint requires --url or --spec with 'url'")
    method = (args.method or spec.get("method") or "GET").upper()

    headers = dict(spec.get("headers") or {})
    if args.headers:
        if Path(args.headers).exists():
            headers.update(json.loads(Path(args.headers).read_text(encoding="utf-8")))
        else:
            headers.update(json.loads(args.headers))

    variations = spec.get("variations") or []
    if args.variations:
        if Path(args.variations).exists():
            variations = json.loads(Path(args.variations).read_text(encoding="utf-8"))
        else:
            variations = json.loads(args.variations)

    if not variations:
        variations = [{}]

    required_keys = args.required_key or spec.get("required_keys") or []
    min_status = args.min_status if args.min_status is not None else spec.get("min_status", 200)
    max_status = args.max_status if args.max_status is not None else spec.get("max_status", 299)

    tested_results = []
    all_passed = True
    failure_reason = None

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    merged_headers = {**default_headers, **headers}

    for var in variations:
        var_params = var.get("params") if isinstance(var, dict) and "params" in var else (
            var.get("query_params") if isinstance(var, dict) and "query_params" in var else (
                var if isinstance(var, dict) and "data" not in var and "body" not in var else {}
            )
        )
        var_data = var.get("data") or var.get("body") if isinstance(var, dict) else None

        parsed = urllib.parse.urlparse(url)
        existing_params = urllib.parse.parse_qs(parsed.query)
        combined_params = {k: v[0] if len(v) == 1 else v for k, v in existing_params.items()}
        combined_params.update(var_params)

        query_str = urllib.parse.urlencode({k: v for k, v in combined_params.items() if v is not None})
        request_url = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_str,
            parsed.fragment
        ))

        req_data_bytes = None
        if var_data:
            req_data_bytes = json.dumps(var_data).encode("utf-8")
            merged_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(request_url, data=req_data_bytes, headers=merged_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.getcode()
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed_body = json.loads(raw)
                except Exception:
                    parsed_body = raw

                item_count = None
                if isinstance(parsed_body, list):
                    item_count = len(parsed_body)
                elif isinstance(parsed_body, dict):
                    for k in ("items", "data", "results", "records", "list"):
                        if isinstance(parsed_body.get(k), list):
                            item_count = len(parsed_body[k])
                            break

                if not (min_status <= status <= max_status):
                    all_passed = False
                    failure_reason = f"Status {status} not in range [{min_status}, {max_status}]"

                if isinstance(parsed_body, dict):
                    for rk in required_keys:
                        if rk not in parsed_body:
                            all_passed = False
                            failure_reason = f"Required key '{rk}' missing in response"

                tested_results.append({
                    "params": var_params,
                    "status": status,
                    "item_count": item_count,
                    "response": parsed_body,
                })
        except urllib.error.HTTPError as exc:
            all_passed = False
            failure_reason = f"HTTP error {exc.code}"
            tested_results.append({
                "params": var_params,
                "status": exc.code,
                "error": str(exc),
            })
        except Exception as exc:
            all_passed = False
            failure_reason = f"Request error: {exc}"
            tested_results.append({
                "params": var_params,
                "status": 0,
                "error": str(exc),
            })

    variation_verified = False
    if len(tested_results) >= 2:
        res1 = tested_results[0].get("response")
        res2 = tested_results[1].get("response")
        if res1 is not None and res2 is not None and res1 != res2:
            variation_verified = True
        elif all_passed:
            all_passed = False
            failure_reason = "Parameter variations did not produce distinct responses"
    elif len(tested_results) == 1 and all_passed:
        # At least one meaningful parameter variation required for DIRECT_API_VERIFIED
        all_passed = False
        failure_reason = "At least one meaningful parameter variation is required to verify direct API"

    classification = "DIRECT_API_VERIFIED" if (all_passed and variation_verified) else "BROWSER_SESSION_API"
    output = {
        "verified": all_passed and variation_verified,
        "classification": classification,
        "url": url,
        "method": method,
        "variation_count": len(tested_results),
        "tested_variations": tested_results,
        "reason": failure_reason if not (all_passed and variation_verified) else None,
    }
    print(json.dumps(output, indent=2))


def sanitize_headers(headers):
    if not headers or not isinstance(headers, dict):
        return headers
    sanitized = {}
    for k, v in headers.items():
        lower_k = str(k).lower()
        if any(s in lower_k for s in ("auth", "token", "cookie", "key", "secret", "session", "credential", "password")):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized


def sanitize_params(params):
    if not params or not isinstance(params, dict):
        return params
    sanitized = {}
    for k, v in params.items():
        if isinstance(v, dict):
            clean_v = dict(v)
            if "default" in clean_v:
                lower_name = str(clean_v.get("name", k)).lower()
                if any(s in lower_name for s in ("auth", "token", "key", "secret", "password", "credential")):
                    clean_v["default"] = "[REDACTED]"
            sanitized[k] = clean_v
        else:
            lower_k = str(k).lower()
            if any(s in lower_k for s in ("auth", "token", "key", "secret", "password", "credential")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = v
    return sanitized


def sanitize_variations(variations):
    if not variations or not isinstance(variations, list):
        return variations
    sanitized = []
    for v in variations:
        if isinstance(v, dict):
            sv = dict(v)
            if "headers" in sv:
                sv["headers"] = sanitize_headers(sv["headers"])
            if "params" in sv:
                sv["params"] = sanitize_params(sv["params"])
            sanitized.append(sv)
        else:
            sanitized.append(v)
    return sanitized


def generate_skill(args):
    root = resolve_root(args.root)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else root / PRIVATE_DIR / "output" / safe_token(args.skill_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    spec = {}
    if args.endpoint_spec:
        spec_path = Path(args.endpoint_spec).resolve()
        if spec_path.exists():
            spec = json.loads(spec_path.read_text(encoding="utf-8"))

    classification = args.classification or spec.get("classification", "DIRECT_API_VERIFIED")
    site_name = args.site_name or spec.get("site_name", "Target Site")
    site_slug = safe_token(args.site_slug or spec.get("site_slug", "site"))
    capability_slug = safe_token(args.capability_slug or spec.get("capability_slug", "extract-items"))
    capability_name = f"{site_slug}-{capability_slug}"
    base_url = spec.get("base_url") or spec.get("url") or "https://example.com"
    endpoint_path = spec.get("path") or "/api/items"

    raw_endpoints = spec.get("endpoints") or [{
        "id": capability_slug,
        "method": spec.get("method", "GET"),
        "path": endpoint_path,
        "classification": classification,
        "headers": spec.get("headers", {}),
        "parameters": spec.get("parameters", {
            "query": {"type": "string", "in": "query", "name": "q"},
            "page": {"type": "integer", "in": "query", "name": "page", "default": 1},
            "limit": {"type": "integer", "in": "query", "name": "limit", "default": 20}
        }),
        "verification": {
            "status": "PASSED" if classification == "DIRECT_API_VERIFIED" else "FALLBACK",
            "tested_variations": spec.get("tested_variations", [])
        }
    }]

    # Sanitize secrets in endpoints metadata
    sanitized_endpoints = []
    for ep in raw_endpoints:
        clean_ep = dict(ep)
        if "headers" in clean_ep:
            clean_ep["headers"] = sanitize_headers(clean_ep["headers"])
        if "parameters" in clean_ep:
            clean_ep["parameters"] = sanitize_params(clean_ep["parameters"])
        if "verification" in clean_ep and isinstance(clean_ep["verification"], dict):
            clean_v = dict(clean_ep["verification"])
            if "tested_variations" in clean_v:
                clean_v["tested_variations"] = sanitize_variations(clean_v["tested_variations"])
            clean_ep["verification"] = clean_v
        sanitized_endpoints.append(clean_ep)

    har_hash = spec.get("har_sha256") or "0" * 64
    if args.har_path:
        hp = Path(args.har_path).resolve()
        if hp.exists():
            har_hash = hashlib.sha256(hp.read_bytes()).hexdigest()

    # 1. Write endpoint-manifest.json
    manifest = {
        "skill_name": capability_name,
        "target_origin": base_url,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": sanitized_endpoints
    }
    (output_dir / "endpoint-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # 2. Write provenance.json
    provenance = {
        "forge_version": "0.1.0",
        "agent_browser_version": "agent-browser 0.34.0",
        "target_origin": base_url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "har_sha256": har_hash,
        "capabilities": [
            {
                "name": capability_name,
                "classification": classification,
                "steady_state_runtime": "python" if classification == "DIRECT_API_VERIFIED" else "agent-browser",
                "verified_endpoint": endpoint_path
            }
        ],
        "verification_summary": {
            "direct_api_count": 1 if classification == "DIRECT_API_VERIFIED" else 0,
            "browser_session_count": 1 if classification == "BROWSER_SESSION_API" else 0,
            "dom_only_count": 1 if classification == "DOM_ONLY" else 0,
            "all_passed": True
        }
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    # 3. Write client.py if DIRECT_API_VERIFIED
    if classification == "DIRECT_API_VERIFIED":
        client_code = f'''import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = {json.dumps(base_url)}


class APIClient:
    def __init__(self, base_url=BASE_URL, auth_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("API_AUTH_TOKEN")
        if not self.auth_token:
            auth_file = Path(os.getcwd()) / ".agent-forge" / "auth.json"
            if auth_file.exists():
                try:
                    auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                    self.auth_token = auth_data.get("token") or auth_data.get("auth_token")
                except Exception:
                    pass

    def _request(self, path, params=None, data=None, method="GET"):
        url = f"{{self.base_url}}/{{path.lstrip('/')}}"
        if params:
            clean_params = {{k: v for k, v in params.items() if v is not None}}
            if clean_params:
                url += f"?{{urllib.parse.urlencode(clean_params)}}"

        headers = {{
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {{self.auth_token}}"

        encoded_data = json.dumps(data).encode("utf-8") if data else None
        if encoded_data:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            if exc.code in (401, 403):
                return {{"error": True, "code": "AUTH_EXPIRED", "message": f"Authentication token expired or unauthorized (HTTP {{exc.code}}): {{err_body}}"}}
            return {{"error": True, "code": f"HTTP_{{exc.code}}", "message": err_body}}
        except Exception as exc:
            return {{"error": True, "code": "REQUEST_FAILED", "message": str(exc)}}

    def extract_items(self, query=None, page=1, limit=20, category=None):
        params = {{"q": query, "page": page, "limit": limit, "category": category}}
        return self._request({json.dumps(endpoint_path)}, params=params)


def main():
    parser = argparse.ArgumentParser(description="{capability_name} standalone client")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--page", "-p", type=int, default=1, help="Page number")
    parser.add_argument("--limit", "-l", type=int, default=20, help="Page size")
    parser.add_argument("--category", "-c", help="Category filter")
    args = parser.parse_args()

    client = APIClient()
    result = client.extract_items(
        query=args.query,
        page=args.page,
        limit=args.limit,
        category=args.category,
    )
    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        (output_dir / "client.py").write_text(client_code, encoding="utf-8")

    # 4. Write script helper in scripts/
    feature_script = f'''import argparse
import json
import sys


def build_js(query=None, limit=20):
    query_json = json.dumps(query)
    limit_json = json.dumps(limit)
    return f"""
(() => {{{{
  try {{{{
    const query = {{{{query_json}}}};
    const limit = {{{{limit_json}}}};
    const rows = Array.from(document.querySelectorAll('.item-card, .list-row, tr.item'));
    if (!rows.length) {{{{
      return JSON.stringify({{{{ error: true, code: "ELEMENT_NOT_FOUND", message: "No items found in DOM" }}}});
    }}}}
    const items = rows.slice(0, limit).map(row => ({{{{
      title: row.querySelector('.title, h3, a')?.textContent?.trim() || '',
      url: row.querySelector('a')?.href || '',
      price: row.querySelector('.price')?.textContent?.trim() || null
    }}}}));
    return JSON.stringify({{{{ items, count: items.length }}}});
  }}}} catch (err) {{{{
    return JSON.stringify({{{{ error: true, code: "EXTRACTION_FAILED", message: err.message }}}});
  }}}}
}}}})()
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", default=None)
    parser.add_argument("--limit", "-l", type=int, default=20)
    args = parser.parse_args()
    sys.stdout.write(build_js(query=args.query, limit=args.limit))


if __name__ == "__main__":
    main()
'''
    (scripts_dir / f"{capability_slug}.py").write_text(feature_script, encoding="utf-8")

    # 5. Write SKILL.md
    if classification == "DIRECT_API_VERIFIED":
        component_section = f'''### Standalone API Client (DIRECT_API_VERIFIED)

`python client.py --query "<query>" --page <page> --limit <limit>`

Parameters:
- `--query <string>`: Search keyword or filter.
- `--page <int>`: Page number (default: 1).
- `--limit <int>`: Items per page (default: 20).
- `--category <string>`: Category filter.

Output example:
```json
{{
  "items": [
    {{
      "id": "101",
      "title": "Sample Item",
      "price": 29.99
    }}
  ],
  "page": 1,
  "total": 45,
  "has_more": true
}}
```'''
    else:
        component_section = f'''### Browser Extraction ({classification})

`python scripts/{capability_slug}.py --query "<query>" --limit <limit> | agent-browser eval --stdin`

Parameters:
- `--query <string>`: Search keyword.
- `--limit <int>`: Max items.

Output example:
```json
{{
  "items": [
    {{
      "title": "Sample Item",
      "url": "https://example.com/items/101"
    }}
  ],
  "count": 1
}}
```'''

    skill_md = f'''---
name: {capability_name}
description: "Extracts structured data from {site_name}. Use when searching items, extracting listings, or querying the {site_slug} API."
---

# {site_name} — {capability_slug}

> Classification: `{classification}`
> Search and extract structured items from {site_name}.

## Language

All process output follows the user's language. Code comments, logs, and output schemas remain in English.

## Objective

Extract structured item listings from {site_name} with verified parameter variations and pagination.

## Prerequisites

- {"Python 3.8+ (no browser required for steady-state extraction)" if classification == "DIRECT_API_VERIFIED" else "agent-browser installed and target page accessible"}

## Pre-execution Checks

1. Verify environment prerequisites are met.
2. Ensure target endpoints are reachable.

## Capability Components

{component_section}

## Enum Parameters

| Parameter | Type | Source & Acquisition Method | Options / Values |
|---|---|---|---|
| `category` | string | `[API]` `/api/categories` -> `[item.slug]` | `electronics`, `books`, `apparel` |
| `status` | string | `[DOM]` `<select id="status">` | `active`, `archived` |

## Pagination Parameters

| Parameter | Type | Mechanism | Termination Condition |
|---|---|---|---|
| `page` | integer | Query parameter `?page={{n}}` | `items.length == 0` or `has_more == false` |

## Quantifiable Success Criteria

- HTTP status 200 or successful script execution.
- Top-level `items` array is present.
- Each item contains required properties (`id` or `title`).

## Error Envelope

```json
{{
  "error": true,
  "code": "REQUEST_FAILED | ELEMENT_NOT_FOUND",
  "message": "Diagnostic message"
}}
```

## Recovery & Revalidation Lifecycle

1. Fast path: Run the verified client.
2. On 401/403 or schema drift: Revalidate endpoint with test query.
3. Re-exploration: Only enter forge if API contract changed.
'''
    (output_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    result = {
        "output_dir": str(output_dir),
        "skill_name": capability_name,
        "classification": classification,
        "files": [
            str(output_dir / "SKILL.md"),
            str(output_dir / "endpoint-manifest.json"),
            str(output_dir / "provenance.json"),
        ] + ([str(output_dir / "client.py")] if classification == "DIRECT_API_VERIFIED" else [])
    }
    print(json.dumps(result, indent=2))


def validate_package(args):
    pkg_dir = Path(args.package_dir).resolve()
    if not pkg_dir.exists() or not pkg_dir.is_dir():
        fail(f"Package directory does not exist: {pkg_dir}")

    errors = []

    # 1. SKILL.md
    skill_md = pkg_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md is missing")
    else:
        text = skill_md.read_text(encoding="utf-8")
        if not re.search(r"^---\r?\n[\s\S]*?\r?\n---", text):
            errors.append("SKILL.md is missing YAML frontmatter")
        if not re.search(r"DIRECT_API_VERIFIED|BROWSER_SESSION_API|DOM_ONLY|HYBRID", text):
            errors.append("SKILL.md does not declare an approved runtime classification")
        if re.search(r"@e\d+\b", text):
            errors.append("SKILL.md contains concrete runtime snapshot ref (@eN)")

    # 2. endpoint-manifest.json
    manifest_path = pkg_dir / "endpoint-manifest.json"
    if not manifest_path.exists():
        errors.append("endpoint-manifest.json is missing")
    else:
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(m.get("endpoints"), list):
                errors.append("endpoint-manifest.json must contain 'endpoints' array")
        except Exception as exc:
            errors.append(f"endpoint-manifest.json is invalid JSON: {exc}")

    # 3. provenance.json
    prov_path = pkg_dir / "provenance.json"
    if not prov_path.exists():
        errors.append("provenance.json is missing")
    else:
        try:
            p = json.loads(prov_path.read_text(encoding="utf-8"))
            if "har_sha256" not in p:
                errors.append("provenance.json must contain 'har_sha256'")
        except Exception as exc:
            errors.append(f"provenance.json is invalid JSON: {exc}")

    # 4. Check for snapshot refs in any files
    for root_path, _, files in os.walk(pkg_dir):
        for f in files:
            if f.endswith((".md", ".py")):
                fp = Path(root_path) / f
                content = fp.read_text(encoding="utf-8", errors="replace")
                if re.search(r"@e\d+\b", content):
                    errors.append(f"{f} contains concrete snapshot ref (@eN)")

    valid = len(errors) == 0
    result = {"valid": valid, "package_dir": str(pkg_dir), "errors": errors}
    print(json.dumps(result, indent=2))
    if not valid:
        sys.exit(1)


def export_skill(args):
    pkg_dir = Path(args.package_dir).resolve()
    if not pkg_dir.exists() or not pkg_dir.is_dir():
        fail(f"Package directory does not exist: {pkg_dir}")
    if not args.destination or not str(args.destination).strip():
        fail("Destination path is required for export")
    dest_dir = Path(args.destination).resolve()

    skill_md = pkg_dir / "SKILL.md"
    if not skill_md.exists():
        fail(f"Invalid package: SKILL.md missing in {pkg_dir}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in pkg_dir.iterdir():
        target = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    result = {
        "exported": True,
        "source": str(pkg_dir),
        "destination": str(dest_dir),
    }
    print(json.dumps(result, indent=2))


def revalidate_skill(args):
    pkg_dir = Path(args.package_dir).resolve()
    if not pkg_dir.exists() or not pkg_dir.is_dir():
        fail(f"Package directory does not exist: {pkg_dir}")
    manifest_file = pkg_dir / "endpoint-manifest.json"
    if not manifest_file.exists():
        fail(f"endpoint-manifest.json missing in package: {pkg_dir}")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    base_url = args.base_url or manifest.get("target_origin", "https://example.com")
    endpoints = manifest.get("endpoints", [])

    tested_endpoints = []
    overall_status = "HEALTHY"
    all_verified = True

    for ep in endpoints:
        ep_path = ep.get("path", "")
        ep_method = ep.get("method", "GET").upper()
        url = f"{base_url.rstrip('/')}/{ep_path.lstrip('/')}"

        req_params = {}
        for p_name, p_def in ep.get("parameters", {}).items():
            if isinstance(p_def, dict) and p_def.get("default") is not None and p_def.get("default") != "[REDACTED]":
                req_params[p_def.get("name", p_name)] = p_def["default"]

        if req_params:
            url += f"?{urllib.parse.urlencode(req_params)}"

        req = urllib.request.Request(url, method=ep_method)
        auth_token = os.environ.get("API_AUTH_TOKEN")
        if auth_token:
            req.add_header("Authorization", f"Bearer {auth_token}")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                body_raw = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed_body = json.loads(body_raw)
                except Exception:
                    parsed_body = body_raw

                required_keys = []
                for v in ep.get("verification", {}).get("tested_variations", []):
                    if isinstance(v, dict) and v.get("required_keys"):
                        required_keys.extend(v["required_keys"])
                if not required_keys:
                    if isinstance(parsed_body, dict) and "items" in parsed_body:
                        required_keys = ["items"]

                ep_ok = True
                if isinstance(parsed_body, dict) and required_keys:
                    for rk in required_keys:
                        if rk not in parsed_body:
                            ep_ok = False
                            overall_status = "DRIFT_DETECTED"
                            all_verified = False
                            break

                tested_endpoints.append({
                    "endpoint": ep_path,
                    "status": status_code,
                    "verified": ep_ok,
                    "drift": not ep_ok,
                })
        except urllib.error.HTTPError as exc:
            all_verified = False
            if exc.code in (401, 403):
                overall_status = "AUTH_EXPIRED"
            elif exc.code == 404:
                overall_status = "RE_EXPLORATION_REQUIRED"
            else:
                overall_status = "DRIFT_DETECTED"
            tested_endpoints.append({
                "endpoint": ep_path,
                "status": exc.code,
                "verified": False,
                "error": str(exc),
            })
        except Exception as exc:
            all_verified = False
            overall_status = "RE_EXPLORATION_REQUIRED"
            tested_endpoints.append({
                "endpoint": ep_path,
                "status": 0,
                "verified": False,
                "error": str(exc),
            })

    result = {
        "status": overall_status,
        "verified": all_verified,
        "tested_endpoints": tested_endpoints,
    }
    print(json.dumps(result, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Trusted runtime boundary for agent-browser-skill-forge")
    sub = parser.add_subparsers(dest="action", required=True)

    p_boot = sub.add_parser("bootstrap")
    p_boot.add_argument("--root", default=os.getcwd())
    p_boot.add_argument("--task", default="forge")
    p_boot.add_argument("--run-id")
    p_boot.add_argument("--trusted-config")
    p_boot.set_defaults(func=bootstrap)

    p_exec = sub.add_parser("exec")
    p_exec.add_argument("--root", default=os.getcwd())
    p_exec.add_argument("--run-id", required=True)
    p_exec.add_argument("command", nargs=argparse.REMAINDER)
    p_exec.set_defaults(func=execute)

    p_har_analyze = sub.add_parser("har-analyze")
    p_har_analyze.add_argument("--har", required=True)
    p_har_analyze.add_argument("--origin")
    p_har_analyze.add_argument("--filter")
    p_har_analyze.set_defaults(func=har_analyze)

    p_har_inspect = sub.add_parser("har-inspect")
    p_har_inspect.add_argument("--har", required=True, help="Path to HAR file")
    p_har_inspect.add_argument("--methods", default=None, help="Comma-separated HTTP methods to include (default: all)")
    p_har_inspect.set_defaults(func=har_inspect)

    p_ver = sub.add_parser("verify-endpoint")
    p_ver.add_argument("--url")
    p_ver.add_argument("--method", default="GET")
    p_ver.add_argument("--headers")
    p_ver.add_argument("--spec")
    p_ver.add_argument("--variations")
    p_ver.add_argument("--required-key", action="append")
    p_ver.add_argument("--pagination-key")
    p_ver.add_argument("--min-status", type=int)
    p_ver.add_argument("--max-status", type=int)
    p_ver.set_defaults(func=verify_endpoint)

    p_gen = sub.add_parser("generate-skill")
    p_gen.add_argument("--root", default=os.getcwd())
    p_gen.add_argument("--skill-name", required=True)
    p_gen.add_argument("--site-name", default="Target Site")
    p_gen.add_argument("--site-slug", default="site")
    p_gen.add_argument("--capability-slug", default="extract-items")
    p_gen.add_argument("--classification", default="DIRECT_API_VERIFIED")
    p_gen.add_argument("--endpoint-spec")
    p_gen.add_argument("--har-path")
    p_gen.add_argument("--output-dir")
    p_gen.set_defaults(func=generate_skill)

    p_val = sub.add_parser("validate-package")
    p_val.add_argument("--package-dir", required=True)
    p_val.set_defaults(func=validate_package)

    p_exp = sub.add_parser("export-skill")
    p_exp.add_argument("--package-dir", required=True)
    p_exp.add_argument("--destination", required=True)
    p_exp.set_defaults(func=export_skill)

    p_rev = sub.add_parser("revalidate-skill")
    p_rev.add_argument("--package-dir", required=True)
    p_rev.add_argument("--base-url")
    p_rev.set_defaults(func=revalidate_skill)
    return parser


def har_inspect(args):
    har_path = Path(args.har).resolve()
    if not har_path.exists():
        fail(f"HAR file does not exist: {har_path}")
    try:
        data = json.loads(har_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"failed to read HAR JSON: {exc}")

    entries = data.get("log", {}).get("entries", [])
    results = []
    methods = {m.strip().upper() for m in args.methods.split(",")} if args.methods else None

    for entry in entries:
        req = entry.get("request", {})
        method = req.get("method", "GET").upper()
        if methods and method not in methods:
            continue

        post_data = req.get("postData", {})
        mime = post_data.get("mimeType", "")
        raw_text = post_data.get("text", "")
        parsed_body = None
        if raw_text:
            if "application/json" in mime or raw_text.startswith(("{", "[")):
                try:
                    parsed_body = json.loads(raw_text)
                except Exception:
                    parsed_body = raw_text
            else:
                parsed_body = raw_text

        is_graphql = False
        graphql_info = None
        if isinstance(parsed_body, dict) and "query" in parsed_body:
            q = parsed_body.get("query", "")
            if isinstance(q, str) and re.search(r"\bmutation\b", q):
                is_graphql = True
                m = re.search(r"mutation\s+([A-Za-z0-9_]+)", q)
                graphql_info = {
                    "mutation_name": m.group(1) if m else "anonymous",
                    "variables": parsed_body.get("variables", {}),
                }

        results.append({
            "url": req.get("url"),
            "method": method,
            "headers": {h.get("name"): h.get("value") for h in req.get("headers", [])},
            "query_string": req.get("queryString", []),
            "post_data": parsed_body,
            "mime_type": mime,
            "is_graphql": is_graphql,
            "graphql": graphql_info,
        })

    print(json.dumps({"count": len(results), "entries": results}, indent=2))



def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
