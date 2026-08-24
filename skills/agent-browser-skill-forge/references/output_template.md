# Generated Skill Output Contract

Use this reference during Phase 3. Generated output remains private under `.agent-forge/output/<skill-name>/` until the user explicitly exports it.

## Package Shape

Each generated capability package must contain a `SKILL.md` entrypoint plus only the scripts, references, client files, manifests, and provenance required by the verified implementation.

The generated Skill is the primary public interface. It must declare:
- capability purpose and inputs/outputs;
- actual classification: `DIRECT_API_VERIFIED`, `BROWSER_SESSION_API`, `DOM_ONLY`, or `HYBRID`;
- prerequisites;
- executable command templates;
- quantifiable success criteria;
- real known limitations;
- deterministic recovery/revalidation behavior.

## Reusable Strategy Rules

- Do not include task-specific usernames, search terms, one-off URLs, secret values, or raw capture data.
- Do not persist concrete snapshot refs. Browser-dependent paths must resolve targets again at execution time.
- Do not label an observed endpoint as direct unless direct replay plus meaningful parameter variation passed.
- Keep browser dependency only for classifications that actually require browser/session state.
- For `DIRECT_API_VERIFIED`, the steady-state runtime must be usable without launching agent-browser.

## Browser-Side JavaScript

When a generated browser-dependent script emits JavaScript, make the Python file assemble only browser-side JS and business parameters. The canonical cross-shell execution form is:

```text
python scripts/<feature>.py <args> | agent-browser eval --stdin
```

Generated JS must return a defined error envelope for expected structural failures instead of crashing.
