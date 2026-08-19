---
name: ask-impeccable
description: Frontend and UI workflow router. Use when designing, building, critiquing, auditing, polishing, or refactoring user interfaces, web/mobile components, styling, animations, or UX flows. Dispatches UI intents to Impeccable workflows. Also activate when the user explicitly mentions "ask-impeccable" or requests UI/UX guidance.
---

# Ask Impeccable

Frontend and UI workflow router that directs UI/UX tasks to Impeccable workflows.

## When to Use

Activate Ask Impeccable when:
- Designing, building, critiquing, auditing, polishing, or refactoring user interfaces, components, or pages.
- Working on responsive layouts, design tokens, styling, typography, colors, animations, or UX flows.
- The user explicitly invokes `ask-impeccable`, `/ask-impeccable`, or asks for UI/UX guidance.

## Dependency Guard (Recovery-First)

Ask Impeccable requires the `impeccable` skill/tool to be present in the active agent environment.

Before executing any UI workflow:
1. Check whether `impeccable` is available in the agent's installed skills, tools, or commands.
2. If `impeccable` is **missing**:
   - Tell the user exactly what is missing and provide the canonical install command:
     `npx skills add pbakaus/impeccable`
   - If the current environment permits shell execution and skill installation, and the user has not prohibited installs, install it automatically from the project root with the non-interactive form:
     `npx skills add pbakaus/impeccable --skill impeccable -y`
   - If the current agent identifier is known and the Skills CLI supports explicit targeting, add `--agent <current-agent>` to the automatic install command.
   - After the install command succeeds, **re-check** whether `impeccable` is now discoverable in the active environment.
   - If the re-check succeeds, continue the user's original UI workflow in the same turn. Do not make the user repeat the request.
   - If installation succeeds but the current harness does not hot-reload newly installed skills, tell the user that installation succeeded, ask them to reload/restart the harness once, and then resume the original request after reload.
   - If installation is blocked, unavailable, or fails, report the exact command above plus the concrete failure. Stop only because the dependency is still unavailable.
3. **Do NOT emulate, improvise, or fabricate fallback Impeccable behavior while the dependency is unavailable.**

## State Management

- Ask Impeccable maintains **no persistent state** of its own.
- Do not create `.ask-impeccable/` directories or parallel state files in the workspace.
- Rely solely on project files and Impeccable's native mechanisms.

## Workflow Dispatch

When `impeccable` is available, delegate the UI request to the corresponding Impeccable workflow or command.

## Read-Only UI Research Layer

Ask Impeccable includes a built-in read-only UI research retrieval layer powered by BM25 search over approved domain datasets:
- **Domains**: `style`, `color`, `chart`, `landing`, `product`, `ux`, `typography`, `icons`, `react`, `web`, `google-fonts`
- **Stacks**: `react`, `nextjs`, `vue`, `svelte`, `astro`, `swiftui`, `react-native`, `flutter`, `nuxtjs`, `nuxt-ui`, `html-tailwind`, `shadcn`, `jetpack-compose`, `threejs`, `angular`, `laravel`, `javafx`, `wpf`, `winui`, `avalonia`, `uno`, `uwp`
- **Usage**:
  ```bash
  node research/search.mjs "<query>" [--domain <domain>] [--stack <stack>] [--max-results 3] [--json]
  ```
- **Properties**:
  - Zero runtime dependencies (Node.js built-ins only).
  - Purely read-only; performs zero project-file writes or mutations.
  - Informational lookup only; does not generate design systems, overrides, or templates.
