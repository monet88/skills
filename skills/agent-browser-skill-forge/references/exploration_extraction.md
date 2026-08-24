# Extraction Capability Exploration

This reference is used during Phase 2 for extraction capabilities.

## Runtime Boundary

All browser commands must use the current forge run:

```text
python <skill-root>/scripts/forge-runtime.py exec --root "<workspace-root>" --run-id "<run-id>" -- <agent-browser-command>
```

Never invoke raw `agent-browser` for forge-controlled exploration. The wrapper owns trusted config and the isolated named session.

## Goal

Prefer structured network evidence and verified direct replay. Fall back to browser-session network access, then DOM extraction when direct HTTP cannot be reproduced reliably.

Classify the result as exactly one of:
- `DIRECT_API_VERIFIED`
- `BROWSER_SESSION_API`
- `DOM_ONLY`
- `HYBRID`

## Exploration Skeleton

1. Open the target page and wait on a purpose-specific condition from live core guidance.
2. Start HAR before the target interaction when network evidence is required.
3. Exercise the target flow with meaningful input variation where safe.
4. Inspect structured network output and use the returned real request identifier for detail lookup.
5. Treat an observed endpoint as a candidate only; direct replay and predictable variation are required before `DIRECT_API_VERIFIED`.
6. If direct replay depends on browser-only state, preserve `BROWSER_SESSION_API` instead of forcing a false direct classification.
7. If structured network data cannot satisfy the capability, use stable DOM/semantic locators and runtime-resolved refs.
8. For list data, verify pagination produces different records before generation.
9. Determine retrieval methods for meaningful enum/filter controls.

## Ref Discipline

Refs are short-lived live identifiers. Resolve them from a fresh snapshot when needed and never write a concrete ref into reusable strategy artifacts.

## Evidence

HARs and raw evidence belong under `.agent-forge/runs/<run-id>/`. Never copy them into tracked source paths.
