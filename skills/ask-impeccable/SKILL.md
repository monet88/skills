---
name: ask-impeccable
description: Frontend and UI workflow router for Impeccable. Use for planning, building, critiquing, auditing, polishing, or refactoring web/mobile interfaces; design-system setup or extraction; onboarding, UX copy, typography, layout, color, motion, responsive adaptation, accessibility, performance, edge cases, or live browser iteration. Route each UI intent to the matching Impeccable workflow. Also activate when the user explicitly mentions ask-impeccable or requests UI/UX guidance.
---

# Ask Impeccable

Route frontend and UI/UX work to the most specific Impeccable workflow.

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

When `impeccable` is available, route the request to the most specific Impeccable command. If the user explicitly names an Impeccable subcommand, use that command unless it conflicts with an explicit safety or scope constraint.

### Intent Routing

| User intent | Route |
|---|---|
| Build or substantially redesign a UI end-to-end, including visual iteration | `/impeccable craft` |
| Initialize Impeccable project context, PRODUCT.md/DESIGN.md, or live-mode setup | `/impeccable init` |
| Generate or refresh root DESIGN.md from existing project code | `/impeccable document` |
| Extract reusable components, patterns, or tokens into a design system | `/impeccable extract` |
| Plan, shape, or specify UX/UI before implementation | `/impeccable shape` |
| Review hierarchy, clarity, usability, information architecture, or emotional quality | `/impeccable critique` |
| Check accessibility, responsive behavior, performance, or technical UI quality | `/impeccable audit` |
| Run a broad final design-system alignment and shipping-readiness pass | `/impeccable polish` |
| Make a bland, timid, or generic design more expressive | `/impeccable bolder` |
| Tone down an overly loud, dense, or aggressive design | `/impeccable quieter` |
| Remove unnecessary complexity and reduce the interface to its essentials | `/impeccable distill` |
| Harden error states, edge cases, i18n, overflow, and resilience | `/impeccable harden` |
| Improve first-run flows, activation, onboarding, or empty states | `/impeccable onboard` |
| Add or improve purposeful motion and transitions | `/impeccable animate` |
| Improve the color system, contrast strategy, or color usage | `/impeccable colorize` |
| Improve fonts, type scale, hierarchy, rhythm, or typographic details | `/impeccable typeset` |
| Fix layout, spacing, alignment, grids, density, or visual rhythm | `/impeccable layout` |
| Add tasteful micro-interactions, personality, or moments of delight | `/impeccable delight` |
| Add ambitious, technically extraordinary visual effects | `/impeccable overdrive` |
| Improve UX copy, labels, instructions, errors, or interface clarity | `/impeccable clarify` |
| Adapt the interface for mobile, tablet, desktop, or other device contexts | `/impeccable adapt` |
| Improve frontend runtime/loading/render performance | `/impeccable optimize` |
| Iterate on visual variants directly in a browser/live visual workflow | `/impeccable live` |

### Routing Precedence

Apply these rules when multiple routes appear plausible:
1. **Explicit command wins.** Honor an explicitly named Impeccable subcommand.
2. **Specific transformation beats generic polish.** Prefer `typeset`, `layout`, `colorize`, `animate`, `adapt`, `optimize`, `clarify`, `harden`, `onboard`, `bolder`, `quieter`, `distill`, `delight`, or `overdrive` over `polish` when the request names that specific problem.
3. **Technical inspection beats subjective review.** Route accessibility, performance, and responsive-quality checks to `audit`; route hierarchy, clarity, usability, and design-quality review to `critique`.
4. **Plan versus implement.** Route planning-only requests to `shape`; route requests to build or materially redesign the interface to `craft`. Do not run a separate `shape` first when `craft` already covers the requested shape-then-build flow unless the user asks for a planning checkpoint.
5. **Project/design-system operations are deliberate.** Use `init`, `document`, or `extract` only when the user requests or clearly implies that project-level/design-system operation.
6. **Live mode is explicit.** Use `live` only when the user asks for browser/live visual iteration or when that interaction mode is clearly required.
7. **Multi-part requests may chain.** Use only the commands needed for distinct requested intents; run critique/audit before corrective transformations when diagnosis is required, and use `polish` last for a broad finishing pass.

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
