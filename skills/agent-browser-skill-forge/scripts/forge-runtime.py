import argparse
import base64
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
COORDINATOR_REGEXES = [
    r"\bchatgpt\b", r"\bclaude(?:-code)?\b", r"\bcodex\b", r"\bantigravity\b",
    r"\bagy\b", r"\bopencode\b", r"@agent\b", r"\bsubagent:",
    r"\bmanage_task\b", r"\bcall_mcp_tool\b"
]


def fail(message, code=2, error_code=None):
    payload = {"error": True, "message": message}
    if error_code:
        payload["code"] = error_code
    print(json.dumps(payload), file=sys.stderr)
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


def run_process(argv, cwd, *, check=True, timeout=None):
    # File-backed capture avoids Windows daemon children keeping PIPE handles open.
    with tempfile.TemporaryFile() as out_file, tempfile.TemporaryFile() as err_file:
        try:
            completed = subprocess.run(
                argv,
                cwd=str(cwd),
                env=clean_env(),
                stdout=out_file,
                stderr=err_file,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            out_file.seek(0)
            err_file.seek(0)
            out = out_file.read().decode("utf-8", errors="replace")
            err = err_file.read().decode("utf-8", errors="replace")
            if check:
                raise RuntimeError(f"Command timed out after {timeout}s: {argv}") from exc
            return subprocess.CompletedProcess(argv, returncode=124, stdout=out, stderr=err or f"Timeout after {timeout}s")
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
    if "chat" in argv:
        fail("interactive mode is blocked in forge-controlled runs: 'chat' is not allowed")
    for token in argv:
        flag = token.split("=", 1)[0]
        if flag in ("--confirm-interactive", "--confirm-actions"):
            fail(f"interactive mode is blocked in forge-controlled runs: '{flag}' is not allowed")
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
    "key_count", "sort_key", "partition_key", "primary_key",
    "auth_renewal", "token_mapping", "source_field", "target_header",
    "target_format", "body_template", "trigger_statuses"
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
                    if v.startswith("{") and v.endswith("}"):
                        sanitized[k] = v
                    elif v.lower().startswith("bearer "):
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

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_receipt_hash(receipt_dict):
    if not isinstance(receipt_dict, dict):
        return None
    body = {k: v for k, v in receipt_dict.items() if k != "receipt_hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def compute_endpoint_input_digest(url, method, variations, min_status=200, max_status=299, required_keys=None):
    norm_vars = []
    for v in variations or [{}]:
        if isinstance(v, dict):
            nv = {k: val for k, val in v.items() if k not in ("status", "response", "item_count", "error", "headers")}
            norm_vars.append(nv if nv else v)
        else:
            norm_vars.append(v)
    input_obj = {
        "max_status": max_status if max_status is not None else 299,
        "method": (method or "GET").upper(),
        "min_status": min_status if min_status is not None else 200,
        "required_keys": sorted(required_keys) if isinstance(required_keys, list) else [],
        "url": url or "",
        "variations": norm_vars,
    }
    return hashlib.sha256(canonical_json(input_obj).encode("utf-8")).hexdigest()


def validate_verification_receipt(receipt, ep, spec, base_url):
    if not isinstance(receipt, dict):
        return False, "Receipt is not a dictionary"

    if receipt.get("receipt_version") != "1.0":
        return False, f"Unsupported receipt version: {receipt.get('receipt_version')}"

    expected_hash = compute_receipt_hash(receipt)
    if not expected_hash or receipt.get("receipt_hash") != expected_hash:
        return False, f"Receipt hash mismatch: expected {expected_hash}, got {receipt.get('receipt_hash')}"

    if not receipt.get("verified"):
        return False, "Receipt verified field is not true"

    if receipt.get("classification") != "DIRECT_API_VERIFIED":
        return False, f"Receipt classification is '{receipt.get('classification')}', expected DIRECT_API_VERIFIED"

    ep_method = (ep.get("method") or spec.get("method") or "GET").upper()
    rcpt_method = (receipt.get("method") or "").upper()
    if ep_method != rcpt_method:
        return False, f"Method mismatch: endpoint method {ep_method} != receipt method {rcpt_method}"

    ep_url = ep.get("url") or spec.get("url") or f"{base_url.rstrip('/')}/{ep.get('path', '').lstrip('/')}"
    rcpt_url = receipt.get("url") or ""

    parsed_ep = urllib.parse.urlparse(ep_url)
    parsed_rcpt = urllib.parse.urlparse(rcpt_url)

    url_match = (
        ep_url.rstrip("/") == rcpt_url.rstrip("/")
        or (parsed_ep.path.rstrip("/") == parsed_rcpt.path.rstrip("/") and (not parsed_ep.netloc or not parsed_rcpt.netloc or parsed_ep.netloc.lower() == parsed_rcpt.netloc.lower()))
    )
    if not url_match:
        return False, f"URL mismatch: endpoint URL {ep_url} != receipt URL {rcpt_url}"

    ep_vars = ep.get("variations") or spec.get("variations") or ep.get("verification", {}).get("tested_variations") or spec.get("tested_variations")
    if ep_vars and receipt.get("input_digest"):
        min_st = ep.get("min_status") if ep.get("min_status") is not None else spec.get("min_status", 200)
        max_st = ep.get("max_status") if ep.get("max_status") is not None else spec.get("max_status", 299)
        req_keys = ep.get("required_keys") or spec.get("required_keys") or []
        expected_digest = compute_endpoint_input_digest(ep_url, ep_method, ep_vars, min_st, max_st, req_keys)
        alt_digest = compute_endpoint_input_digest(rcpt_url, ep_method, ep_vars, min_st, max_st, req_keys)
        if receipt.get("input_digest") != expected_digest and receipt.get("input_digest") != alt_digest:
            matched = False
            for cand_url in (ep_url, rcpt_url):
                for cand_req in ([req_keys] if isinstance(req_keys, str) else [req_keys, []]):
                    if receipt.get("input_digest") == compute_endpoint_input_digest(cand_url, ep_method, ep_vars, min_st, max_st, cand_req):
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                return False, f"Input digest mismatch: expected {expected_digest}, got {receipt.get('input_digest')}"

    return True, receipt

def find_receipt_for_endpoint(ep, spec, root, args):
    if getattr(args, "receipt", None):
        rp = Path(args.receipt).resolve()
        if rp.exists():
            try:
                return json.loads(rp.read_text(encoding="utf-8"))
            except Exception:
                pass

    candidate = (
        ep.get("verification", {}).get("receipt")
        or ep.get("receipt")
        or spec.get("verification", {}).get("receipt")
        or spec.get("receipt")
    )
    if isinstance(candidate, dict):
        return candidate
    elif isinstance(candidate, str) and candidate.endswith(".json"):
        cp = Path(candidate).resolve()
        if cp.exists():
            try:
                return json.loads(cp.read_text(encoding="utf-8"))
            except Exception:
                pass

    candidate_file = (
        ep.get("verification", {}).get("receipt_file")
        or ep.get("receipt_file")
        or ep.get("receipt_path")
        or spec.get("verification", {}).get("receipt_file")
        or spec.get("receipt_file")
        or spec.get("receipt_path")
    )
    if candidate_file:
        cp = Path(candidate_file).resolve()
        if cp.exists():
            try:
                return json.loads(cp.read_text(encoding="utf-8"))
            except Exception:
                pass

    search_dirs = []
    if getattr(args, "receipts_dir", None):
        search_dirs.append(Path(args.receipts_dir).resolve())

    root_path = resolve_root(getattr(args, "root", None) or os.getcwd())
    run_id = getattr(args, "run_id", None) or spec.get("run_id") or ep.get("run_id")
    if run_id:
        search_dirs.append(root_path / PRIVATE_DIR / "runs" / safe_token(run_id) / "receipts")
    search_dirs.append(root_path / PRIVATE_DIR / "evidence" / "receipts")
    search_dirs.append(root_path / PRIVATE_DIR / "receipts")

    receipt_id = (
        ep.get("verification", {}).get("receipt_id")
        or ep.get("receipt_id")
        or spec.get("verification", {}).get("receipt_id")
        or spec.get("receipt_id")
    )

    for sdir in search_dirs:
        if not sdir.exists() or not sdir.is_dir():
            continue
        if receipt_id:
            rf = sdir / f"{receipt_id}.json"
            if rf.exists():
                try:
                    return json.loads(rf.read_text(encoding="utf-8"))
                except Exception:
                    pass
        for f in sdir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("receipt_version") == "1.0":
                    if receipt_id and data.get("receipt_id") == receipt_id:
                        return data
                    ep_method = (ep.get("method") or spec.get("method") or "GET").upper()
                    rcpt_method = (data.get("method") or "").upper()
                    if ep_method == rcpt_method:
                        ep_path = ep.get("path") or spec.get("path") or ""
                        rcpt_url = data.get("url") or ""
                        if ep_path and (ep_path in rcpt_url or urllib.parse.urlparse(rcpt_url).path == ep_path):
                            return data
            except Exception:
                pass

    return None

def validate_auth_renewal(auth_renewal, spec, base_url, root=None, args=None):
    if not isinstance(auth_renewal, dict):
        return None
    r_type = auth_renewal.get("type")
    if r_type not in ("refresh_endpoint", "login_flow"):
        return None

    endpoint_conf = auth_renewal.get("endpoint") or {}
    if not isinstance(endpoint_conf, dict):
        return None

    renewal_path = endpoint_conf.get("path") or endpoint_conf.get("url") or "/api/auth/refresh"
    renewal_url = endpoint_conf.get("url") or f"{base_url.rstrip('/')}/{renewal_path.lstrip('/')}"
    renewal_method = (endpoint_conf.get("method") or "POST").upper()

    renewal_dummy_ep = {
        "id": "auth-renewal",
        "method": renewal_method,
        "path": renewal_path,
        "url": renewal_url,
        "classification": "DIRECT_API_VERIFIED",
        "receipt": auth_renewal.get("receipt"),
        "receipt_id": auth_renewal.get("receipt_id"),
        "receipt_file": auth_renewal.get("receipt_file") or auth_renewal.get("receipt_path"),
        "verification": {
            "tested_variations": auth_renewal.get("tested_variations")
            or endpoint_conf.get("tested_variations")
            or [{"status": 200}]
        },
    }

    found_rcpt = find_receipt_for_endpoint(renewal_dummy_ep, spec, root, args)
    if not found_rcpt:
        return None

    is_valid, validated_or_reason = validate_verification_receipt(
        found_rcpt, renewal_dummy_ep, spec, base_url
    )
    if not is_valid:
        return None

    validated_rcpt = validated_or_reason

    raw_statuses = auth_renewal.get("trigger_statuses", [401, 403])
    if isinstance(raw_statuses, list):
        trigger_statuses = [int(s) for s in raw_statuses if isinstance(s, (int, str)) and str(s).isdigit()]
    else:
        trigger_statuses = [401, 403]
    if not trigger_statuses:
        trigger_statuses = [401, 403]

    token_mapping = auth_renewal.get("token_mapping") or {}
    if not isinstance(token_mapping, dict):
        token_mapping = {}

    sanitized_mapping = {
        "source_field": str(token_mapping.get("source_field") or "access_token"),
        "target_header": str(token_mapping.get("target_header") or "Authorization"),
        "target_format": str(token_mapping.get("target_format") or "Bearer {token}"),
    }

    sanitized_endpoint = {
        "path": renewal_path,
        "method": renewal_method,
        "headers": endpoint_conf.get("headers") or {"Content-Type": "application/json"},
        "body_template": endpoint_conf.get("body_template") or {"refresh_token": "{refresh_token}"},
    }
    if "url" in endpoint_conf and endpoint_conf["url"]:
        sanitized_endpoint["url"] = sanitize_url(endpoint_conf["url"])

    return {
        "type": r_type,
        "trigger_statuses": trigger_statuses,
        "endpoint": sanitize_deep(sanitized_endpoint),
        "token_mapping": sanitize_deep(sanitized_mapping),
        "receipt_id": validated_rcpt.get("receipt_id"),
        "receipt_hash": validated_rcpt.get("receipt_hash"),
        "receipt_version": validated_rcpt.get("receipt_version", "1.0"),
    }


def validate_har_lifecycle(root, run_id, har_file_path=None):
    if not root or not run_id:
        return None
    root_path = resolve_root(root)
    lifecycle_file = root_path / PRIVATE_DIR / "runs" / safe_token(run_id) / "har-lifecycle.json"
    if not lifecycle_file.exists():
        fail(f"HAR lifecycle record missing for run {run_id}. HAR capture must follow har-start -> flow -> har-stop lifecycle.")
    try:
        state = json.loads(lifecycle_file.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Corrupted HAR lifecycle record for run {run_id}: {exc}")

    if state.get("status") != "finalized":
        fail(f"HAR capture lifecycle for run {run_id} is not finalized (status: '{state.get('status')}').")

    if state.get("pre_capture") and (not state.get("target_flow") or state.get("target_flow") in ("pre-capture", "setup", "login", "auth")):
        fail(f"HAR capture lifecycle for run {run_id} lacks target-flow evidence (pre-capture setup cannot satisfy target-flow evidence gate alone).")

    if har_file_path:
        hp = Path(har_file_path).resolve()
        if not hp.exists():
            fail(f"HAR file does not exist: {hp}")
        actual_hash = hashlib.sha256(hp.read_bytes()).hexdigest()
        expected_hash = state.get("har_sha256")
        if actual_hash != expected_hash:
            fail(f"HAR SHA-256 mismatch for run {run_id}: expected {expected_hash}, got {actual_hash}")

    return state


def har_start(args):
    root = resolve_root(args.root)
    run_id = safe_token(args.run_id)
    run_dir = root / PRIVATE_DIR / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lifecycle_file = run_dir / "har-lifecycle.json"

    capture_id = f"cap_{hashlib.sha256(f'{run_id}:{args.target_flow}:{time.time()}'.encode('utf-8')).hexdigest()[:16]}"
    state = {
        "status": "recording",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_flow": args.target_flow,
        "capture_id": capture_id,
        "pre_capture": bool(args.pre_capture),
    }
    lifecycle_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(sanitize_deep(state), indent=2))


def har_stop(args):
    root = resolve_root(args.root)
    run_id = safe_token(args.run_id)
    run_dir = root / PRIVATE_DIR / "runs" / run_id
    lifecycle_file = run_dir / "har-lifecycle.json"

    if not lifecycle_file.exists():
        fail(f"HAR capture was not started for run: {run_id}")
    try:
        state = json.loads(lifecycle_file.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Invalid HAR lifecycle state: {exc}")

    if state.get("status") != "recording":
        fail(f"HAR capture is not in recording state (status: {state.get('status')}) for run: {run_id}")

    har_file = Path(args.har_file).resolve()
    if not har_file.exists():
        fail(f"HAR file does not exist: {har_file}")

    content_bytes = har_file.read_bytes()
    try:
        json.loads(content_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        fail(f"HAR file is not valid JSON: {exc}")

    har_sha256 = hashlib.sha256(content_bytes).hexdigest()

    saved_har = run_dir / "capture.har"
    if har_file != saved_har:
        try:
            saved_har.write_bytes(content_bytes)
        except Exception:
            pass

    state["status"] = "finalized"
    state["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["har_path"] = str(saved_har)
    state["original_har_path"] = str(har_file)
    state["har_sha256"] = har_sha256

    lifecycle_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(sanitize_deep(state), indent=2))


def har_analyze(args):
    har_file = Path(args.har).resolve()
    if not har_file.exists():
        fail(f"HAR file does not exist: {har_file}")

    root = getattr(args, "root", None)
    run_id = getattr(args, "run_id", None)
    if root and run_id:
        validate_har_lifecycle(root, run_id, har_file)

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
        all_passed = False
        failure_reason = "At least one meaningful parameter variation is required to verify direct API"

    classification = "DIRECT_API_VERIFIED" if (all_passed and variation_verified) else "BROWSER_SESSION_API"

    input_obj = {
        "max_status": max_status,
        "method": method,
        "min_status": min_status,
        "required_keys": sorted(required_keys) if isinstance(required_keys, list) else [],
        "url": url,
        "variations": variations,
    }
    input_digest = hashlib.sha256(canonical_json(input_obj).encode("utf-8")).hexdigest()

    sanitized_tested = [sanitize_deep(r) for r in tested_results]
    result_digests = [
        hashlib.sha256(canonical_json(r).encode("utf-8")).hexdigest()
        for r in sanitized_tested
    ]

    successful_variation_count = sum(
        1 for r in tested_results
        if min_status <= (r.get("status") or 0) <= max_status
        and (not required_keys or (isinstance(r.get("response"), dict) and all(rk in r.get("response") for rk in required_keys)))
        and not r.get("error")
    )

    pass_assertions = {
        "status_in_range": bool(tested_results and all(min_status <= (r.get("status") or 0) <= max_status for r in tested_results)),
        "required_keys_present": bool(tested_results and all(all(rk in (r.get("response") or {}) for rk in required_keys) if isinstance(r.get("response"), dict) else True for r in tested_results)),
        "distinct_responses": bool(variation_verified),
        "all_passed": bool(all_passed and variation_verified),
    }

    run_id = getattr(args, "run_id", None) or spec.get("run_id")
    token_basis = f"{url}:{method}:{input_digest}:{time.time()}"
    receipt_id = f"rcpt_{hashlib.sha256(token_basis.encode('utf-8')).hexdigest()[:16]}"
    receipt_body = {
        "receipt_version": "1.0",
        "receipt_id": receipt_id,
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "url": sanitize_url(url),
        "method": method,
        "classification": classification,
        "verified": bool(all_passed and variation_verified),
        "input_digest": input_digest,
        "variation_count": len(tested_results),
        "successful_variation_count": successful_variation_count,
        "result_digests": result_digests,
        "pass_assertions": pass_assertions,
    }
    receipt_hash = hashlib.sha256(canonical_json(receipt_body).encode("utf-8")).hexdigest()
    receipt_body["receipt_hash"] = receipt_hash

    sanitized_receipt = sanitize_deep(receipt_body)

    if getattr(args, "output_receipt", None):
        out_p = Path(args.output_receipt).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(sanitized_receipt, indent=2) + "\n", encoding="utf-8")

    if getattr(args, "root", None):
        root_path = resolve_root(args.root)
        if run_id:
            r_dir = root_path / PRIVATE_DIR / "runs" / safe_token(run_id) / "receipts"
        else:
            r_dir = root_path / PRIVATE_DIR / "evidence" / "receipts"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / f"{receipt_id}.json").write_text(json.dumps(sanitized_receipt, indent=2) + "\n", encoding="utf-8")

    output = {
        "verified": all_passed and variation_verified,
        "classification": classification,
        "url": url,
        "method": method,
        "variation_count": len(tested_results),
        "tested_variations": tested_results,
        "receipt": sanitized_receipt,
        "reason": failure_reason if not (all_passed and variation_verified) else None,
    }
    print(json.dumps(sanitize_deep(output), indent=2))


def find_matching_endpoint_index(new_ep, existing_eps):
    new_id = new_ep.get("id")
    new_method = (new_ep.get("method") or "GET").upper()
    new_path = new_ep.get("path") or ""

    if new_id:
        for idx, ep in enumerate(existing_eps):
            if ep.get("id") == new_id:
                return idx
    for idx, ep in enumerate(existing_eps):
        if (ep.get("method") or "GET").upper() == new_method and (ep.get("path") or "") == new_path:
            return idx
    return -1


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

    is_refining = False
    existing_manifest = None
    existing_provenance = None

    if output_dir.exists() and any(output_dir.iterdir()):
        if getattr(args, "fresh", False):
            shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir = output_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
        else:
            manifest_file = output_dir / "endpoint-manifest.json"
            skill_md_file = output_dir / "SKILL.md"
            if not manifest_file.exists() or not skill_md_file.exists():
                fail("Existing package is corrupted or unrecoverable; run with --fresh to perform a clean rebuild", error_code="FRESH_REQUIRED")
            try:
                existing_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                if not isinstance(existing_manifest, dict) or not isinstance(existing_manifest.get("endpoints"), list):
                    fail("Existing package endpoint-manifest.json is invalid; run with --fresh to perform a clean rebuild", error_code="FRESH_REQUIRED")
            except Exception:
                fail("Existing package endpoint-manifest.json cannot be parsed; run with --fresh to perform a clean rebuild", error_code="FRESH_REQUIRED")

            try:
                skill_md_text = skill_md_file.read_text(encoding="utf-8")
                if not skill_md_text.strip():
                    fail("Existing package SKILL.md is empty; run with --fresh to perform a clean rebuild", error_code="FRESH_REQUIRED")
            except Exception:
                fail("Existing package SKILL.md cannot be read; run with --fresh to perform a clean rebuild", error_code="FRESH_REQUIRED")

            prov_file = output_dir / "provenance.json"
            if prov_file.exists():
                try:
                    existing_provenance = json.loads(prov_file.read_text(encoding="utf-8"))
                except Exception:
                    existing_provenance = None

            is_refining = True
            scripts_dir = output_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
    else:
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
    run_id = getattr(args, "run_id", None) or spec.get("run_id")

    raw_auth_renewal = spec.get("auth_renewal")
    verified_auth_renewal = None
    if raw_auth_renewal:
        verified_auth_renewal = validate_auth_renewal(raw_auth_renewal, spec, base_url, root, args)
    elif is_refining and existing_manifest and existing_manifest.get("auth_renewal"):
        verified_auth_renewal = validate_auth_renewal(existing_manifest.get("auth_renewal"), spec, base_url, root, args) or existing_manifest.get("auth_renewal")
    raw_endpoints = spec.get("endpoints")
    spec_has_explicit_endpoints = bool(raw_endpoints)
    if not raw_endpoints:
        ep_vars = spec.get("verification", {}).get("tested_variations") or spec.get("tested_variations") or []
        ep_obj = {
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
                "tested_variations": ep_vars
            }
        }
        raw_endpoints = [ep_obj]

    for ep in raw_endpoints:
        ep_class = ep.get("classification", classification)
        ep_vars = ep.get("verification", {}).get("tested_variations") or ep.get("tested_variations") or spec.get("tested_variations") or []
        if "verification" not in ep or not isinstance(ep.get("verification"), dict):
            ep["verification"] = {}
        ep["verification"]["tested_variations"] = ep_vars

        if ep_class == "DIRECT_API_VERIFIED":
            found_rcpt = find_receipt_for_endpoint(ep, spec, root, args)
            is_valid, validated_or_reason = validate_verification_receipt(found_rcpt, ep, spec, base_url) if found_rcpt else (False, "No receipt found")
            if is_valid:
                rcpt = validated_or_reason
                ep["verification"]["status"] = "PASSED"
                ep["verification"]["receipt_id"] = rcpt.get("receipt_id")
                ep["verification"]["receipt_version"] = rcpt.get("receipt_version", "1.0")
                ep["verification"]["receipt_hash"] = rcpt.get("receipt_hash")
            else:
                ep["verification"]["status"] = "UNVERIFIED"
                ep["verification"].pop("receipt_id", None)
                ep["verification"].pop("receipt_version", None)
                ep["verification"].pop("receipt_hash", None)
        else:
            ep["verification"]["status"] = "FALLBACK"

    sanitized_endpoints = sanitize_deep(raw_endpoints)
    if is_refining and existing_manifest:
        merged_endpoints = list(existing_manifest.get("endpoints", []))
        for new_ep in sanitized_endpoints:
            match_idx = find_matching_endpoint_index(new_ep, merged_endpoints)
            if match_idx >= 0:
                merged_endpoints[match_idx] = new_ep
            else:
                merged_endpoints.append(new_ep)
        sanitized_endpoints = merged_endpoints
    har_hash = spec.get("har_sha256")
    har_source = getattr(args, "har_path", None) or spec.get("har_path")
    if har_source:
        hp = Path(har_source).resolve()
        if not hp.exists():
            fail(f"HAR file does not exist: {hp}")
        if run_id:
            lifecycle = validate_har_lifecycle(root, run_id, hp)
            if lifecycle:
                har_hash = lifecycle.get("har_sha256")
        else:
            har_hash = hashlib.sha256(hp.read_bytes()).hexdigest()
    elif run_id:
        lifecycle_file = resolve_root(root) / PRIVATE_DIR / "runs" / safe_token(run_id) / "har-lifecycle.json"
        if lifecycle_file.exists():
            lifecycle = validate_har_lifecycle(root, run_id, None)
            if lifecycle:
                har_hash = lifecycle.get("har_sha256")
    # 1. Write endpoint-manifest.json
    manifest = {
        "skill_name": capability_name,
        "target_origin": sanitize_url(base_url),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": sanitized_endpoints
    }
    if verified_auth_renewal:
        manifest["auth_renewal"] = verified_auth_renewal
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

    _et = spec.get("exploration_time") or spec.get("exploration_time_s")

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

        cap_info = {
            "name": cap_name,
            "method": ep.get("method", "GET"),
            "classification": ep_c,
            "steady_state_runtime": "python" if ep_c == "DIRECT_API_VERIFIED" else "agent-browser",
            "verified_endpoint": sanitize_deep(ep.get("path", endpoint_path))
        }
        ep_ver = ep.get("verification", {})
        if ep_c == "DIRECT_API_VERIFIED" and ep_ver.get("status") == "PASSED" and ep_ver.get("receipt_id"):
            cap_info["receipt_id"] = ep_ver.get("receipt_id")
            cap_info["receipt_version"] = ep_ver.get("receipt_version", "1.0")
            cap_info["receipt_hash"] = ep_ver.get("receipt_hash")

        prov_capabilities.append(cap_info)

    provenance = {
        "forge_version": "0.1.0",
        "agent_browser_version": get_live_agent_browser_version(root),
        "target_origin": sanitize_url(base_url),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
    if is_refining:
        provenance["refined"] = True
    if _et is not None:
        provenance["exploration_time"] = _et
    elif is_refining and existing_provenance and "exploration_time" in existing_provenance:
        provenance["exploration_time"] = existing_provenance["exploration_time"]
    if verified_auth_renewal:
        provenance["auth_renewal"] = verified_auth_renewal
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
                cli_arg_lines = []
                cli_call_args = []
            cli_args_code = "\n".join(cli_arg_lines) if cli_arg_lines else ""
            cli_call_code = f'    result = client.{primary_ep_id}({", ".join(cli_call_args)})'


        if verified_auth_renewal:
            renewal_ep = verified_auth_renewal.get("endpoint") or {}
            renewal_path = renewal_ep.get("path") or "/api/auth/refresh"
            renewal_method = (renewal_ep.get("method") or "POST").upper()
            renewal_headers = renewal_ep.get("headers") or {"Content-Type": "application/json"}
            renewal_body_template = renewal_ep.get("body_template") or {"refresh_token": "{refresh_token}"}
            t_map = verified_auth_renewal.get("token_mapping") or {}
            source_field = t_map.get("source_field") or "access_token"
            target_header = t_map.get("target_header") or "Authorization"
            target_format = t_map.get("target_format") or "Bearer {token}"
            trigger_statuses = verified_auth_renewal.get("trigger_statuses", [401, 403])

            client_class_code = f'''class APIClient:
    def __init__(self, base_url=BASE_URL, auth_token=None, refresh_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("API_AUTH_TOKEN")
        self.refresh_token = refresh_token or os.environ.get("API_REFRESH_TOKEN") or os.environ.get("REFRESH_TOKEN")
        if not self.auth_token or not self.refresh_token:
            self._discover_auth()

    def _discover_auth(self):
        """Discover auth.json from the private .agent-forge boundary that contains this client file.
        If this client is inside a .agent-forge ancestor directory, read auth.json from that boundary.
        If this client is outside any .agent-forge directory (exported/installed), no file discovery
        is performed — use environment variables or pass tokens explicitly."""
        client_path = Path(__file__).resolve()
        for ancestor in client_path.parents:
            if ancestor.name == ".agent-forge":
                auth_file = ancestor / "auth.json"
                if auth_file.exists():
                    try:
                        auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                        if not self.auth_token:
                            token = auth_data.get("token") or auth_data.get("auth_token")
                            if token:
                                self.auth_token = token
                        if not self.refresh_token:
                            rt = auth_data.get("refresh_token")
                            if rt:
                                self.refresh_token = rt
                    except Exception:
                        pass
                return

    def _save_auth(self, new_token):
        client_path = Path(__file__).resolve()
        for ancestor in client_path.parents:
            if ancestor.name == ".agent-forge":
                auth_file = ancestor / "auth.json"
                try:
                    auth_data = {{}}
                    if auth_file.exists():
                        try:
                            auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                        except Exception:
                            auth_data = {{}}
                    auth_data["token"] = new_token
                    auth_data["auth_token"] = new_token
                    auth_file.write_text(json.dumps(auth_data, indent=2) + "\\n", encoding="utf-8")
                except Exception:
                    pass
                return

    def _renew_auth(self):
        """Renew authentication using the verified renewal endpoint.
        Bounded to a single renewal attempt."""
        if not self.refresh_token:
            self._discover_auth()
        if not self.refresh_token:
            return False

        renewal_url = f"{{self.base_url}}/{renewal_path.lstrip('/')}"
        headers = {json.dumps(renewal_headers)}
        body_template = {json.dumps(renewal_body_template)}
        body = {{}}
        if isinstance(body_template, dict):
            for k, v in body_template.items():
                if isinstance(v, str) and "{{refresh_token}}" in v:
                    body[k] = v.replace("{{refresh_token}}", str(self.refresh_token))
                else:
                    body[k] = v
        else:
            body = {{"refresh_token": str(self.refresh_token)}}

        try:
            encoded_data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(renewal_url, data=encoded_data, headers=headers, method={json.dumps(renewal_method)})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                new_token = data.get({json.dumps(source_field)})
                if new_token:
                    self.auth_token = new_token
                    self._save_auth(new_token)
                    return True
        except Exception:
            return False
        return False

    def _request(self, path, params=None, data=None, method="GET", _is_retry=False):
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
            target_hdr = {json.dumps(target_header)}
            target_fmt = {json.dumps(target_format)}
            headers[target_hdr] = target_fmt.replace("{{token}}", self.auth_token)

        encoded_data = json.dumps(data).encode("utf-8") if data else None
        if encoded_data:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in {json.dumps(trigger_statuses)}:
                if not _is_retry:
                    if self._renew_auth():
                        return self._request(path, params=params, data=data, method=method, _is_retry=True)
                    return {{"error": True, "code": "AUTH_EXPIRED", "message": "Authentication token expired and renewal failed"}}
                return {{"error": True, "code": "AUTH_EXPIRED", "message": "Authentication token expired and renewal failed"}}
            return {{"error": True, "code": f"HTTP_{{exc.code}}", "message": f"HTTP request failed with status {{exc.code}}"}}
        except Exception as exc:
            return {{"error": True, "code": "REQUEST_FAILED", "message": "HTTP request failed due to client connection error"}}'''
        else:
            client_class_code = f'''class APIClient:
    def __init__(self, base_url=BASE_URL, auth_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("API_AUTH_TOKEN")
        if not self.auth_token:
            self._discover_auth()

    def _discover_auth(self):
        """Discover auth.json from the private .agent-forge boundary that contains this client file.
        If this client is inside a .agent-forge ancestor directory, read auth.json from that boundary.
        If this client is outside any .agent-forge directory (exported/installed), no file discovery
        is performed — use the API_AUTH_TOKEN environment variable or pass auth_token explicitly."""
        client_path = Path(__file__).resolve()
        # Walk ancestors of this client file looking for a directory literally named .agent-forge
        for ancestor in client_path.parents:
            if ancestor.name == ".agent-forge":
                # This client lives inside a .agent-forge boundary; read only that boundary's auth.json
                auth_file = ancestor / "auth.json"
                if auth_file.exists():
                    try:
                        auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
                        token = auth_data.get("token") or auth_data.get("auth_token")
                        if token:
                            self.auth_token = token
                    except Exception:
                        pass
                return  # Found the boundary — stop regardless of whether auth loaded
        # No .agent-forge ancestor found: client is outside the private workspace (exported/installed).
        # Do not attempt any file-based auth discovery; require explicit auth_token or API_AUTH_TOKEN.

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
            return {{"error": True, "code": "REQUEST_FAILED", "message": "HTTP request failed due to client connection error"}}'''

        client_code = f'''import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = {json.dumps(base_url)}


{client_class_code}

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
    const query = {{query_json}};
    const limit = {{limit_json}};
    const selectors = [
      '.item-card', '.product-card', '.list-row', 'tr.item', 'li.product-card',
      '[data-item]', '.card', '.item', 'li[class*="product"]', 'li[class*="item"]',
      'div[class*="product"]', 'div[class*="item"]', '#items-list > li', '#items-list > div',
      'ul.items > li', '.items-list > li'
    ];
    let rows = Array.from(document.querySelectorAll(selectors.join(', ')));
    if (!rows.length) {{{{
      const container = document.querySelector('#items-list, ul.items, .products-list, .catalog-list');
      if (container && container.children.length) {{{{
        rows = Array.from(container.children);
      }}}}
    }}}}
    if (!rows.length) {{{{
      return JSON.stringify({{{{ error: true, code: "ELEMENT_NOT_FOUND", message: "No items found in DOM" }}}});
    }}}}
    const rawItems = rows.map(row => {{{{
      let url = '';
      if (row.tagName === 'A' && row.href) {{{{
        url = row.href;
      }}}} else {{{{
        const link = row.querySelector('a[href]');
        if (link) url = link.href;
      }}}}

      const titleEl = row.querySelector('.title, .product-title, .item-title, .name, [data-title], [data-name], h1, h2, h3, h4, h5, [class*="title"], [class*="name"]');
      const priceEl = row.querySelector('.price, .product-price, .item-price, .cost, .amount, [data-price], [class*="price"]');

      let title = titleEl ? titleEl.textContent.trim() : '';
      let price = priceEl ? priceEl.textContent.trim() : null;

      const fullText = (row.textContent || '').replace(/\\\\s+/g, ' ').trim();

      if (!price) {{{{
        const priceMatch = fullText.match(/(?:^|[-–—\\\\s|:,])([$€£¥₹]\\\\s*[\\\\d,]+(?:\\\\.\\\\d+)?|\\\\b[\\\\d,]+(?:\\\\.\\\\d+)?\\\\s*(?:USD|EUR|GBP|VND|đ|[$€£¥₹])\\\\b)/i);
        if (priceMatch) {{{{
          price = priceMatch[1].trim();
        }}}}
      }}}}

      if (!title) {{{{
        const aEl = row.querySelector('a');
        if (aEl && aEl.textContent.trim()) {{{{
          title = aEl.textContent.trim();
        }}}} else if (price) {{{{
          let cleaned = fullText.replace(price, '');
          cleaned = cleaned.replace(/^[-–—\\\\s|:,]+|[-–—\\\\s|:,]+$/g, '').trim();
          title = cleaned || fullText;
        }}}} else {{{{
          title = fullText;
        }}}}
      }}}}

      return {{{{ title, url, price }}}};
    }}}});

    const filtered = query
      ? rawItems.filter(it => (it.title && it.title.toLowerCase().includes(query.toLowerCase())) || (it.price && it.price.toLowerCase().includes(query.toLowerCase())))
      : rawItems;

    const items = filtered.slice(0, limit);
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
    sys.stdout.buffer.write(build_js(query=args.query, limit=args.limit).encode("utf-8"))


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
    skill_md_param_lines = []
    if readme_query_params:
        for pn, pd in readme_query_params.items():
            arg_name = pn.replace("-", "_")
            ptype = pd.get("type", "string") if isinstance(pd, dict) else "string"
            if ptype in ("integer", "int"):
                skill_md_param_lines.append(f'- `--{arg_name} <int>`: {pd.get("description", arg_name)}.')
            else:
                skill_md_param_lines.append(f'- `--{arg_name} <string>`: {pd.get("description", arg_name)}.')

    skill_md_params_block = "\n".join(skill_md_param_lines) if skill_md_param_lines else "No query parameters required."
    enum_param_rows = []
    for pn, pd in readme_query_params.items():
        options = (pd.get("options") or pd.get("enum") or []) if isinstance(pd, dict) else []
        if options:
            arg_name = pn.replace("-", "_")
            enum_param_rows.append(f'| `{arg_name}` | string | declared in verified spec | {", ".join(str(o) for o in options)} |')
    enum_params_block = "\n".join(enum_param_rows) if enum_param_rows else "No enum parameters are declared in the verified spec for this capability."

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
            first_pd = readme_query_params[first_pn] if isinstance(readme_query_params[first_pn], dict) else {}
            first_type = first_pd.get("type", "string")
            first_example = "1" if first_type in ("integer", "int") else "keyword"
            readme_python_example = f'result = client.{readme_ep_id}({first_arg}={first_example})'
            readme_cli_example = f'python client.py --{first_arg} {first_example}'
        else:
            readme_python_example = f'result = client.{readme_ep_id}()'
            readme_cli_example = f'python client.py'

    if has_direct_endpoints:
        prereqs = f'''- Python 3.8+ (for direct API client operations)
- `agent-browser` (for browser-session or DOM-fallback interactions)'''
        client_sections = f'''## Python API Client
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
```'''
    else:
        prereqs = f'''- Python 3.8+
- `agent-browser` installed and target page accessible'''
        client_sections = f'''## Browser Steady-State Usage
This is a browser-only capability (`{classification}`). Direct API client (`client.py`) is not generated.
Execute the capability by running the generated Python helper script to build the DOM extraction script, and passing it to `agent-browser`:

**POSIX (Bash / Zsh):**
```bash
python scripts/{capability_slug}.py --query "<query>" --limit <limit> | agent-browser eval --stdin
```

**Windows (PowerShell / Command Prompt):**
```bash
python scripts/{capability_slug}.py --query "<query>" --limit <limit> > temp_eval.js
cmd.exe /c "agent-browser eval --stdin < temp_eval.js"
```

### Parameters
- `--query <string>`: Search keyword.
- `--limit <int>`: Max items.
'''

    if has_direct_endpoints:
        reval_section = f'''## Revalidation
To revalidate this capability against drift or auth expiration:

- **Quick direct client revalidation**:
```bash
python client.py
```

- **Full capability revalidation** (via forge runtime):
```bash
python <agent-browser-skill-forge-root>/scripts/forge-runtime.py revalidate-skill --package-dir .
```'''
    else:
        reval_section = f'''## Revalidation
To revalidate this capability against drift or auth expiration:

```bash
python <agent-browser-skill-forge-root>/scripts/forge-runtime.py revalidate-skill --package-dir .
```'''

    readme_content = f'''# {site_name} — {capability_name}

> Classification: `{classification}`
> Reusable skill package for {site_name} generated by `agent-browser-skill-forge`.

## Overview
- **Target Origin**: `{base_url}`
- **Classification**: `{classification}`
- **Generated At**: {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

## Installation & Prerequisites
{prereqs}

{client_sections}

## Data Models
Data models are defined in `models.py` when schema is present.

{reval_section}
'''
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")

    # 7. Write SKILL.md
    if classification == "DIRECT_API_VERIFIED":
        component_section = f'''### Standalone API Client (DIRECT_API_VERIFIED)

`{readme_cli_example}`

Parameters:
{skill_md_params_block}

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

**POSIX (Bash / Zsh):**
```bash
python scripts/{capability_slug}.py --query "<query>" --limit <limit> | agent-browser eval --stdin
```

**Windows (PowerShell / Command Prompt):**
```bash
python scripts/{capability_slug}.py --query "<query>" --limit <limit> > temp_eval.js
cmd.exe /c "agent-browser eval --stdin < temp_eval.js"
```

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

    if classification == "DIRECT_API_VERIFIED":
        recovery_fast_path = "Run the verified client (`python client.py`)."
    elif classification == "HYBRID":
        recovery_fast_path = f"Run the verified direct client (`python client.py`) or browser extraction script (`python scripts/{capability_slug}.py`)."
    else:
        recovery_fast_path = f"Run the verified browser extraction script (`python scripts/{capability_slug}.py`)."

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

{enum_params_block}

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

1. Fast path: {recovery_fast_path}
2. On 401/403 or schema drift: Revalidate capability via `python <agent-browser-skill-forge-root>/scripts/forge-runtime.py revalidate-skill --package-dir .`.
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

        # Coordinator-agnostic instruction check
        for pat in COORDINATOR_REGEXES:
            if re.search(pat, text, re.IGNORECASE):
                errors.append(f"SKILL.md contains coordinator-specific syntax matching '{pat}'")

    # 2. endpoint-manifest.json
    manifest_path = pkg_dir / "endpoint-manifest.json"
    if not manifest_path.exists():
        errors.append("endpoint-manifest.json is missing")
    else:
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(m.get("endpoints"), list):
                errors.append("endpoint-manifest.json must contain 'endpoints' array")
            else:
                for ep in m.get("endpoints", []):
                    if ep.get("classification") == "DIRECT_API_VERIFIED" and ep.get("verification", {}).get("status") == "PASSED":
                        ver = ep.get("verification", {})
                        if not ver.get("receipt_id") or not ver.get("receipt_hash") or not ver.get("receipt_version"):
                            errors.append(f"DIRECT_API_VERIFIED endpoint '{ep.get('id')}' is marked PASSED without valid verification receipt reference")
            if m.get("auth_renewal"):
                ar = m.get("auth_renewal")
                if isinstance(ar, dict) and ar.get("type") in ("refresh_endpoint", "login_flow"):
                    if not ar.get("receipt_id") or not ar.get("receipt_hash"):
                        errors.append("auth_renewal is present in manifest without valid verification receipt reference")
        except Exception as exc:
            errors.append(f"endpoint-manifest.json is invalid JSON: {exc}")
    prov_path = pkg_dir / "provenance.json"
    if not prov_path.exists():
        errors.append("provenance.json is missing")
    else:
        try:
            p = json.loads(prov_path.read_text(encoding="utf-8"))
            if "har_sha256" not in p:
                errors.append("provenance.json must contain 'har_sha256'")
            if p.get("auth_renewal"):
                ar = p.get("auth_renewal")
                if isinstance(ar, dict) and ar.get("type") in ("refresh_endpoint", "login_flow"):
                    if not ar.get("receipt_id") or not ar.get("receipt_hash"):
                        errors.append("auth_renewal is present in provenance without valid verification receipt reference")
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
        print("; ".join(errors), file=sys.stderr)
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


def get_supplied_params(test_cases_data, ep_id):
    if not test_cases_data:
        return None
    if isinstance(test_cases_data, dict):
        if ep_id in test_cases_data:
            val = test_cases_data[ep_id]
            if isinstance(val, dict):
                if "params" in val:
                    return val["params"]
                return val
        for k, v in test_cases_data.items():
            if k.lower() == ep_id.lower():
                if isinstance(v, dict):
                    if "params" in v:
                        return v["params"]
                    return v
    if isinstance(test_cases_data, list):
        for item in test_cases_data:
            if isinstance(item, dict):
                for key_name in ("id", "endpoint", "name", "component"):
                    if item.get(key_name) == ep_id:
                        if "params" in item:
                            return item["params"]
                        return {k: v for k, v in item.items() if k not in ("id", "endpoint", "name", "component")}
    return None


def test_skill(args):
    test_cases_data = None
    if getattr(args, "test_cases", None):
        try:
            if args.test_cases.strip().startswith(("{", "[")):
                test_cases_data = json.loads(args.test_cases)
            else:
                p = Path(args.test_cases)
                if p.exists() and p.is_file():
                    test_cases_data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass

    pkg_dir = Path(args.package_dir).resolve()
    if not pkg_dir.exists() or not pkg_dir.is_dir():
        fail(f"Package directory does not exist: {pkg_dir}")

    manifest_file = pkg_dir / "endpoint-manifest.json"
    skill_md_file = pkg_dir / "SKILL.md"

    if not skill_md_file.exists():
        fail(f"SKILL.md missing in package: {pkg_dir}")

    manifest = {}
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    base_url = args.base_url or manifest.get("target_origin") or "https://example.com"
    endpoints = manifest.get("endpoints") or []

    has_client = (pkg_dir / "client.py").exists()

    components = []
    all_passed = True
    unclear_instructions = []
    severe_issues = []
    failures = []

    # 1. Check SKILL.md for coordinator-specific syntax
    skill_md_text = skill_md_file.read_text(encoding="utf-8")
    for pat in COORDINATOR_REGEXES:
        if re.search(pat, skill_md_text, re.IGNORECASE):
            unclear_instructions.append(f"SKILL.md contains coordinator-specific syntax matching '{pat}'")
            all_passed = False

    # 2. Check for snapshot refs in package
    if re.search(r"@e\d+\b", skill_md_text):
        severe_issues.append("SKILL.md persists concrete snapshot ref (@eN)")
        all_passed = False

    # 3. Test each declared endpoint/component
    if endpoints:
        for ep in endpoints:
            ep_id = ep.get("id") or "endpoint"
            ep_class = ep.get("classification", "DIRECT_API_VERIFIED")
            method_name = safe_token(ep_id).replace("-", "_")

            comp_result = {
                "name": ep_id,
                "classification": ep_class,
                "steady_state_runtime": "python" if ep_class == "DIRECT_API_VERIFIED" else "agent-browser",
                "status": "PASSED",
                "import_check": None,
                "cli_check": None,
                "output_summary": None,
            }

            # Retrieve parameter values to avoid false-failing valid capabilities
            supplied_params = get_supplied_params(test_cases_data, ep_id)
            if supplied_params is not None:
                params_to_use = dict(supplied_params)
            else:
                params_to_use = {}
                variations = ep.get("verification", {}).get("tested_variations") or []
                successful_variations = [v for v in variations if isinstance(v, dict) and v.get("status") in (200, 201, 204)]
                if successful_variations:
                    params_to_use = successful_variations[0].get("params") or {}
                elif variations:
                    params_to_use = variations[0].get("params") or {}

                if not params_to_use:
                    ep_params = ep.get("parameters") or {}
                    for p_name, p_def in ep_params.items():
                        if isinstance(p_def, dict):
                            p_val = p_def.get("default")
                            if p_val is not None and p_val != "[REDACTED]":
                                params_to_use[p_name] = p_val

            python_params = {k.replace("-", "_"): v for k, v in params_to_use.items()}

            if ep_class in ("DIRECT_API_VERIFIED", "HYBRID"):
                client_path = pkg_dir / "client.py"
                if not client_path.exists():
                    all_passed = False
                    comp_result["status"] = "FAILED"
                    comp_result["error"] = "client.py missing for DIRECT_API_VERIFIED endpoint"
                    failures.append(f"{ep_id}: client.py missing")
                    components.append(comp_result)
                    continue

                # Python module import check
                import_ok = False
                import_out = None
                import_err = None
                py_code = f"""
import sys, json
sys.path.insert(0, {json.dumps(str(pkg_dir))})
try:
    from client import APIClient
    client = APIClient(base_url={json.dumps(base_url)})
    if hasattr(client, {json.dumps(method_name)}):
        m = getattr(client, {json.dumps(method_name)})
        res = m(**{json.dumps(python_params)})
        print(json.dumps({{"success": True, "data": res}}))
    elif hasattr(client, "extract_items"):
        res = client.extract_items(**{json.dumps(python_params)})
        print(json.dumps({{"success": True, "data": res}}))
    else:
        print(json.dumps({{"success": False, "error": f"Method {{method_name}} not found on APIClient"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
                try:
                    proc = subprocess.run([sys.executable, "-c", py_code], cwd=str(pkg_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                    if proc.stdout.strip():
                        parsed = json.loads(proc.stdout.strip())
                        if parsed.get("success"):
                            import_out = parsed.get("data")
                            if isinstance(import_out, dict) and import_out.get("error") is True:
                                import_ok = False
                                import_err = import_out.get("message") or "Returned error envelope"
                            else:
                                import_ok = True
                        else:
                            import_err = parsed.get("error")
                    else:
                        import_err = proc.stderr.strip() or "Import check failed"
                except Exception as ex:
                    import_err = str(ex)

                comp_result["import_check"] = import_ok
                if not import_ok:
                    comp_result["status"] = "FAILED"
                    all_passed = False
                    failures.append(f"{ep_id} Python import check failed: {import_err}")

                # CLI execution check
                cli_ok = False
                cli_out = None
                cli_err = None
                cli_args = []
                method_upper = ep.get("method", "GET").upper()
                if method_upper in ("POST", "PUT", "PATCH"):
                    if params_to_use:
                        cli_args = ["--data", json.dumps(params_to_use)]
                elif method_upper == "DELETE":
                    val_id = params_to_use.get("id")
                    if val_id is None and params_to_use:
                        val_id = list(params_to_use.values())[0]
                    if val_id is not None:
                        cli_args = ["--id", str(val_id)]
                else:
                    for k, v in params_to_use.items():
                        if v is not None:
                            cli_args.extend([f"--{k.replace('-', '_')}", str(v)])
                try:
                    cli_proc = subprocess.run([sys.executable, str(client_path)] + cli_args, cwd=str(pkg_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                    if cli_proc.stdout.strip():
                        try:
                            parsed_cli = json.loads(cli_proc.stdout.strip())
                            cli_out = parsed_cli
                            if isinstance(cli_out, dict) and cli_out.get("error") is True:
                                cli_ok = False
                                cli_err = cli_out.get("message") or "Returned error envelope"
                            else:
                                cli_ok = True
                        except Exception:
                            cli_ok = (cli_proc.returncode == 0)
                    elif cli_proc.returncode == 0:
                        cli_ok = True
                    else:
                        cli_err = (cli_proc.stderr or cli_proc.stdout or "").strip()
                except Exception as ex:
                    cli_err = str(ex)

                comp_result["cli_check"] = cli_ok
                if not cli_ok:
                    comp_result["status"] = "FAILED"
                    all_passed = False
                    failures.append(f"{ep_id} CLI execution check failed: {cli_err or 'unknown'}")

                # Sanitized output summary
                sample_data = import_out or cli_out
                if isinstance(sample_data, dict):
                    comp_result["output_summary"] = {
                        "keys": list(sample_data.keys()),
                        "has_items": "items" in sample_data or "results" in sample_data or "data" in sample_data,
                        "item_count": len(sample_data["items"]) if isinstance(sample_data.get("items"), list) else None,
                    }
                elif isinstance(sample_data, list):
                    comp_result["output_summary"] = {
                        "count": len(sample_data),
                        "first_item_keys": list(sample_data[0].keys()) if len(sample_data) > 0 and isinstance(sample_data[0], dict) else []
                    }

            if ep_class in ("DOM_ONLY", "BROWSER_SESSION_API", "HYBRID"):
                script_path = None
                if (pkg_dir / "scripts").exists():
                    for sc in (pkg_dir / "scripts").glob("*.py"):
                        if safe_token(ep_id) in sc.stem or len(list((pkg_dir / "scripts").glob("*.py"))) == 1:
                            script_path = sc
                            break

                script_ok = False
                if script_path and script_path.exists():
                    script_args = []
                    q_val = params_to_use.get("query") or params_to_use.get("q")
                    if q_val is not None:
                        script_args.extend(["--query", str(q_val)])
                    l_val = params_to_use.get("limit") or params_to_use.get("l")
                    if l_val is not None:
                        script_args.extend(["--limit", str(l_val)])
                    try:
                        s_proc = subprocess.run([sys.executable, str(script_path)] + script_args, cwd=str(pkg_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                        if s_proc.returncode == 0 and s_proc.stdout.strip():
                            script_ok = True
                            comp_result["output_summary"] = {"js_length": len(s_proc.stdout.strip()), "script": script_path.name}
                    except Exception as ex:
                        failures.append(f"{ep_id} Script execution failed: {ex}")
                else:
                    failures.append(f"{ep_id}: scripts helper missing")

                comp_result["script_check"] = script_ok
                if not script_ok:
                    comp_result["status"] = "FAILED"
                    all_passed = False

            if ep_class == "HYBRID":
                comp_result["hybrid_check"] = True

            components.append(comp_result)

    elif has_client:
        comp_result = {
            "name": "api_client",
            "classification": "DIRECT_API_VERIFIED",
            "steady_state_runtime": "python",
            "status": "PASSED",
        }
        client_path = pkg_dir / "client.py"

        supplied_params = get_supplied_params(test_cases_data, "api_client")
        if supplied_params is not None:
            params_to_use = dict(supplied_params)
        else:
            params_to_use = {}
            top_variations = manifest.get("tested_variations") or []
            successful_top = [v for v in top_variations if isinstance(v, dict) and v.get("status") in (200, 201, 204)]
            if successful_top:
                params_to_use = successful_top[0].get("params") or {}
            elif top_variations:
                params_to_use = top_variations[0].get("params") or {}

            if not params_to_use:
                ep_params = manifest.get("parameters") or {}
                for p_name, p_def in ep_params.items():
                    if isinstance(p_def, dict):
                        p_val = p_def.get("default")
                        if p_val is not None and p_val != "[REDACTED]":
                            params_to_use[p_name] = p_val

        method_upper = manifest.get("method", "GET").upper()
        cli_args = []
        if method_upper in ("POST", "PUT", "PATCH"):
            if params_to_use:
                cli_args = ["--data", json.dumps(params_to_use)]
        elif method_upper == "DELETE":
            val_id = params_to_use.get("id")
            if val_id is None and params_to_use:
                val_id = list(params_to_use.values())[0]
            if val_id is not None:
                cli_args = ["--id", str(val_id)]
        else:
            for k, v in params_to_use.items():
                if v is not None:
                    cli_args.extend([f"--{k.replace('-', '_')}", str(v)])

        try:
            c_proc = subprocess.run([sys.executable, str(client_path)] + cli_args, cwd=str(pkg_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            cli_ok = False
            if c_proc.stdout.strip():
                try:
                    json.loads(c_proc.stdout.strip())
                    cli_ok = True
                except Exception:
                    cli_ok = (c_proc.returncode == 0)
            elif c_proc.returncode == 0:
                cli_ok = True

            comp_result["cli_check"] = cli_ok
            if not cli_ok:
                comp_result["status"] = "FAILED"
                all_passed = False
                failures.append(f"client.py execution failed: {(c_proc.stderr or c_proc.stdout or '').strip()}")
        except Exception as ex:
            comp_result["status"] = "FAILED"
            all_passed = False
            failures.append(str(ex))
        components.append(comp_result)

    report = {
        "package_dir": str(pkg_dir),
        "all_passed": all_passed,
        "components": components,
        "unclear_instructions": unclear_instructions,
        "severe_issues": severe_issues,
        "severe_accuracy_performance_issues": [],
        "failures": failures,
        "failure_reasons": failures,
    }
    print(json.dumps(sanitize_deep(report), indent=2))
    if not all_passed:
        if failures:
            print("; ".join(failures), file=sys.stderr)
        sys.exit(1)


def install_skill(args):
    pkg_dir = Path(args.package_dir).resolve()
    if not pkg_dir.exists() or not pkg_dir.is_dir():
        fail(f"Package directory does not exist: {pkg_dir}")

    skill_md = pkg_dir / "SKILL.md"
    if not skill_md.exists():
        fail(f"Invalid package: SKILL.md missing in {pkg_dir}")

    root = resolve_root(args.root)
    agent = args.agent or "antigravity"
    skill_name = pkg_dir.name

    if args.dest:
        dest_dir = Path(args.dest).resolve()
    elif agent in ("antigravity", "codex", "*"):
        dest_dir = root / ".agents" / "skills" / skill_name
    elif agent in ("claude", "claude-code"):
        dest_dir = root / ".claude" / "skills" / skill_name
    else:
        dest_dir = root / ".agents" / "skills" / skill_name

    try:
        val_errors = []
        text = skill_md.read_text(encoding="utf-8")
        if not re.search(r"^---\r?\n[\s\S]*?\r?\n---", text):
            val_errors.append("SKILL.md is missing YAML frontmatter")
        if re.search(r"@e\d+\b", text):
            val_errors.append("SKILL.md contains concrete snapshot ref (@eN)")

        if val_errors:
            fail(f"Package validation failed before install: {'; '.join(val_errors)}")

        dest_dir.mkdir(parents=True, exist_ok=True)
        EXCLUDED_NAMES = {"auth.json", ".env", "capture.har", "sample.har"}
        for item in pkg_dir.iterdir():
            if item.name in EXCLUDED_NAMES or item.name.endswith(".har") or item.name == ".agent-forge":
                continue
            target = dest_dir / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        result = {
            "installed": True,
            "skill_name": skill_name,
            "source": str(pkg_dir),
            "destination": str(dest_dir),
            "agent": agent,
            "error": None
        }
        print(json.dumps(result, indent=2))
    except Exception as exc:
        result = {
            "installed": False,
            "skill_name": skill_name,
            "source": str(pkg_dir),
            "destination": str(dest_dir) if "dest_dir" in locals() else None,
            "agent": agent,
            "error": str(exc)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


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
            if ep_class == "BROWSER_SESSION_API":
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
                    "message": f"Classification '{ep_class}' requires browser session probe."
                })
                continue

            probe_result = _attempt_browser_dom_probe(base_url, ep_path, ep_class, pkg_dir=pkg_dir, ep=ep)
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
                probe_status = probe_result.get("status", "BROWSER_SESSION_REVALIDATION_REQUIRED")
                if overall_status in ("HEALTHY", "SAFE_REVALIDATION_REQUIRED"):
                    overall_status = probe_status
                tested_endpoints.append({
                    "endpoint": sanitize_deep(ep_path),
                    "method": ep_method,
                    "classification": ep_class,
                    "status": probe_status,
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


def _attempt_browser_dom_probe(base_url, ep_path, ep_class, pkg_dir=None, ep=None):
    """Perform safe live browser/DOM revalidation through the forge trusted agent-browser boundary.
    Returns {"verified": bool, "status": str, "message": str}."""
    binary = shutil.which("agent-browser.cmd" if os.name == "nt" else "agent-browser") or shutil.which("agent-browser")
    resolved_path = ep_path or ""
    if ep:
        params = ep.get("parameters", {})
        for p_name, p_def in params.items():
            if isinstance(p_def, dict):
                p_val = p_def.get("default") or "1"
                resolved_path = resolved_path.replace(f"{{{p_name}}}", str(p_val))
    resolved_path = re.sub(r"\{[a-zA-Z0-9_-]+\}", "1", resolved_path)
    target_url = f"{base_url.rstrip('/')}/{resolved_path.lstrip('/')}" if resolved_path else base_url

    if not binary:
        return {
            "verified": False,
            "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
            "message": (
                f"agent-browser not found on PATH; {ep_class} endpoint at {target_url} "
                "requires a live browser session. Install agent-browser and run: "
                f"agent-browser open '{target_url}' then eval DOM state to revalidate."
            )
        }

    run_cwd = pkg_dir or Path(os.getcwd())
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        config_path = temp_dir / "trusted.agent-browser.json"
        config_path.write_text(json.dumps({"engine": "chrome", "plugins": []}) + "\n", encoding="utf-8")
        session_id = f"agent-browser-skill-forge-reval-{uuid.uuid4().hex[:8]}"

        try:
            open_res = run_process(
                [binary, "--config", str(config_path), "--session", session_id, "open", target_url],
                run_cwd,
                check=False,
                timeout=15,
            )
            if open_res.returncode != 0:
                err_msg = (open_res.stderr or open_res.stdout or "navigation failed").strip()
                return {
                    "verified": False,
                    "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                    "message": f"Browser navigation to '{target_url}' failed: {err_msg}",
                }

            run_process(
                [binary, "--config", str(config_path), "--session", session_id, "wait", "--load", "networkidle"],
                run_cwd,
                check=False,
                timeout=15,
            )

            # Check if package has a script JS emitter in scripts/
            script_found = None
            if pkg_dir and isinstance(pkg_dir, Path) and (pkg_dir / "scripts").exists():
                ep_id = safe_token(ep.get("id", "")) if ep else ""
                for candidate in (pkg_dir / "scripts").glob("*.py"):
                    if ep_id and ep_id in candidate.stem:
                        script_found = candidate
                        break
                if not script_found:
                    candidates = list((pkg_dir / "scripts").glob("*.py"))
                    if candidates:
                        script_found = candidates[0]

            if script_found:
                js_gen = run_process([sys.executable, str(script_found)], pkg_dir, check=False, timeout=10)
                if js_gen.returncode == 0 and js_gen.stdout.strip():
                    js_code = js_gen.stdout.strip()
                    js_b64 = base64.b64encode(js_code.encode("utf-8")).decode("ascii")
                    eval_res = run_process(
                        [binary, "--config", str(config_path), "--session", session_id, "eval", "-b", js_b64],
                        run_cwd,
                        check=False,
                        timeout=15,
                    )
                    if eval_res.returncode == 0 and eval_res.stdout.strip():
                        raw_out = eval_res.stdout.strip()
                        try:
                            parsed = json.loads(raw_out)
                            if isinstance(parsed, str):
                                parsed = json.loads(parsed)
                        except Exception:
                            parsed = None

                        if isinstance(parsed, dict) and not parsed.get("error"):
                            items = parsed.get("items")
                            if items is not None and len(items) > 0:
                                return {
                                    "verified": True,
                                    "status": "BROWSER_DOM_VERIFIED",
                                    "message": f"Browser DOM probe succeeded: {len(items)} items extracted via {script_found.name}.",
                                }
                        err_detail = parsed.get("message", "no items found") if isinstance(parsed, dict) else "extraction failed"
                        return {
                            "verified": False,
                            "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                            "message": f"Browser DOM extraction failed: {err_detail}",
                        }

            # Fallback DOM / Session Health Probe
            probe_js = """
(() => {
  try {
    const title = document.title || '';
    const bodyText = (document.body ? document.body.innerText : '') || '';
    const elementsCount = document.querySelectorAll('*').length;

    let jsonBody = null;
    try {
      jsonBody = JSON.parse(bodyText.trim());
    } catch (e) {}

    if (jsonBody && typeof jsonBody === 'object') {
      if (jsonBody.error) {
        return JSON.stringify({ error: true, code: jsonBody.code || "API_ERROR", message: jsonBody.message || "Endpoint returned error JSON" });
      }
      return JSON.stringify({ verified: true, title, is_json: true, data_keys: Object.keys(jsonBody) });
    }

    if (/\\b404\\b|not found|page not found/i.test(title) || /\\b404\\b|not found|page not found/i.test(bodyText.slice(0, 300))) {
      return JSON.stringify({ error: true, code: "NOT_FOUND", message: "Page returned 404 Not Found" });
    }
    if (/access denied|403 forbidden|unauthorized/i.test(title) || /403 forbidden/i.test(bodyText.slice(0, 300))) {
      return JSON.stringify({ error: true, code: "FORBIDDEN", message: "Page returned Access Denied / 403 Forbidden" });
    }

    if (elementsCount < 3 && bodyText.trim().length === 0) {
      return JSON.stringify({ error: true, message: "Page DOM is empty" });
    }

    return JSON.stringify({ verified: true, title, body_len: bodyText.trim().length, elements_count: elementsCount });
  } catch (e) {
    return JSON.stringify({ error: true, message: e.message });
  }
})()
"""
            probe_b64 = base64.b64encode(probe_js.strip().encode("utf-8")).decode("ascii")
            eval_res = run_process(
                [binary, "--config", str(config_path), "--session", session_id, "eval", "-b", probe_b64],
                run_cwd,
                check=False,
                timeout=15,
            )
            if eval_res.returncode == 0 and eval_res.stdout.strip():
                raw_out = eval_res.stdout.strip()
                try:
                    parsed = json.loads(raw_out)
                    if isinstance(parsed, str):
                        parsed = json.loads(parsed)
                except Exception:
                    parsed = None

                if isinstance(parsed, dict):
                    if parsed.get("verified"):
                        return {
                            "verified": True,
                            "status": "BROWSER_DOM_VERIFIED",
                            "message": f"Browser DOM probe succeeded for {target_url} (title: '{parsed.get('title', '')}').",
                        }
                    elif parsed.get("code") in ("FORBIDDEN", "AUTH_EXPIRED"):
                        return {
                            "verified": False,
                            "status": "AUTH_EXPIRED",
                            "message": f"Browser probe failed with auth error: {parsed.get('message')}",
                        }
                    elif parsed.get("code") == "NOT_FOUND":
                        return {
                            "verified": False,
                            "status": "RE_EXPLORATION_REQUIRED",
                            "message": f"Browser probe failed with 404: {parsed.get('message')}",
                        }
                    else:
                        return {
                            "verified": False,
                            "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                            "message": f"Browser DOM probe failed: {parsed.get('message', 'probe failed')}",
                        }

            return {
                "verified": False,
                "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                "message": f"Browser evaluation failed: {(eval_res.stderr or eval_res.stdout).strip()}",
            }
        except Exception as exc:
            return {
                "verified": False,
                "status": "BROWSER_SESSION_REVALIDATION_REQUIRED",
                "message": f"Browser DOM probe encountered exception: {exc}",
            }
        finally:
            try:
                run_process(
                    [binary, "--config", str(config_path), "--session", session_id, "close"],
                    run_cwd,
                    check=False,
                    timeout=10,
                )
            except Exception:
                pass



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

    p_har_start = sub.add_parser("har-start")
    p_har_start.add_argument("--root", default=os.getcwd())
    p_har_start.add_argument("--run-id", required=True)
    p_har_start.add_argument("--target-flow", required=True)
    p_har_start.add_argument("--pre-capture", action="store_true")
    p_har_start.set_defaults(func=har_start)

    p_har_stop = sub.add_parser("har-stop")
    p_har_stop.add_argument("--root", default=os.getcwd())
    p_har_stop.add_argument("--run-id", required=True)
    p_har_stop.add_argument("--har-file", required=True)
    p_har_stop.set_defaults(func=har_stop)

    p_har_analyze = sub.add_parser("har-analyze")
    p_har_analyze.add_argument("--har", required=True)
    p_har_analyze.add_argument("--root", default=os.getcwd())
    p_har_analyze.add_argument("--run-id")
    p_har_analyze.add_argument("--origin")
    p_har_analyze.add_argument("--filter")
    p_har_analyze.set_defaults(func=har_analyze)

    p_har_inspect = sub.add_parser("har-inspect")
    p_har_inspect.add_argument("--har", required=True, help="Path to HAR file")
    p_har_inspect.add_argument("--root", default=os.getcwd())
    p_har_inspect.add_argument("--run-id")
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
    p_ver.add_argument("--root")
    p_ver.add_argument("--run-id")
    p_ver.add_argument("--output-receipt")
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
    p_gen.add_argument("--run-id")
    p_gen.add_argument("--receipt")
    p_gen.add_argument("--receipts-dir")
    p_gen.add_argument("--fresh", action="store_true", default=False, help="Perform clean rebuild instead of refining existing package")
    p_gen.set_defaults(func=generate_skill)

    p_val = sub.add_parser("validate-package")
    p_val.add_argument("--package-dir", required=True)
    p_val.set_defaults(func=validate_package)

    p_test = sub.add_parser("test-skill")
    p_test.add_argument("--package-dir", required=True)
    p_test.add_argument("--base-url")
    p_test.add_argument("--test-cases")
    p_test.set_defaults(func=test_skill)

    p_inst = sub.add_parser("install-skill")
    p_inst.add_argument("--package-dir", required=True)
    p_inst.add_argument("--agent", default="antigravity")
    p_inst.add_argument("--dest")
    p_inst.add_argument("--root", default=os.getcwd())
    p_inst.set_defaults(func=install_skill)

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

    root = getattr(args, "root", None)
    run_id = getattr(args, "run_id", None)
    if root and run_id:
        validate_har_lifecycle(root, run_id, har_path)

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
