# Operation Capability Exploration

Use this reference during Phase 2 for website operations that may create, update, delete, submit, publish, purchase, or otherwise cause side effects.

## Runtime Boundary

Run every browser command through the current forge run:

```text
python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- <agent-browser-command>
```

Never invoke raw `agent-browser` for forge-controlled exploration. The wrapper owns trusted config and the isolated named session.

## Goal

Capture the intended write request without causing the live operation whenever possible. Prefer a reproducible API path only when its parameters and auth requirements are actually verified. Otherwise preserve a browser-session or DOM implementation.

Classify the result as exactly one of `DIRECT_API_VERIFIED`, `BROWSER_SESSION_API`, `DOM_ONLY`, or `HYBRID`.

## Zero-Side-Effect Verification

For a consequential operation, use the live runtime guidance to execute the equivalent of:

1. Start HAR capture into `.agent-forge/runs/<run-id>/` before the target interaction.
2. Enable browser offline mode.
3. Fill the form or prepare the UI using runtime-resolved targets.
4. Trigger the operation once while offline so request intent is captured but cannot reach the target server.
5. Stop HAR capture to the canonical run-local path.
6. Restore online mode.
7. Immediately leave or neutralize the submission page if retry logic could resend the request.

On the verified agent-browser runtime, the relevant primitives are `network har start`, `set offline on|off`, and `network har stop <path>`. Re-check live core guidance if command spelling differs on the installed version.

Inspect the HAR for method, URL, headers, body shape, and input conditions. Do not expose credential values in user-visible output.

## Live-Submission Boundary

If offline/HAR or another harmless dry-run cannot prove the required request shape, do not silently perform a consequential live action. Explain what evidence is missing and obtain explicit user confirmation before the one live submission needed for verification.

## API Feasibility

A write endpoint is direct only after a real, authorized replay is safe and the request can be parameterized without opaque browser-only state. Dynamic signatures, page-only tokens, or browser-bound credentials imply `BROWSER_SESSION_API` or `HYBRID`; do not keep mutating parameters to force a direct classification.

## DOM Fallback

When the page's own JS must construct the operation, automate the stable controls and let native page logic create credentials/signatures. Prefer semantic locators and stable selectors. Re-snapshot after material UI changes and resolve targets again.

## Enumeration and Multi-Step Forms

Determine how dropdown/radio/search options are populated using network evidence first, then DOM, then visual interaction. Record cascading dependencies between controls. For stepped forms, record the state dependency between steps rather than assuming every field exists at once.

## Ref Discipline

Snapshot refs are ephemeral runtime handles. Never persist a concrete ref into generated operation steps, scripts, manifests, provenance, or examples.

## Evidence Boundary

HARs, raw request bodies, auth evidence, screenshots used for verification, and private generated clients remain under `.agent-forge/`. Report only redacted structural facts outside that boundary.
