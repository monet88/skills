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

## Dependency Guard (Strict)

Ask Impeccable requires the `impeccable` skill/tool to be present in the active agent environment.

Before executing any UI workflow:
1. Check if `impeccable` is available in the agent's installed skills, tools, or commands.
2. If `impeccable` is **missing**:
   - **Halt immediately** and report the missing dependency explicitly:
     `Error: Impeccable dependency is required but not installed in the current environment.`
   - **Do NOT emulate or improvise fallback design rules or Impeccable behaviors.**
   - **Monet setup guidance**:
     - Check if an approved Monet setup capability is discoverable in the environment (e.g. `setup-monet` skill or command).
     - If discoverable: advise the user to run the Monet setup path (e.g. `Run 'setup-monet' or install via 'npx skills add monet88/skills'`).
     - If NOT discoverable: state the missing dependency clearly without inventing an unverified setup command.

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
