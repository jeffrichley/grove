# Agent Guidance for Grove

Coding agents working in this repository should follow the rules and conventions defined in:

- **`.ai/RULES.md`** — Workflow invariants, quality gates, architecture boundaries, and project-type rules.
- **`docs/concept.md`** — GROVE context system (Grow, Root, Optimize, Verify, Enrich).

Grove-specific conventions (plan-before-code, execute from plan, validate every change, keep changes small) are in `.ai/RULES.md`. There is no separate "Lily" project in this repo; treat any references to `src/lily` or Lily-specific rules in legacy docs as historical and use `src/grove` and Grove conventions instead.

For implementation plans, use `.ai/PLANS/<NNN>-<feature>.md` and follow `.ai/REF/plan-authoring.md`.
