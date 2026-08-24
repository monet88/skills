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

    p_har = sub.add_parser("har-inspect")
    p_har.add_argument("--har", required=True, help="Path to HAR file")
    p_har.add_argument("--methods", default=None, help="Comma-separated HTTP methods to include (default: all)")
    p_har.set_defaults(func=har_inspect)
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
