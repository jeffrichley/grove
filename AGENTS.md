# Agent Guidance for Grove

Coding agents working in this repository should follow the rules and conventions defined in:

- **`.ai/RULES.md`** — Workflow invariants, quality gates, architecture boundaries, and project-type rules.
- **`docs/concept.md`** — GROVE context system (Grow, Root, Optimize, Verify, Enrich).

Grove-specific conventions (plan-before-code, execute from plan, validate every change, keep changes small) are in `.ai/RULES.md`. Use `src/grove` and the conventions in `.ai/RULES.md` for all implementation work.

For implementation plans, use `.ai/PLANS/<NNN>-<feature>.md` and follow `.ai/REF/plan-authoring.md`.

<!-- grove:tool-hook:codex:codex-agents-shim:start -->
# Grove Managed Codex Shim

Read `.grove/GROVE.md` first. That is the canonical Grove operating guide for this repository.

Then use `.grove/INDEX.md` to decide which scoped rules, commands, and reference docs to load next.

Load `.grove/rules/*`, `.grove/docs/*`, and `.grove/commands/*` only when the current task needs them.
<!-- grove:tool-hook:codex:codex-agents-shim:end -->
