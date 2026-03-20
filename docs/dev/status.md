last_updated: 2026-03-20
---

# Development Status

## Current Focus

- No active feature phase is in progress; Plan 006 is complete. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- Next feature plan has not yet been selected. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.

## Recently Completed

- **Plan 006 complete:** `grove remove` and `grove doctor` are now shipped, docs are aligned, pack-owned doctor checks are supported, Codex skill front matter is validated, and final quality/test/coverage/docs/status gates passed. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 006 Phase 5 complete:** packs can now contribute generic doctor checks, the built-in Codex pack ships `skill_front_matter` checks, doctor reports missing/malformed/mis-specified skill front matter, and the built-in Codex skill templates now include valid front matter. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 006 Phase 4 complete:** `grove doctor` now exists with read-only generic diagnostics for manifest health, dependency coherence, managed-file drift, anchor safety, tool-hook targets, and pack-local skills, with healthy repos exiting cleanly and broken repos reporting categorized findings. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 006 Phase 3 complete:** `grove remove <pack> [--root] [--dry-run]` now exists, remove applies ordered delete/rewrite operations, AGENTS managed blocks are removed safely, pack-local skills are deleted when orphaned, and manifest persistence happens after a successful apply path. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 006 Phase 2 complete:** remove planning now blocks `base` and installed dependents, recomputes remaining desired state, and classifies managed files, tool-hook targets, and repo-local Codex skills into delete/rewrite/preserve without mutating the repo. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 006 Phase 1 complete:** typed ownership/report models landed for remove/doctor, doctor-check contribution parsing is normalized in loader coverage, and manifest schema remains v1 because ownership is still derivable from existing provenance surfaces. Source: `.ai/PLANS/006-grove-remove-and-doctor.md`.
- **Plan 004 complete:** CLI/help and error-message polish, install-path confirmation, pack author guide completion, and roadmap/status closure are complete. Source: `.ai/PLANS/004-grove-polish-packaging.md`.
- **Plan 005 Phase 2G (validation and observability):** `grove sync --dry-run` now reports changed anchors with pack/injection provenance, sync paths are project-root-relative, and provenance coverage landed in unit and integration tests. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 complete:** Grove Phase 2 composition, safe sync, generic pack-owned tool integrations, Codex shim generation, Codex skill materialization, and provenance/dry-run observability are all complete. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2F (pack-owned Codex skills materialization):** Codex skill contributions now materialize through the generic integration pipeline into repo-local `.agents/skills`, with built-in `planning-execution` and `memory-writeback` skills and integration coverage for repo-local installs. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2E (generic tool hook pipeline + first Codex integration pack):** Generic `tool_hooks` pipeline landed in core, built-in `codex` integration pack added, repo-root `AGENTS.md` shim generation wired into init/add/sync/TUI apply, and Codex shim tests added. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2D (pack slimming and Phase 2 pack set):** Base pack slimmed to `GROVE.md` + `INDEX.md`; new minimal built-in `memory`, `commands`, `knowledge`, and `project-context` packs added and verified through `init`/`add`. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2C (Grove rendered navigation):** Structured `index_entries`, `INDEX.md` anchor rendering, composer/index renderer integration, and Python pack `rules`/`commands`/`docs` navigation entries. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2B (Grove safe sync):** Managed-region replacement during sync, anchor-based reconstruction when managed markers are missing, user-region preservation, idempotent reruns, and explicit unsafe-reconstruction failure path. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 005 Phase 2A (Grove robust composition):** Anchor markers, managed/user markers, deterministic injection assembly, composition-aware dry-run preview, minimal base `GROVE.md`/`INDEX.md`, Python snippet injections. Source: `.ai/PLANS/005-grove-phase2-composition.md`.
- **Plan 003 (Grove CLI — add, sync, configure / manage mode):** All three phases done. `grove add <pack>`, `grove sync [--root] [--dry-run]`, `grove configure` (init TUI when no manifest, manage TUI when manifest exists), `grove manage` alias; manage dashboard with installed packs, add pack, re-run analysis, full re-setup; integration tests; docs polish. Plan: `.ai/PLANS/003-grove-add-sync-manage-mode.md`.
- **Plan 002 (Grove CLI — TUI + full init flow):** All 9 screens (Welcome → Finish), Apply with conflict choices, manifest save; flag-based init preserved. Plan: `.ai/PLANS/002-grove-cli-tui-init-flow.md`.
- **Grove CLI core engine (001):** `grove init` with Base + Python packs, `.grove/` and manifest; all six phases done. Source: `.ai/PLANS/001-grove-cli-core-engine.md`.

## Diary Log

- 2026-03-20: Plan 006 complete: README/CLI/pack-author docs updated for `remove` and `doctor`, roadmap/status marked done, and final gates passed (`just quality`, `just test`, `just test-cov`, `just docs-check`, `just status-ready`).
- 2026-03-20: Status sync run for `.ai/PLANS/006-grove-remove-and-doctor.md` after Phase 5; current focus advanced to Phase 6 docs/final validation, and docs-check/status pass.
- 2026-03-20: Plan 006 Phase 5 complete: pack-owned doctor checks landed, the Codex pack now validates skill front matter, built-in Codex skills now ship valid front matter, and doctor reports missing/malformed/required-key front-matter failures.
- 2026-03-20: Status sync run for `.ai/PLANS/006-grove-remove-and-doctor.md` after Phase 4; current focus advanced to Phase 5 pack-owned doctor checks and docs-check/status pass.
- 2026-03-20: Plan 006 Phase 4 complete: `grove doctor` landed with generic read-only manifest/dependency/drift/anchor/tool/skill diagnostics, healthy-vs-broken integration coverage, and the first CLI health-report surface; `--json` and `--strict` were deferred.
- 2026-03-20: Status sync run for `.ai/PLANS/006-grove-remove-and-doctor.md` after Phase 3; current focus advanced to Phase 4 doctor core checks, and docs-check/status pass.
- 2026-03-20: Plan 006 Phase 3 complete: `grove remove` CLI landed with dry-run reporting, ordered apply/delete behavior, safe AGENTS managed-block removal, pack-local skill cleanup, and replace-based manifest persistence; `just quality && just test` passed.
- 2026-03-20: Status sync run for `.ai/PLANS/006-grove-remove-and-doctor.md` after Phase 2; current focus advanced to Phase 3 apply-path and CLI work; docs-check and status pass.
- 2026-03-20: Plan 006 Phase 2 complete: remove planning now enforces base/dependent blocking, recomputes remaining desired state, and classifies managed files, AGENTS managed blocks, and repo-local Codex skills into delete/rewrite/preserve with unit and integration coverage.
- 2026-03-20: Status sync run for `.ai/PLANS/006-grove-remove-and-doctor.md` after Phase 1; current focus advanced to Plan 006 Phase 2 remove planning, roadmap updated, and docs-check/status pass.
- 2026-03-20: Plan 006 Phase 1 complete: typed ownership/report models landed for remove/doctor, doctor-check contribution parsing gained loader coverage, manifest schema intentionally remains v1, and `just types && just lint && just test` passed.
- 2026-03-20: Plan 004 completed: CLI help and error wording audited, install path confirmed with `uv pip install .`, pack author guide extended for integration packs/tool hooks, and roadmap/status updated.
- 2026-03-20: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2G; Plan 005 marked complete; docs-check and status pass.
- 2026-03-20: Plan 005 Phase 2G complete: sync dry-run now reports changed anchors plus provenance, project-root-relative output landed, and final gates passed.
- 2026-03-20: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2F; current focus advanced to Phase 2G validation and observability; docs-check and status pass.
- 2026-03-20: Plan 005 Phase 2F complete: Codex skill contributions now materialize into repo-local `.agents/skills` via the generic integration pipeline, Phase 2 validation skills landed, and final gates passed.
- 2026-03-20: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2E; current focus advanced to Phase 2F pack-owned Codex skills materialization; docs-check and status pass.
- 2026-03-20: Plan 005 Phase 2E complete: generic `tool_hooks` pipeline landed, built-in `codex` integration pack added, repo-root `AGENTS.md` shim now updates through init/add/sync/TUI apply, and final gates passed.
- 2026-03-18: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2D; current focus advanced to Phase 2E Codex tool hook outputs; docs-check and status pass.
- 2026-03-18: Plan 005 Phase 2D complete: base pack slimmed to the core anchor infrastructure, minimal `memory`/`commands`/`knowledge`/`project-context` packs landed, and integration coverage now verifies both base-only init and pack add flows.
- 2026-03-18: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2C; current focus advanced to Phase 2D pack slimming and pack-set work; docs-check and status pass.
- 2026-03-18: Plan 005 Phase 2C complete: structured INDEX entry rendering landed, composer now injects rendered navigation blocks into `INDEX.md`, and the Python pack contributes `rules`/`commands`/`docs` navigation entries; quality-check and Phase 2C unit validation pass.
- 2026-03-18: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md` after Phase 2B; current focus advanced to Phase 2C rendered navigation; docs-check and status pass.
- 2026-03-18: Plan 005 Phase 2B complete: `grove sync` now replaces only managed regions, preserves user regions, reconstructs managed blocks under anchors when possible, and fails clearly when reconstruction is unsafe; `just quality && just test` pass.
- 2026-03-18: Status sync run for `.ai/PLANS/005-grove-phase2-composition.md`; roadmap/status advanced to Plan 005, Phase 2A recorded complete, Phase 2B set as current focus; docs-check and status pass.
- 2026-03-18: Plan 005 Phase 2A complete: marker parsing, anchor injection composition, composition-aware dry-run preview, base `GROVE.md`/`INDEX.md` infrastructure, Python snippet injections; quality-check and targeted unit/integration validation pass.
- 2026-03-17: Status sync run for `.ai/PLANS/003-grove-add-sync-manage-mode.md`; canonical status/roadmap confirmed; docs-check and status pass.
- 2026-03-17: Plan 003 complete (Phases 1–3); acceptance criteria and completion checklist marked done; docs polish: roadmap Phase 3 → Done, status updated, README CLI section added.
- 2026-03-17: Plan 003 Phase 3: integration tests (sync reverts file, configure requires TTY); just quality && just test pass.
- 2026-03-17: Plan 003 Phase 2 complete: configure, manage TUI, manage alias, init→configure when manifest exists.
- 2026-03-17: Plan 003 Phase 1 complete: grove sync, grove add (core); sync_managed in core/sync.py; quality and tests pass. Status sync.
- 2026-03-17: Status sync run (plan 002 context); docs already aligned with Phase 2 complete, Phase 3 next.
- 2026-03-17: PRD/docs: init + manage merged into `grove configure` (canonical command; init/manage aliases). Finish screen: next steps = doctor/sync; configure noted for “later.” Status sync run.
- 2026-03-17: Plan 002 (TUI + full init flow) completed; all screens implemented, Apply → Finish; status sync run.
- 2025-03-17: Plan 001 (Grove CLI — Core Engine) completed and finalized. Acceptance criteria and completion checklist updated; status sync run.
- 2026-03-16: Current focus set to Phase 2 (TUI + full init flow) per PRD; Plan 002 (`.ai/PLANS/002-grove-cli-tui-init-flow.md`) created, referencing `.ai/SPECS/001-grove-cli/PRD.md` §12 Phase 2.
