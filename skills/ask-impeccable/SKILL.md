---
name: ask-impeccable
description: Coordinator for Impeccable UI workflows executed inside coding workers for frontend interfaces. Use when the user invokes ask-impeccable or wants UI/UX work delegated through upstream /impeccable commands. Start a new coordinated workflow with /impeccable init unless the user explicitly skips it. Prefer batching a coherent serial command chain in one worker prompt/session when the commands can run without a decision boundary; split only when user input, failure, scope change, independent review, or orchestration policy requires it. Never replace commands with coordinator-authored UI briefs or coordinator-side design work.
---

# Ask Impeccable

Act as the coordinator for upstream Impeccable. The coding worker invokes the actual `/impeccable ...` commands and owns the UI analysis or edits produced by them.

## Hard invariants

1. **Init first.** The first command in a new Ask Impeccable workflow is `/impeccable init`, with no target argument, unless the user explicitly says to skip init.
2. **Native commands only.** Put the exact `/impeccable ...` invocations in the worker prompt. Do not paraphrase them into a design brief, audit checklist, or manual implementation plan.
3. **Batch when safe.** Prefer one worker Task/Dispatch/session for a coherent command chain that can run serially in the same context.
4. **Serial inside the batch.** The worker must let each command finish before invoking the next command. Never run overlapping mutating Impeccable commands concurrently.
5. **Split only at a real boundary.** Start a fresh Task/session only when a command needs user input or coordinator choice before continuing, fails, materially changes scope, requires independent review/fresh context, or the active orchestration policy requires separation.
6. **Coordinator does not design.** Do not perform coordinator-side UI research, critique, audit, styling, or product-file edits. Express UI work through Impeccable commands.
7. **Use native state only.** Do not create `.ask-impeccable/` state. Rely on Impeccable artifacts, repository state, and orchestration state.

## Dependency and transport

- The target worker environment must expose the upstream `impeccable` skill before dispatch.
- Prefer the upstream installer from the project root when installation is needed: `npx impeccable install`. Resolve provider/scope flags from the live CLI instead of guessing.
- After install/update, re-check that the worker can discover Impeccable. If the harness requires reload, use a fresh worker after reload.
- Never fabricate Impeccable behavior while the dependency is unavailable.
- For supervised AGY work on a local repository, invoke the installed `orca-orchestrator` Skill and follow its current AGY policy, lifecycle, delivery marker, WIP safety, and completion rules.
- If the user names another worker, use that worker through the appropriate current orchestration path while preserving this skill's command-batching rules.

## Coordinator workflow

### 1. Build the command queue

Translate the user's UI goal only into upstream Impeccable commands, not into substitute design instructions.

- Begin with `/impeccable init` unless explicitly skipped.
- Preserve any commands the user explicitly named and their requested order.
- For a broad goal, choose commands from the routing table below. Batch commands whose order is already known; defer commands whose choice depends on earlier findings.
- Keep the target concise and concrete, such as `dashboard`, `settings`, `checkout`, `landing`, or `the campaign table`.

Example of a safe known queue:

```text
/impeccable init
/impeccable audit dashboard
/impeccable critique dashboard
/impeccable optimize dashboard
/impeccable polish dashboard
```

### 2. Dispatch the batch

When the known queue can run coherently in one context, create one worker Task/Dispatch/session and include the commands verbatim in order.

The worker task should stay minimal: exact command lines, repository/worktree scope, lifecycle marker, and safety constraints required by the active orchestration skill. Do not add coordinator-authored UI requirements that compete with Impeccable.

Use a task shape like:

```text
Run these Impeccable commands from the project root, strictly in order:
/impeccable init
/impeccable audit dashboard
/impeccable critique dashboard
/impeccable optimize dashboard
/impeccable polish dashboard

Let each command complete before starting the next.
If a command needs user/coordinator input, fails, or makes the remaining queue invalid, stop at that boundary and use the orchestration ask/escalation path instead of guessing.
Preserve existing WIP and repository instructions. Report structured completion with evidence for each command.
```

Do not create a new worker merely because one command ended if the next queued command is already known and can safely continue in the same session.

### 3. Handle boundaries

A boundary interrupts the current command queue. Treat these as boundaries:

- Impeccable asks for product facts, approval, or another user decision before later commands can be correct.
- A command fails or its required output is incomplete.
- The result materially changes the target or makes the remaining queued commands inappropriate.
- The next step is an independent review that should not inherit the implementer's context.
- The active orchestration policy explicitly requires a fresh worker/session.

At a boundary, settle or pause the current lifecycle as appropriate, resolve the question/failure, then create a fresh Task/session only if needed. Do not blindly continue the stale queue.

### 4. Verify completion

When the batch finishes:

1. Accept only the matching structured worker completion required by the active orchestration policy.
2. Verify repository/artifact state independently when the workflow requires it.
3. Confirm which `/impeccable ...` commands actually ran and which were skipped or interrupted.
4. If more UI work remains, either dispatch another safe batch or a single command based on the new evidence.

## Command routing

Honor an explicitly named command. Otherwise select the command or known serial chain that best matches the requested work.

| Intent | Impeccable command |
|---|---|
| Capture or refresh durable product context | `/impeccable init` |
| Plan UX/UI before implementation | `/impeccable shape <target>` |
| Record the incumbent design system | `/impeccable document` |
| Extract reusable tokens/components | `/impeccable extract <target>` |
| UX/hierarchy/clarity review | `/impeccable critique <target>` |
| Accessibility/performance/responsive audit | `/impeccable audit <target>` |
| Final quality/shipping pass | `/impeccable polish <target>` |
| Make a bland design more expressive | `/impeccable bolder <target>` |
| Tone down an aggressive design | `/impeccable quieter <target>` |
| Remove unnecessary complexity | `/impeccable distill <target>` |
| Harden errors, i18n, overflow, edge cases | `/impeccable harden <target>` |
| Improve first-run/empty/activation flows | `/impeccable onboard <target>` |
| Add purposeful motion | `/impeccable animate <target>` |
| Improve strategic color usage | `/impeccable colorize <target>` |
| Improve typography | `/impeccable typeset <target>` |
| Fix spacing/layout/rhythm | `/impeccable layout <target>` |
| Add tasteful personality | `/impeccable delight <target>` |
| Add technically ambitious effects | `/impeccable overdrive <target>` |
| Improve UX copy and labels | `/impeccable clarify <target>` |
| Adapt to device/screen contexts | `/impeccable adapt <target>` |
| Diagnose and fix UI performance | `/impeccable optimize <target>` |
| Iterate visually in the browser | `/impeccable live` |
| User explicitly asks for deprecated craft alias | `/impeccable craft <target>` |

`craft` is a deprecated upstream alias for ordinary new-work behavior. Do not make it the default for every redesign. For direct new-work language that does not map cleanly to a named command, the worker may invoke `/impeccable <description>` after init.

## Sequencing guidance

- **Known chain:** batch it in one prompt/session and execute strictly in order.
- **Finding-dependent chain:** batch only the known prefix, then stop and choose the next command from evidence.
- **User explicitly names several commands:** preserve their order and batch them unless a real boundary requires a split.
- **Command recommends another command:** continue in the same session only when the recommendation is unambiguous and does not require coordinator/user judgment; otherwise stop at the boundary.
- **Command asks a question:** use orchestration ask/reply; after the answer, the same worker may continue the remaining batch if still valid.
- **Command fails:** stop the batch. Diagnose before retrying; do not skip ahead.

## Forbidden patterns

- Do not replace `/impeccable audit dashboard` with a coordinator-authored accessibility/performance checklist.
- Do not write a detailed UI redesign brief and tell the worker to "use Impeccable somehow".
- Do not force one-command-per-session churn when a serial command batch can run coherently in one worker context.
- Do not parallelize mutating commands over the same UI scope.
- Do not invent a next command when the previous result creates a material decision boundary.

## Upstream contract

Impeccable exposes one skill with 23 named commands plus direct-description usage. Start new project work with `/impeccable init`; later commands accept their own optional targets, for example `/impeccable audit blog`, `/impeccable critique landing`, `/impeccable polish settings`, and `/impeccable harden checkout`.
