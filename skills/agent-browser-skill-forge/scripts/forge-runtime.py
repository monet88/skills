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


EXCLUDED_METADATA_KEYS = {
    "required_keys", "required_key", "pagination_key",
    "key_count", "sort_key", "partition_key", "primary_key"
}

SENSITIVE_KEY_SUBSTRINGS = (
    "auth", "token", "cookie", "secret", "password",
    "credential", "session", "jwt", "api_key", "access_token",
    "csrf", "bearer", "authorization"
)


def is_sensitive_key(key):
    if not isinstance(key, str):
        return False
    lower_k = key.lower().strip()
    if lower_k in EXCLUDED_METADATA_KEYS:
        return False
    if any(s in lower_k for s in SENSITIVE_KEY_SUBSTRINGS):
        return True
    if lower_k == "key" or lower_k.endswith("_key") or lower_k.endswith("key"):
        return True
    return False


def sanitize_url(url_str):
    if not isinstance(url_str, str):
        return url_str
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme and (parsed.netloc or parsed.path):
            netloc = parsed.netloc
            if "@" in netloc:
                userinfo, host = netloc.rsplit("@", 1)
                if ":" in userinfo:
                    netloc = f"[REDACTED]:[REDACTED]@{host}"
                else:
                    netloc = f"[REDACTED]@{host}"

            qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            new_qs = []
            for qk, qv in qs:
                if is_sensitive_key(qk):
                    new_qs.append((qk, "[REDACTED]"))
                else:
                    new_qs.append((qk, qv))
            new_query = urllib.parse.urlencode(new_qs)
            return urllib.parse.urlunparse((
                parsed.scheme, netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
    except Exception:
        pass
    return url_str


def sanitize_text(text):
    if not isinstance(text, str):
        return text
    trimmed = text.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
        try:
            parsed_json = json.loads(trimmed)
            sanitized_json = sanitize_deep(parsed_json)
            return json.dumps(sanitized_json)
        except Exception:
            pass

    url_pattern = re.compile(r'https?://[^\s"\'<>]+')
    def replace_url(match):
        return sanitize_url(match.group(0))
    text = url_pattern.sub(replace_url, text)
    text = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9_\-\.\+\/=]+', 'Bearer [REDACTED]', text)
    for k in SENSITIVE_KEY_SUBSTRINGS:
        text = re.sub(rf'(?i)([\?&;,\s]|^)({k}[a-z0-9_]*)=([^\s&,;"]+)', r'\1\2=[REDACTED]', text)
    return text


def redact_all_leaves(inner):
    if isinstance(inner, dict):
        return {ik: redact_all_leaves(iv) for ik, iv in inner.items()}
    elif isinstance(inner, list):
        return [redact_all_leaves(ix) for ix in inner]
    elif isinstance(inner, str):
        if inner.lower().startswith("bearer "):
            return "Bearer [REDACTED]"
        return "[REDACTED]"
    return "[REDACTED]"


def sanitize_deep(obj):
    if obj is None:
        return None
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [sanitize_deep(item) for item in obj]
    if isinstance(obj, dict):
        sanitized = {}
        is_name_val_sensitive = False
        if "name" in obj and isinstance(obj["name"], str) and is_sensitive_key(obj["name"]):
            is_name_val_sensitive = True

        for k, v in obj.items():
            if is_name_val_sensitive and k == "value":
                sanitized[k] = "[REDACTED]"
            elif is_sensitive_key(k):
                if isinstance(v, str):
                    if v.lower().startswith("bearer "):
                        sanitized[k] = "Bearer [REDACTED]"
                    else:
                        sanitized[k] = "[REDACTED]"
                elif isinstance(v, dict):
                    if "type" in v and ("in" in v or "name" in v):
                        clean_dict = dict(v)
                        if "default" in clean_dict:
                            clean_dict["default"] = "[REDACTED]"
                        sanitized[k] = clean_dict
                    else:
                        sanitized[k] = redact_all_leaves(v)
                elif isinstance(v, list):
                    sanitized[k] = redact_all_leaves(v)
                else:
                    sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_deep(v)
        return sanitized
    return obj


def get_live_agent_browser_version(root=None):
    if root:
        runs_dir = Path(root) / PRIVATE_DIR / "runs"
        if runs_dir.exists():
            for rdir in sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                rt_file = rdir / "runtime.json"
                if rt_file.exists():
                    try:
                        rt_data = json.loads(rt_file.read_text(encoding="utf-8"))
                        if rt_data.get("agent_browser_version") or rt_data.get("version"):
                            return rt_data.get("agent_browser_version") or rt_data.get("version")
                    except Exception:
                        pass
    try:
        proc = subprocess.run(["agent-browser", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "agent-browser (version unavailable)"


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
    print(json.dumps(sanitize_deep(result), indent=2))


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
    print(json.dumps(sanitize_deep(output), indent=2))


def generate_skill(args):
    root = resolve_root(args.root)
    allowed_output_base = (root / PRIVATE_DIR / "output").resolve()
    if args.output_dir:
        requested_dir = Path(args.output_dir).resolve()
        try:
            requested_dir.relative_to(allowed_output_base)
            output_dir = requested_dir
        except ValueError:
            fail(f"Generated output must stay under {allowed_output_base}; writing elsewhere is only via explicit export-skill")
    else:
        skill_slug = safe_token(args.skill_name)
        output_dir = allowed_output_base / skill_slug

    output_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    spec = {}
    if args.endpoint_spec:
        spec_path = Path(args.endpoint_spec).resolve()
        if spec_path.exists():
            spec = json.loads(spec_path.read_text(encoding="utf-8"))

    classification = args.classification or spec.get("classification", "DIRECT_API_VERIFIED")
    site_name = args.site_name or spec.get("site_name") or "Target Site"
    site_slug = safe_token(args.site_slug or spec.get("site_slug") or "site")
    capability_slug = safe_token(args.capability_slug or spec.get("capability_slug") or "extract-items")
    capability_name = safe_token(args.skill_name) if args.skill_name else f"{site_slug}-{capability_slug}"
    base_url = spec.get("base_url") or spec.get("url") or "https://example.com"
    endpoint_path = spec.get("path") or "/api/items"

    raw_endpoints = spec.get("endpoints")
    spec_has_explicit_endpoints = bool(raw_endpoints)  # True when spec provides explicit endpoint IDs
    if not raw_endpoints:
        tested_vars = spec.get("verification", {}).get("tested_variations") or spec.get("tested_variations") or []
        has_evidence = len(tested_vars) >= 1 and any(v.get("status") in (200, 201, 204, "200", "201", "204") for v in tested_vars if isinstance(v, dict))
        if not has_evidence and classification == "DIRECT_API_VERIFIED":
            status = "UNVERIFIED"
        else:
            status = "PASSED" if (classification == "DIRECT_API_VERIFIED" and has_evidence) else "FALLBACK"

        raw_endpoints = [{
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
                "status": status,
                "tested_variations": tested_vars
            }
        }]
    else:
        for ep in raw_endpoints:
            ep_class = ep.get("classification", classification)
            ep_vars = ep.get("verification", {}).get("tested_variations") or ep.get("tested_variations") or spec.get("tested_variations") or []
            has_ev = len(ep_vars) >= 1 and any(v.get("status") in (200, 201, 204, "200", "201", "204") for v in ep_vars if isinstance(v, dict))
            if "verification" not in ep or not isinstance(ep.get("verification"), dict):
                ep["verification"] = {}
            if "tested_variations" not in ep["verification"]:
                ep["verification"]["tested_variations"] = ep_vars
            if "status" not in ep["verification"]:
                st = "PASSED" if (ep_class == "DIRECT_API_VERIFIED" and has_ev) else ("UNVERIFIED" if ep_class == "DIRECT_API_VERIFIED" else "FALLBACK")
                ep["verification"]["status"] = st
            elif ep_class == "DIRECT_API_VERIFIED" and ep["verification"].get("status") == "PASSED" and not has_ev:
                ep["verification"]["status"] = "UNVERIFIED"

    sanitized_endpoints = sanitize_deep(raw_endpoints)

    har_hash = spec.get("har_sha256")
    if args.har_path:
        hp = Path(args.har_path).resolve()
        if hp.exists():
            har_hash = hashlib.sha256(hp.read_bytes()).hexdigest()

    # 1. Write endpoint-manifest.json
    manifest = {
        "skill_name": capability_name,
        "target_origin": sanitize_url(base_url),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": sanitized_endpoints
    }
    (output_dir / "endpoint-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # 2. Write provenance.json
    direct_count = sum(1 for ep in sanitized_endpoints if ep.get("classification") == "DIRECT_API_VERIFIED" and ep.get("verification", {}).get("status") == "PASSED")
    browser_count = sum(1 for ep in sanitized_endpoints if ep.get("classification") == "BROWSER_SESSION_API")
    dom_count = sum(1 for ep in sanitized_endpoints if ep.get("classification") == "DOM_ONLY")
    has_multiple_types = len({ep.get("classification") for ep in sanitized_endpoints}) > 1
    hybrid_count = 1 if (classification == "HYBRID" or has_multiple_types) else sum(1 for ep in sanitized_endpoints if ep.get("classification") == "HYBRID")
    all_passed = bool(sanitized_endpoints) and all(
        ep.get("verification", {}).get("status") == "PASSED" for ep in sanitized_endpoints
    )

    # Exploration time: accept from spec evidence if present, otherwise null.
    exploration_time_s = spec.get("exploration_time_s")

    prov_capabilities = []
    for ep in sanitized_endpoints:
        ep_c = ep.get("classification", classification)
        ep_id = ep.get("id")
        if len(sanitized_endpoints) == 1:
            cap_name = capability_name
        elif ep_id:
            cap_name = ep.get("name") or ep_id
        else:
            cap_name = capability_name

        prov_capabilities.append({
            "name": cap_name,
            "method": ep.get("method", "GET"),
            "classification": ep_c,
            "steady_state_runtime": "python" if ep_c == "DIRECT_API_VERIFIED" else "agent-browser",
            "verified_endpoint": sanitize_deep(ep.get("path", endpoint_path))
        })

    provenance = {
        "forge_version": "0.1.0",
        "agent_browser_version": get_live_agent_browser_version(root),
        "target_origin": sanitize_url(base_url),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "exploration_time_s": exploration_time_s,
        "har_sha256": har_hash,
        "capabilities": prov_capabilities,
        "verification_summary": {
            "direct_api_count": direct_count,
            "browser_session_count": browser_count,
            "dom_only_count": dom_count,
            "hybrid_count": hybrid_count,
            "all_passed": all_passed
        }
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    # 3. Models generation (models.py) when schema is present
    models_spec = spec.get("models") or {}
    if models_spec:
        models_lines = [
            "from dataclasses import dataclass, field",
            "from typing import Optional, List, Dict, Any",
            "",
        ]
        for model_name, fields in models_spec.items():
            models_lines.append("@dataclass")
            models_lines.append(f"class {model_name}:")
            if isinstance(fields, dict) and fields:
                for fname, ftype in fields.items():
                    py_type = "str"
                    if ftype in ("int", "integer"):
                        py_type = "int"
                    elif ftype in ("float", "number"):
                        py_type = "float"
                    elif ftype in ("bool", "boolean"):
                        py_type = "bool"
                    elif ftype in ("list", "array"):
                        py_type = "List[Any]"
                    elif ftype in ("dict", "object"):
                        py_type = "Dict[str, Any]"
                    models_lines.append(f"    {fname}: {py_type} = None")
            else:
                models_lines.append("    pass")
            models_lines.append("")
        (output_dir / "models.py").write_text("\n".join(models_lines) + "\n", encoding="utf-8")

    # 4. Write client.py if direct endpoints are present
    has_direct_endpoints = any(ep.get("classification") == "DIRECT_API_VERIFIED" for ep in sanitized_endpoints) or classification == "DIRECT_API_VERIFIED"
    if has_direct_endpoints:
        endpoint_methods = []
        direct_eps = [ep for ep in sanitized_endpoints if ep.get("classification") == "DIRECT_API_VERIFIED"]
        if not direct_eps:
            direct_eps = sanitized_endpoints

        for ep in direct_eps:
            ep_id = safe_token(ep.get("id", "request")).replace("-", "_")
            ep_method = ep.get("method", "GET").upper()
            ep_path = ep.get("path", "/api/items")

            # Build param signature from spec parameters for this endpoint
            ep_params = ep.get("parameters") or {}
            query_params = {pn: pd for pn, pd in ep_params.items() if isinstance(pd, dict) and pd.get("in") == "query"}

            if ep_method in ("POST", "PUT", "PATCH"):
                endpoint_methods.append(f'''    def {ep_id}(self, data=None, **kwargs):
        path = {json.dumps(ep_path)}
        for k, v in list(kwargs.items()):
            target = "{{" + k + "}}"
            if target in path:
                path = path.replace(target, str(v))
                kwargs.pop(k)
        params = kwargs.get("params")
        body_data = data if data is not None else (kwargs if kwargs else None)
        return self._request(path, params=params, data=body_data, method={json.dumps(ep_method)})''')
            elif ep_method == "DELETE":
                endpoint_methods.append(f'''    def {ep_id}(self, **kwargs):
        path = {json.dumps(ep_path)}
        for k, v in list(kwargs.items()):
            target = "{{" + k + "}}"
            if target in path:
                path = path.replace(target, str(v))
                kwargs.pop(k)
        params = kwargs.get("params") or {{k: v for k, v in kwargs.items() if v is not None}}
        return self._request(path, params=params, method="DELETE")''')
            else:
                # Build named query parameters from spec so signature matches actual API
                named_args = []
                params_build_lines = []
                for pn, pd in query_params.items():
                    arg_name = pn.replace("-", "_")
                    named_args.append(f"{arg_name}=None")
                    qname = pd.get("name", pn) if isinstance(pd, dict) else pn
                    params_build_lines.append(f"        if {arg_name} is not None: params[{json.dumps(qname)}] = {arg_name}")
                named_args_str = (", ".join(named_args) + ", " if named_args else "")
                params_init = "        params = {}"
                params_kwargs = "\n        for k, v in kwargs.items():\n            if v is not None: params[k] = v"
                endpoint_methods.append(f'''    def {ep_id}(self, {named_args_str}**kwargs):
        path = {json.dumps(ep_path)}
        for k, v in list(kwargs.items()):
            target = "{{" + k + "}}"
            if target in path:
                path = path.replace(target, str(v))
                kwargs.pop(k)
{params_init}
{chr(10).join(params_build_lines)}{params_kwargs}
        return self._request(path, params=params, method="GET")''')

        # Backward-compat alias: inject extract_items only for flat-spec (no explicit endpoints in spec).
        # When spec provides an explicit endpoints array, the generated methods ARE the spec operations.
        if not spec_has_explicit_endpoints and not any(safe_token(ep.get("id", "")).replace("-", "_") == "extract_items" for ep in direct_eps):
            first_ep_path = direct_eps[0].get("path", endpoint_path) if direct_eps else endpoint_path
            endpoint_methods.append(f'''    def extract_items(self, query=None, page=1, limit=20, category=None, **kwargs):
        """Backward-compatible extraction alias. Delegates to the primary endpoint."""
        params = {{"q": query, "page": page, "limit": limit, "category": category}}
        for k, v in kwargs.items():
            if v is not None: params[k] = v
        return self._request({json.dumps(first_ep_path)}, params=params, method="GET")''')

        methods_joined = "\n\n".join(endpoint_methods)

        # Determine primary CLI operation from first direct endpoint in spec (spec-driven, not hardcoded)
        primary_ep = direct_eps[0] if direct_eps else None
        primary_ep_id = safe_token(primary_ep.get("id", "request")).replace("-", "_") if primary_ep else "request"
        primary_ep_method = (primary_ep.get("method", "GET").upper()) if primary_ep else "GET"
        primary_ep_params = (primary_ep.get("parameters") or {}) if primary_ep else {}
        primary_query_params = {pn: pd for pn, pd in primary_ep_params.items() if isinstance(pd, dict) and pd.get("in") == "query"}

        # Build CLI args and call for primary endpoint (spec-driven)
        if primary_ep_method in ("POST", "PUT", "PATCH"):
            cli_args_code = '    parser.add_argument("--data", "-d", help="JSON body data")'
            cli_call_code = f'    body = json.loads(args.data) if args.data else {{}}\n    result = client.{primary_ep_id}(data=body)'
        elif primary_ep_method == "DELETE":
            cli_args_code = '    parser.add_argument("--id", help="Resource ID for path substitution")'
            cli_call_code = f'    result = client.{primary_ep_id}(id=args.id)'
        else:
            cli_arg_lines = []
            cli_call_args = []
            for pn, pd in primary_query_params.items():
                arg_name = pn.replace("-", "_")
                ptype = pd.get("type", "string") if isinstance(pd, dict) else "string"
                if ptype in ("integer", "int"):
                    cli_arg_lines.append(f'    parser.add_argument("--{arg_name}", type=int, help="{arg_name}")')
                else:
                    cli_arg_lines.append(f'    parser.add_argument("--{arg_name}", help="{arg_name}")')
                cli_call_args.append(f"{arg_name}=args.{arg_name}")
            if not cli_arg_lines:
                # No spec params -> generic fallback
                cli_arg_lines = [
                    '    parser.add_argument("--query", "-q", help="Search query")',
                    '    parser.add_argument("--page", "-p", type=int, default=1, help="Page number")',
                    '    parser.add_argument("--limit", "-l", type=int, default=20, help="Page size")',
                ]
                cli_call_args = ["query=args.query", "page=args.page", "limit=args.limit"]
            cli_args_code = "\n".join(cli_arg_lines)
            cli_call_code = f'    result = client.{primary_ep_id}({", ".join(cli_call_args)})'

        # Embed workspace root for scoped auth discovery (stops walk at generation root)
        workspace_root_embedded = json.dumps(str(root))

        client_code = f'''import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = {json.dumps(base_url)}
# Auth discovery is scoped to the originating private workspace.
# Walk upward only within this boundary; do not cross into unrelated ancestor workspaces.
_FORGE_WORKSPACE_ROOT = Path({workspace_root_embedded})


class APIClient:
    def __init__(self, base_url=BASE_URL, auth_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("API_AUTH_TOKEN")
        if not self.auth_token:
            self._discover_auth()

    def _discover_auth(self):
        """Walk upward from cwd toward _FORGE_WORKSPACE_ROOT looking for auth.json.
        Stops at _FORGE_WORKSPACE_ROOT so exported clients never discover unrelated ancestor auth."""
        cur = Path(os.getcwd()).resolve()
        try:
            # Check whether cwd is inside the forge workspace; if not, only check cwd.
            cur.relative_to(_FORGE_WORKSPACE_ROOT)
            walk_candidates = []
            p = cur
            while True:
                walk_candidates.append(p)
                if p == _FORGE_WORKSPACE_ROOT:
                    break
                parent = p.parent
                if parent == p:
                    break
                p = parent
        except ValueError:
            # cwd is outside the originating workspace; only check immediate cwd
            walk_candidates = [cur]

        for candidate in walk_candidates:
            auth_file = candidate / ".agent-forge" / "auth.json"
            if auth_file.exists():
                try:
                    auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                    token = auth_data.get("token") or auth_data.get("auth_token")
                    if token:
                        self.auth_token = token
                        return
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
            if exc.code in (401, 403):
                return {{"error": True, "code": "AUTH_EXPIRED", "message": f"Authentication token expired or unauthorized (HTTP {{exc.code}})"}}
            return {{"error": True, "code": f"HTTP_{{exc.code}}", "message": f"HTTP request failed with status {{exc.code}}"}}
        except Exception as exc:
            return {{"error": True, "code": "REQUEST_FAILED", "message": "HTTP request failed due to client connection error"}}

{methods_joined}


def main():
    parser = argparse.ArgumentParser(description="{capability_name} standalone client")
{cli_args_code}
    args = parser.parse_args()

    client = APIClient()
{cli_call_code}
    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        (output_dir / "client.py").write_text(client_code, encoding="utf-8")

    # 5. Write script helper in scripts/
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

    # 6. Write README.md — use actual primary endpoint operation from spec (not hardcoded extract_items)
    all_direct = [ep for ep in sanitized_endpoints if ep.get("classification") == "DIRECT_API_VERIFIED"]
    readme_primary = all_direct[0] if all_direct else (sanitized_endpoints[0] if sanitized_endpoints else {})
    readme_ep_id = safe_token(readme_primary.get("id", capability_slug)).replace("-", "_")
    readme_ep_method = readme_primary.get("method", "GET").upper()
    readme_ep_path = readme_primary.get("path", endpoint_path)
    readme_ep_params = readme_primary.get("parameters") or {}
    readme_query_params = {pn: pd for pn, pd in readme_ep_params.items() if isinstance(pd, dict) and pd.get("in") == "query"}

    if readme_ep_method in ("POST", "PUT", "PATCH"):
        readme_python_example = f'result = client.{readme_ep_id}(data={{"key": "value"}})'
        readme_cli_example = f'python client.py --data \'{{"key": "value"}}\''
    elif readme_ep_method == "DELETE":
        readme_python_example = f'result = client.{readme_ep_id}(id="123")'
        readme_cli_example = f'python client.py --id "123"'
    else:
        if readme_query_params:
            first_pn = next(iter(readme_query_params))
            first_arg = first_pn.replace("-", "_")
            readme_python_example = f'result = client.{readme_ep_id}({first_arg}="example")'
            readme_cli_example = f'python client.py --{first_arg} "keyword"'
        else:
            readme_python_example = f'result = client.{readme_ep_id}()'
            readme_cli_example = f'python client.py'

    readme_content = f'''# {site_name} — {capability_name}

> Classification: `{classification}`
> Reusable skill package for {site_name} generated by `agent-browser-skill-forge`.

## Overview
- **Target Origin**: `{base_url}`
- **Classification**: `{classification}`
- **Generated At**: {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

## Installation & Prerequisites
- Python 3.8+ (for direct API client operations)
- `agent-browser` (for browser-session or DOM-fallback interactions)

## Python API Client
Import the standalone `APIClient` in Python:

```python
from client import APIClient

client = APIClient(base_url="{base_url}")
# Execute verified endpoint: {readme_ep_method} {readme_ep_path}
{readme_python_example}
print(result)
```

## CLI Usage
Run the standalone client from terminal:

```bash
{readme_cli_example}
```

## Data Models
Data models are defined in `models.py` when schema is present.

## Revalidation
To revalidate this capability against drift or auth expiration:

```bash
python forge-runtime.py revalidate-skill --package-dir .
```
'''
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")

    # 7. Write SKILL.md
    if classification == "DIRECT_API_VERIFIED":
        component_section = f'''### Standalone API Client (DIRECT_API_VERIFIED)

`{readme_cli_example}`

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
            str(output_dir / "README.md"),
            str(output_dir / "endpoint-manifest.json"),
            str(output_dir / "provenance.json"),
        ] + ([str(output_dir / "client.py")] if has_direct_endpoints else [])
          + ([str(output_dir / "models.py")] if models_spec else [])
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
    EXCLUDED_EXPORT_NAMES = {"auth.json", ".env", "capture.har", "sample.har"}
    for item in pkg_dir.iterdir():
        if item.name in EXCLUDED_EXPORT_NAMES or item.name.endswith(".har") or item.name == ".agent-forge":
            continue
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
    SAFE_READ_METHODS = {"GET", "HEAD", "OPTIONS"}

    for ep in endpoints:
        ep_path = ep.get("path", "")
        ep_method = ep.get("method", "GET").upper()
        ep_class = ep.get("classification", "DIRECT_API_VERIFIED")

        # 1. Never replay consequential write methods (POST, PUT, DELETE, PATCH)
        if ep_method not in SAFE_READ_METHODS:
            all_verified = False
            if overall_status == "HEALTHY":
                overall_status = "SAFE_REVALIDATION_REQUIRED"
            tested_endpoints.append({
                "endpoint": sanitize_deep(ep_path),
                "method": ep_method,
                "classification": ep_class,
                "status": "SAFE_REVALIDATION_REQUIRED",
                "action": "mutation_manual_confirmation",
                "safe": False,
                "verified": False,
                "message": f"Consequential HTTP method '{ep_method}' not replayed automatically. Manual confirmation required."
            })
            continue

        # 2. Non-DIRECT_API_VERIFIED classifications: attempt live browser DOM probe
        if ep_class != "DIRECT_API_VERIFIED":
            probe_result = _attempt_browser_dom_probe(base_url, ep_path, ep_class)
            if probe_result["verified"]:
                tested_endpoints.append({
                    "endpoint": sanitize_deep(ep_path),
                    "method": ep_method,
                    "classification": ep_class,
                    "status": "BROWSER_DOM_VERIFIED",
                    "action": "browser_session_probe",
                    "safe": True,
                    "verified": True,
                    "message": probe_result.get("message", "Browser DOM probe succeeded."),
                })
            else:
                all_verified = False
                if overall_status in ("HEALTHY", "SAFE_REVALIDATION_REQUIRED"):
                    overall_status = "BROWSER_SESSION_REVALIDATION_REQUIRED"
                tested_endpoints.append({
                    "endpoint": sanitize_deep(ep_path),
                    "method": ep_method,
                    "classification": ep_class,
                    "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                    "action": "browser_session_probe",
                    "safe": True,
                    "verified": False,
                    "message": probe_result.get("message", f"Classification '{ep_class}' requires browser session probe."),
                })
            continue

        # 3. DIRECT_API_VERIFIED + SAFE READ METHOD -> Issue live safe HTTP request
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
                    "endpoint": sanitize_deep(ep_path),
                    "method": ep_method,
                    "classification": ep_class,
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
                "endpoint": sanitize_deep(ep_path),
                "method": ep_method,
                "classification": ep_class,
                "status": exc.code,
                "verified": False,
                "error": sanitize_text(str(exc)),
            })
        except Exception as exc:
            all_verified = False
            overall_status = "RE_EXPLORATION_REQUIRED"
            tested_endpoints.append({
                "endpoint": sanitize_deep(ep_path),
                "method": ep_method,
                "classification": ep_class,
                "status": 0,
                "verified": False,
                "error": sanitize_text(str(exc)),
            })

    result = {
        "status": overall_status,
        "verified": all_verified,
        "tested_endpoints": tested_endpoints,
    }
    print(json.dumps(sanitize_deep(result), indent=2))


def _attempt_browser_dom_probe(base_url, ep_path, ep_class):
    """Check browser DOM probe readiness for a non-API endpoint.
    Returns {"verified": bool, "message": str}.
    Does NOT launch agent-browser (batch file process trees hang on Windows);
    instead reports availability and the probe URL for the caller to act on."""
    binary = shutil.which("agent-browser.cmd" if os.name == "nt" else "agent-browser") or shutil.which("agent-browser")
    target_url = f"{base_url.rstrip('/')}/{ep_path.lstrip('/')}"
    if not binary:
        return {
            "verified": False,
            "message": (
                f"agent-browser not found on PATH; {ep_class} endpoint at {target_url} "
                "requires a live browser session. Install agent-browser and run: "
                f"agent-browser open '{target_url}' then eval DOM state to revalidate."
            )
        }
    # agent-browser is available — report probe readiness without launching a subprocess
    return {
        "verified": False,
        "message": (
            f"agent-browser found at {binary}. {ep_class} endpoint at {target_url} "
            "requires a live browser session for revalidation. "
            f"Run: agent-browser open '{target_url}' then inspect DOM to confirm endpoint health."
        )
    }



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
    p_gen.add_argument("--site-name", default=None)
    p_gen.add_argument("--site-slug", default=None)
    p_gen.add_argument("--capability-slug", default=None)
    p_gen.add_argument("--classification", default=None)
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

    print(json.dumps(sanitize_deep({"count": len(results), "entries": results}), indent=2))


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
