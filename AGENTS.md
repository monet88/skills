# AGENTS.md

## Overview
This repository (`monet88/skills`) is a public library of ChatGPT and AI agent skills.

## Canonical Install UX
Skills in this repository are installed via:
```bash
npx skills@latest add monet88/skills
```

## Workflow & Guidelines
- **Issue Tracking**: GitHub Issues in `monet88/skills` serve as the implementation and specification tracker.
- **Tracker Source of Truth**: See [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md) for tracker configuration and workflow details.
- **Workflow Labels**: See [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md) for label mapping and lifecycle definitions.
- **Research Materials**: The `.upstream` directory is strictly for local research/reference and must never be committed.
- **Preparation**: Agents must read this `AGENTS.md` before performing repository work.
- **No Direct Vendoring**: Do not vendor upstream skills directly into the repository unless an explicit design decision says so.
- **Package Validation**: Always validate skill packages and metadata before claiming task completion.
