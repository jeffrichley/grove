# Feature: Grove — Phase 2 Robust Composition, Safe Sync, Tool Hooks

**Source:** Implements Phase 2 of [.ai/SPECS/002-grove-phase2-composition/PRD.md](../SPECS/002-grove-phase2-composition/PRD.md). Product authority: that PRD. No doctor stub—doctor is post-MVP when it has real behavior.

---

## Feature Description

Phase 2 turns Grove from a “render templates into whole files” system into a **composable document system** with:

1. **Anchored injection**: packs can inject snippets into stable anchors inside shared files like `.grove/GROVE.md` and `.grove/INDEX.md`.
2. **Anchor-owned sync + user preservation**: `grove sync` rebuilds the full body of declared `grove:anchor:*` regions and preserves explicit `grove:user:*` regions, with deterministic ordering and conflict detection for injections.
3. **Minimal base pack**: base installs lean `.grove/GROVE.md` + `.grove/INDEX.md` + scoped anchor targets, designed as infrastructure that packs extend.
4. **Structured navigation & commands**: pack-provided guidance renders into `.grove/INDEX.md` and `.grove/commands/*` (Markdown rendered from structured sources).
5. **Generic tool hook pipeline + pack-owned integrations**:
   - Grove core provides a generic way to discover, order, render, and apply pack-contributed tool hooks.
   - Tool-specific integrations such as Codex, Cursor, and Claude Code are owned by separate packs rather than hard-coded into core.
   - The first shipped integration is a Codex pack that generates/updates repo-root `AGENTS.md` as a **thin shim** and only manages its shim block (append/update; preserve user content if `AGENTS.md` already exists).
   - Actual Codex skill bodies are **materialized into Codex’s configured skills directory** as part of Grove install/sync. Grove must not store skill bodies under `.grove/`.
6. **Progressive disclosure model** for Codex context constraints:
   - Tier 1: `AGENTS.md` + `.grove/GROVE.md` (extremely small).
   - Tier 2: `INDEX.md` + `rules/*` + `commands/*`.
   - Tier 3: `docs/*` + `knowledge/*` + `memory/*`.
7. **Execution is enforced by skills**:
   - Any behavior that must reliably happen during execution is encoded as a Codex skill (not only prose in Grove).

---

## Out of Scope

- Community marketplace / remote pack fetching.
- Full implementation of every external tool integration in this phase. The pipeline is generic, but Codex is the first required integration.
- Machine-readable `discovery.toml` for agent querying (navigation is rendered into Markdown).
- Arbitrary file patching; only anchored injection + anchor-region sync.

---

## Plan Patch - 2026-03-18

Architecture direction is revised as follows:

- `grove:anchor:*` regions are the Grove-owned rewrite boundary. Sync rebuilds the full body of each matched anchor region from current contributions.
- `grove:user:*` regions remain the only user-owned preserved regions. Sync must never rewrite their bodies.
- `grove:managed:*` markers are removed from the Phase 2 design for now.
- Injection routing is **anchor-first**:
  - `anchor` is required
  - `target` is optional and only narrows where an injection applies
  - if `target` is omitted, Grove injects into every file that exposes that anchor
- Injection payload may come from either:
  - `source` (template/file-backed content), or
  - inline `content` in the manifest
- Core composition/sync logic must remain generic and must not encode file-specific behavior for `INDEX.md`, `GROVE.md`, or other special files.

This plan patch supersedes earlier text that required `grove:managed:*` markers or introduced `INDEX.md`-specific rendering behavior.

## Plan Patch - 2026-03-20

Tool integration direction is revised as follows:

- Grove core must implement a **generic tool hook pipeline**, not a Codex-only hook path.
- Tool-specific integrations are **pack-owned**:
  - a `codex` integration pack owns Codex shim/skill outputs
  - a `cursor` integration pack owns Cursor-native outputs
  - a `claude-code` integration pack owns Claude Code-native outputs
- Core is responsible for:
  - discovering selected-pack hook contributions
  - ordering and rendering them
  - applying them with the correct write/update strategy
- Core must not encode one-off helper flows such as `ensure_codex_agents_shim(...)` as the primary architecture.
- Phase 2 scope still ships Codex first, but the implementation must leave room for additional integration packs without revisiting core design.

This plan patch supersedes earlier text in this plan that framed Phase 2E as a Codex-only hook implementation in core.

---

## User Story

As a developer adopting Grove,
I want packs to safely extend shared GROVE documents (without destroying user edits)
So that `grove init` / `grove sync` produce reliable context for AI coding tools.

As a pack author,
I want to declare injections and tool hook outputs via `pack.toml`
So that I can extend GROVE without modifying core code.

As a Codex user,
I want a repo-root `AGENTS.md` shim and Codex skills installed automatically
So that Codex uses Grove as the canonical instruction system.

---

## Feature Metadata

**Feature Type**: Enhancement + Architectural refactor (composition/sync engine upgrade + new pack contributions)

**Estimated Complexity**: High

**Primary Systems Affected**:
- `src/grove/core/composer.py`, `src/grove/core/file_ops.py`, `src/grove/core/sync.py`
- `src/grove/core/models.py` (compose/sync spec models)
- `src/grove/packs/loader.py` and builtins pack manifests/templates
- TUI preview/conflicts (indirect; plan must ensure it keeps working)
- Integration tests around `grove sync` behavior

**Dependencies**: Existing Python runtime + current test toolchain. No new runtime dependencies required beyond current stack (Jinja2, Pydantic, Textual, Typer).

---

## Traceability Mapping

- PRD Phase: Phase 2 (Robust Composition + Safe Sync + Tool Hooks)
- Roadmap: To be added in `docs/dev/roadmap.md` when this plan starts.
- Debt items: None. `No SI/DEBT mapping for this feature.`

---

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/005-grove-phase2-composition.md`
- Branch: `feat/005-grove-phase2-composition`

Commands (executable as written):

```bash
PLAN_FILE=".ai/PLANS/005-grove-phase2-composition.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (read before implementing)

- `src/grove/core/composer.py` (lines 22-69) — current compose only renders `contributes.templates`; no injection/composition stage.
- `src/grove/core/file_ops.py` (lines 63-164, esp. `preview()`, `apply()`) — apply writes whole files; manifest tracks `generated_files`.
- `src/grove/core/sync.py` (lines 70-148, esp. `sync_managed()`, `run_sync()`) — sync currently re-renders whole files in `manifest.generated_files` set.
- `src/grove/core/models.py`
  - `PackManifest` (lines 12-33) — `contributes` is currently untyped dict; extensions will parse new contribution shapes.
  - `PlannedFile` / `InstallPlan` (lines 70-97) — planned files have `managed: bool` but current apply/sync ignores `managed` for manifest selection.
  - `ManifestState` / `GeneratedFileRecord` (lines 159-178, 130-135) — manifests currently track generated file paths but not managed-vs-seeded ownership per file (we will interpret `managed` via selection rules rather than add a new schema unless required).
- `src/grove/packs/loader.py` (lines 34-140, esp. `_parse_pack_toml()`, `_get_contributes()`) — contributes normalization and pack manifest parsing.
- `src/grove/tui/screens/pack_config.py` (lines 51-82, `_collect_setup_questions()`) — only reads `contributes.setup_questions`; new contributes keys must not break this.
- `src/grove/tui/screens/components_preview.py` (lines 23-49, `_ensure_plan()`) — relies on `compose()` output; injection/composition must keep producing a valid install plan for preview.
- `src/grove/cli/app.py`
  - init command (`init`) flag-based apply + error handling (lines 189-244) — Phase 2 must preserve CLI behavior.
  - `sync` command path (`sync`) (lines 246-291) — sync uses `run_sync()`.

### Relevant Tests (read before implementing)

- `tests/unit/core/test_file_ops.py` — apply/preview semantics currently assume whole-file templates.
- `tests/integration/test_add_sync_configure.py`
  - `test_sync_reverts_modified_managed_file` (lines ~129-145) — currently asserts whole-file overwrite; will need to match managed-region sync behavior.

### New Files to Create (expected)

This plan expects new modules to keep complexity contained:

- `src/grove/core/markers.py` — marker constants + parsing helpers (anchor/managed/user markers).
- `src/grove/core/injections.py` — injection specs + anchor injection algorithm + ordering + provenance mapping.
- `src/grove/core/index_render.py` — rendering of index/commands/navigation sections from pack contributions.
- `src/grove/core/tool_hooks.py` — generic tool hook pipeline, write strategies, and skill materialization helpers used by integration packs.
- `tests/unit/core/test_injections.py` — anchor parsing and managed-block replacement unit tests.
- `tests/unit/core/test_markers.py` — marker parsing edge cases.

### Relevant Documentation (read before implementing)

- [.ai/SPECS/002-grove-phase2-composition/PRD.md](../SPECS/002-grove-phase2-composition/PRD.md)
- [.ai/RULES.md](../RULES.md) — plan-before-code and required quality gates (`just quality && just test`)

---

## IMPLEMENTATION PLAN

### Phase 2A: Composition engine (anchors + injections + deterministic assembly)

**Intent Lock**

- **Source of truth:** PRD §4-§6 and §12 Phase 2A
- **Must:**
  - Parse `contributes.injections` from pack manifests.
  - Define and validate anchor marker pairs in target files (base-authored).
  - Render injection payload from either `source` templates or inline `content`, with strict Jinja2 variables preserved for templated sources.
  - Produce anchor-owned composed bodies using:
    - anchor markers: `<!-- grove:anchor:<name>:start -->` / `<!-- grove:anchor:<name>:end -->`
    - user markers: `<!-- grove:user:<region-id>:start -->` / `<!-- grove:user:<region-id>:end -->`
  - Deterministic ordering: injection.order ascending, tie-break by injection.id.
  - Conflict detection:
    - duplicate injection `id`
    - missing target file anchors
    - invalid injection payload definition
- **Must Not:**
  - Do arbitrary patching of non-declared regions.
  - Render markers incorrectly (markers must remain comments, stable strings).
- **Acceptance gates:**
  - Unit tests pass for anchor parsing + injection placement.
  - `grove init --dry-run` prints an install plan that includes composition-ready outputs.

**Tasks:**

- [x] **CREATE** `src/grove/core/markers.py`
  - implement marker regex/parsers and helper functions:
    - find_anchor_ranges(content) by anchor name
    - find_managed_blocks(content) by injection id
    - find_user_regions(content) by region id
  - VALIDATE with unit tests: marker start/end pairing errors.
- [x] **CREATE** `src/grove/core/injections.py`
  - **IMPLEMENT** injection ordering and composition algorithm:
    - insert rendered content into correct anchor range
    - validate anchors exist before injection
  - **IMPLEMENT** deterministic output for same inputs (idempotency).
  - VALIDATE: unit tests comparing expected string output with fixture inputs.
- [x] **UPDATE** `src/grove/core/models.py`
  - extend internal/compose models (without breaking existing schema):
    - `InjectionSpec` (id, anchor, optional target, order, optional source, optional content)
  - update `PlannedFile` / `InstallPlan` usage to allow “composition-aware” outputs for files that participate in injections.
- [x] **UPDATE** `src/grove/core/composer.py`
  - **IMPLEMENT** parsing of `pack.contributes["injections"]`
  - for each selected pack, collect injections and group them by anchor, with optional target narrowing.
  - output a compose result that can:
    - produce base file content with anchor bodies rebuilt for init/apply
    - provide a mapping of anchor bodies to be replaced during sync
- [x] **UPDATE** base pack templates in `src/grove/packs/builtins/base/`
  - **RENDER** minimal `.grove/GROVE.md` content with anchor + injection targets and user regions.
  - **CREATE/ADD** `.grove/INDEX.md` template with anchors for rules/commands/tools/docs.
  - ensure base pack defines only infrastructure; move opinionated content to capability packs.
- [x] **UPDATE** Python pack contribution(s)
  - **MIGRATE** from whole-file `rules/python.md.j2` templates (if needed) to injections or to managed blocks inside `.grove/rules/python.md` sections with anchors.
- [x] **UPDATE** preview/conflicts UI to reflect new composition outputs (if needed)
  - ensure `compose()` still returns a plan that components preview can display.

**Validation and gates**

- [x] `uv run pytest -n auto tests/unit/core/test_file_ops.py tests/unit/core/test_injections.py tests/unit/core/test_markers.py`
- [x] `just quality-check` (format + lint + types + docs-check as applicable)

---

### Phase 2B: Safe sync (anchor-region replacement + user preservation)

**Intent Lock**

- **Source of truth:** PRD §12 Phase 2B; marker contract rules
- **Must:**
  - Replace the full body of matched anchor regions:
    - `<!-- grove:anchor:<name>:start -->` .. `<!-- grove:anchor:<name>:end -->`
  - Preserve user regions:
    - `<!-- grove:user:<region-id>:start -->` .. `<!-- grove:user:<region-id>:end -->` untouched
  - Idempotency:
    - running `grove sync` twice yields no further diffs
  - Robustness:
    - if a file exposes required anchors, sync must rebuild those anchor bodies safely even when prior generated content is stale
    - if required anchors are missing from an existing file, sync must fail with a clear error instead of overwriting blindly
- **Must Not:**
  - Overwrite user content outside user markers.
  - Add/remove generated content outside anchor zones.
- **Acceptance gates:**
  - Integration tests updated and passing, especially sync behavior around GROVE.md.
  - Sync dry-run does not write.

**Tasks:**

- [x] **UPDATE** `src/grove/core/sync.py`
  - implement anchor-region sync:
    - load existing file content
    - compute desired anchor body content from current packs/profile
    - replace anchor bodies only
  - for files without required anchors, fail clearly unless the plan defines an explicit migration path.
- [x] **UPDATE** `src/grove/core/file_ops.py`
  - adjust `apply()` and manifest tracking so `managed` flag is respected for sync membership (if introduced).
  - ensure dry-run and collision strategies remain correct for whole-file writes during init.
- [x] **UPDATE** integration tests:
  - adjust `tests/integration/test_add_sync_configure.py::test_sync_reverts_modified_managed_file`
    - new assertion: anchor body re-render occurs, user regions preserved, and stale generated anchor content is reconstructed if possible.
- [x] **ADD** new integration tests for:
  - user region preservation
  - anchor body replacement without touching user blocks
  - idempotency (hash or exact string equality on second sync)

**Validation and gates**

- [x] `uv run pytest -n auto tests/integration/test_add_sync_configure.py -k sync`
- [x] `just quality && just test`

---

### Phase 2C: Rendered navigation (INDEX + “when to use” guidance)

**Intent Lock**

- **Source of truth:** PRD §4 Rendered navigation + Phase 2C
- **Must:**
  - `.grove/INDEX.md` exists after init.
  - Packs can contribute navigation content through the generic injection system into INDEX anchors such as:
    - rules
    - commands
    - tools
    - docs
  - The base file remains tiny; heavy docs stay in Tier 3.
- **Must Not:**
  - Introduce file-specific core logic for `INDEX.md`.
  - Introduce agent-required machine-readable `discovery.toml`.
- **Acceptance gates:**
  - Human-readable checks:
    - `GROVE.md` stays short
    - `INDEX.md` lists relevant categories and links/files
  - Snapshot-style unit tests (string contains) for key anchors.
  - Required validation commands:
    - `uv run pytest -n auto tests/unit/core/test_index_render.py tests/unit/core/test_markers.py`

**Tasks:**

- [x] **UPDATE** base pack templates to include `.grove/INDEX.md` anchors.
- [x] **UPDATE** composer/index renderer to:
  - parse `contributes.index_entries` using this minimal schema:
    - `[[contributes.index_entries]]`
      - `id` (string, unique within the pack set; used for ordering/provenance)
      - `section` (string enum: `rules`, `commands`, `tools`, `docs`)
      - `title` (string, heading text)
      - `summary` (string, 1-paragraph or bullet summary)
      - `pointers` (list of strings, absolute-to-`.grove/` file paths to link/point at, e.g. `.grove/rules/python.md`)
      - `when_to_use` (string, short guidance sentence)
      - `order` (integer, default 0)
    - Rendering responsibility:
      - render a stable markdown block that can be inserted under the matching INDEX anchor for `section`
      - do not add new anchors beyond those owned by base pack
  - render consistent markdown blocks into the INDEX anchors
- [x] **UPDATE** Python pack to contribute index entries for Tier 2 rules/docs/commands.
- [x] **ADD** unit tests for index rendering and anchor-based insertion ordering.

---

### Phase 2D: Pack slimming and Phase 2 pack set (Base minimal + new capability packs)

**Intent Lock**

- **Source of truth:** PRD Phase 2D + pack list
- **Must:**
  - Base pack becomes minimal infrastructure (GROVE + INDEX + anchor targets).
  - Add (at minimum):
    - `memory` pack (Tier 3 knowledge) with user-write semantics via `grove:user` markers inside generated files (sync preserves).
    - `commands` pack generating `.grove/commands/*` from structured sources defined by the system.
    - `knowledge` pack (library/repo best practices) rendered as Tier 3 reference docs.
    - `project-context` pack scaffolding (Tier 3 project goals/scope/architecture).
  - Keep python pack working with new composition system.
- **Must Not:**
  - Make base pack opinionated for languages or workflows.
- **Acceptance gates:**
  - `grove init` with selected packs produces expected directory structure and core docs.
  - Required validation commands:
    - `uv run pytest -n auto tests/integration/test_phase2_base_pack_slimming.py`

**Tasks:**

- [x] **UPDATE** `src/grove/packs/builtins/base/pack.toml`:
  - remove old templates (`plans/`, `handoffs/`, etc.) from base Phase 2 scope unless required by compatibility.
- [x] **CREATE** builtins pack directories and `pack.toml` for:
  - `memory`, `commands`, `knowledge`, `project-context` (plus optional planning-execution and self-upgrade).
- [x] **ADD** required templates for each pack:
  - injection-targeted Markdown templates
  - Tier placement via anchors and user regions
- [x] **ADD** integration test `tests/integration/test_phase2_base_pack_slimming.py`:
  - verify minimal base produces only the Phase 2 base infrastructure files and the selected pack outputs
- [x] VALIDATE via end-to-end integration test (init produces expected files).

---

### Phase 2E: Generic tool hook pipeline + first Codex integration pack

**Intent Lock**

- **Source of truth:** PRD §4 Tool hooks + Phase 2E + caveats
- **Must:**
  - Core provides a generic pipeline for pack-contributed `tool_hooks`.
  - Tool-specific integrations are pack-owned; Phase 2 ships a Codex integration pack first.
  - The Codex integration pack generates repo-root `AGENTS.md` (append/update only).
  - If `AGENTS.md` already exists, Grove only manages a dedicated shim block and preserves other content.
  - The Codex shim block points to:
    - `.grove/GROVE.md`
    - `.grove/INDEX.md`
    - (optionally) `.grove/rules/*`, `.grove/docs/*`, `.grove/commands/*`
- **Must Not:**
  - Hard-code Codex-specific orchestration as the primary core architecture.
  - Prevent future integration packs from targeting other tool-native paths.
- **Acceptance gates:**
  - Integration test:
    - init in repo with pre-existing `AGENTS.md` preserves user content outside managed shim block.
  - Unit coverage verifies generic hook collection/render/apply behavior independent of Codex-specific paths.
  - Required validation commands:
    - `uv run pytest -n auto tests/integration/test_phase2_codex_agents_shim.py -k shim`

**Tasks:**

- [x] **CREATE** `src/grove/core/tool_hooks.py` with:
  - generic hook collection/render/apply entrypoints
  - write/update strategies keyed by `hook_type`
  - no Codex-only orchestration path as the primary abstraction
- [x] **UPDATE** pack manifest parsing/models to support generic integration-pack hook declarations:
  - `[[contributes.tool_hooks]]` with fields such as:
    - `tool`
    - `hook_type`
    - `target`
    - `source` or inline `content`
    - `order`
- [x] **CREATE** a built-in Codex integration pack that contributes:
  - the repo-root `AGENTS.md` shim hook
  - any Codex-specific metadata needed by later skill materialization
- [x] **UPDATE** CLI flow:
  - call tool hook generation after:
    - flag-based init (`grove init --pack ...`)
    - and after TUI apply + manifest save
  - call tool hook generation during `grove sync` (idempotent).
- [x] **ADD** unit tests for generic hook planning/application behavior.
- [x] **ADD** integration test for append/update behavior.
  - **ADD** integration test `tests/integration/test_phase2_codex_agents_shim.py` with:
    - initial pre-existing `AGENTS.md` with user content
    - run `grove init` or `grove sync`
    - assert managed shim block updated, user content preserved

---

### Phase 2F: Pack-owned Codex skills materialization on the generic integration pipeline

**Intent Lock**

- **Source of truth:** PRD §4 Skills and codex + enforcement rule + automatic materialization
- **Must:**
  - Actual Codex skill bodies are installed into the Codex skills directory, not stored under `.grove/`.
  - Codex skill materialization is owned by the Codex integration pack and executed through the generic tool hook/integration pipeline.
  - Grove materializes Codex skill bodies automatically during install/sync (no `grove install-skills` command).
  - In tests, installation targets a temp Codex home via env var (e.g. `CODEX_HOME`).
- **Must Not:**
  - Include skill bodies in `.grove/`.
  - Depend on global user environment beyond standard destination paths and env overrides for tests.
  - Treat Codex skill handling as a one-off code path disconnected from the pack/integration model.
- **Acceptance gates:**
  - Integration test verifies:
    - `CODEX_HOME` set to tmp
    - skill directories are created under `CODEX_HOME/skills/...`
    - each skill contains `SKILL.md`
  - Required validation commands:
    - `uv run pytest -n auto tests/integration/test_phase2_codex_skills_materialization.py -k skills`

**Tasks:**

- [ ] **CREATE** a pack-owned Codex skill contribution shape:
  - parse it from the Codex integration pack manifest
  - map each skill to:
    - destination folder path in Codex skills directory
    - source templates inside pack assets
- [ ] **IMPLEMENT** skill materialization in `tool_hooks.py`:
  - render skill `SKILL.md` from integration-pack templates
  - write into Codex skills destination
  - make idempotent (managed-region semantics as needed for future updates)
- [ ] **ADD** minimal planning-execution skill and memory skill (as Phase 2 validation):
  - skills enforce execution steps (subagent delegation heuristics, memory writeback).

- [ ] **ADD** integration test `tests/integration/test_phase2_codex_skills_materialization.py`:
  - set `CODEX_HOME` to tmp
  - run `grove init` (or `grove sync`)
  - assert `CODEX_HOME/skills/**/SKILL.md` exists for the expected Phase 2 skills

---

### Phase 2G: Validation and observability (diff/dry-run + provenance)

**Intent Lock**

- **Source of truth:** PRD Phase 2G + provenance requirement
- **Must:**
  - `grove sync --dry-run` reports which managed regions/files would change.
  - Provenance is available for managed blocks:
    - for each managed block in a composed file, record:
      - pack id
      - injection id
      - anchor name
- **Must Not:**
  - Add brittle heuristics for provenance; use structured mapping from injection specs.
- **Acceptance gates:**
  - Unit tests cover provenance mapping.
  - Integration test verifies `--dry-run` stable output contains modified managed blocks.
  - Required validation commands:
    - `uv run pytest -n auto tests/unit/core/test_provenance.py tests/integration/test_phase2_provenance_sync.py -k provenance`

**Tasks:**

- [ ] **UPDATE** sync output reporting:
  - include managed block list in dry-run for changed files
- [ ] **ADD** unit test for provenance extraction from composed inputs.
- [ ] **UPDATE** docs/comments in core modules for maintainers (marker contract + invariants).

---

## Required Tests and Gates

- Minimum expected flow before commit/merge:
  - `just lint`
  - `just format-check`
  - `just types`
  - `just test`
- Final gate (required):
  - `just quality && just test`

## Definition of Visible Done (Required)

A human can directly verify Phase 2 completion by:

1. **Run command**: in a fixture repo with `pyproject.toml`, run:
   - `grove init --pack base --pack python --root <fixture>`
   - verify `.grove/GROVE.md` exists and contains:
     - GROVE header + acronym
     - marker anchors (`grove:anchor:*`) and user regions (`grove:user:*`)
   - verify `.grove/INDEX.md` exists and contains INDEX sections/anchors.
2. **Anchor-owned sync behavior**:
   - edit `.grove/GROVE.md`:
     - change content inside a `grove:anchor:*` region
     - also edit a `grove:user:*` region
   - run `grove sync --root <fixture>`
   - verify:
     - anchor region content matches the re-rendered composed output
     - user region content remains unchanged.
3. **Repo-root AGENTS shim**:
   - if repo already had `AGENTS.md`, run `grove init` and verify:
     - content outside the Grove-managed shim block remains
     - shim block exists and points to `.grove/GROVE.md` + `.grove/INDEX.md`.
4. **Codex skills installation** (in tests with `CODEX_HOME`):
   - set `CODEX_HOME` to a temp directory
   - run `grove init` (or sync)
   - verify:
     - `"$CODEX_HOME/skills/**/SKILL.md"` files exist for Phase 2 validation skills.

## Execution Report

Append entries here after each completed phase with:
- command run
- pass/fail outcome
- key artifact verified (paths and/or string assertions)

### Phase 2A - 2026-03-18

- Status: Complete
- Note: Superseded in part by the 2026-03-18 plan patch. The earlier implementation used `grove:managed:*` blocks and will need follow-up alignment to the anchor-owned model above.
- Scope notes:
  - Implemented anchor, managed-block, and user-region marker parsing in `src/grove/core/markers.py`.
  - Implemented deterministic anchored injection assembly in `src/grove/core/injections.py`.
  - Extended compose models with `InjectionSpec` and `PlannedFile.rendered_content`.
  - Updated compose/apply/preview flow so composed files render managed blocks during init and dry-run preview.
  - Slimmed base pack `GROVE.md` into anchor-driven infrastructure, added `INDEX.md`, and added Python pack snippet injections.
  - Preview/conflicts UI required no code changes because `compose()` still returns a standard `InstallPlan`, and preview now respects pre-rendered content.
- Commands run:
  - `uv run pytest -n auto tests/unit/core/test_composer.py tests/unit/core/test_file_ops.py tests/unit/core/test_injections.py tests/unit/core/test_markers.py` -> PASS
  - `uv run pytest -n auto tests/integration/test_init.py -k dry_run` -> PASS
  - `just quality-check` -> PASS
  - `just docs-check` -> PASS
  - `just status` -> PASS
- Acceptance evidence:
  - `uv run grove init --root <temp> --pack base --pack python --dry-run` -> PASS; output includes `--- .grove/GROVE.md ---` and managed marker `<!-- grove:managed:python-grove-guidance:start -->`; no `.grove/` directory written.
  - Composition unit coverage verifies anchor parsing, deterministic injection ordering, duplicate-id rejection, missing-anchor rejection, and preview of pre-rendered composed files.
- Fixes applied during execution:
  - Corrected pack manifest loading to carry `root_dir` without a `NameError` regression.

### Phase 2B - 2026-03-18

- Status: Complete
- Note: Superseded in part by the 2026-03-18 plan patch. The earlier implementation synced managed blocks; the revised direction is full anchor-body replacement with `grove:user:*` preservation.
- Scope notes:
  - Implemented marker-aware sync in `src/grove/core/sync.py` so files with managed blocks now replace only managed regions when markers are present.
  - Added safe reconstruction fallback: if managed markers are missing but anchor markers remain, sync rebuilds the managed content under those anchors.
  - Added fail-fast behavior for unsafe reconstruction when both managed markers and required anchors are missing, rather than overwriting blindly.
  - Updated file rendering reuse in `src/grove/core/file_ops.py` so sync, apply, and preview use the same composition-aware render path.
- Commands run:
  - `uv run pytest -n auto tests/integration/test_add_sync_configure.py -k sync` -> PASS
  - `just quality-check` -> PASS
  - `just quality` -> PASS
  - `just test` -> PASS
- Acceptance evidence:
  - Integration coverage verifies managed-region re-render with user-region preservation, marker reconstruction when anchor skeleton exists, idempotent second sync, and clear failure when reconstruction is unsafe.
  - `grove sync --dry-run` remains non-writing; sync now reports no further updates after a successful restore when rerun immediately.

### Phase 2C - 2026-03-18

- Status: Complete
- Note: Superseded in part by the 2026-03-18 plan patch. The earlier implementation introduced structured `index_entries`; the revised direction is to route INDEX content through the same generic injection mechanism as every other file.
- Scope notes:
  - Added structured `index_entries` parsing and rendering via `src/grove/core/index_render.py`.
  - Updated `src/grove/core/composer.py` to convert structured INDEX entries into anchored managed injections targeting `INDEX.md`.
  - Expanded the built-in Python pack to contribute `rules`, `commands`, and `docs` INDEX entries using structured metadata instead of a hand-authored INDEX snippet.
  - Kept the base `INDEX.md` infrastructure tiny while preserving anchor-based composition.
- Commands run:
  - `uv run pytest -n auto tests/unit/core/test_index_render.py tests/unit/core/test_markers.py tests/unit/core/test_composer.py` -> PASS
  - `just quality-check` -> PASS
- Acceptance evidence:
  - Unit coverage verifies stable markdown rendering for structured entries, section validation, and ordered insertion of rendered INDEX blocks into the `rules` anchor.
  - `INDEX.md` anchor infrastructure remains in the base pack, and pack-contributed entries now render into `rules`, `commands`, and `docs` sections via structured contributions.

### Phase 2D - 2026-03-18

- Status: Complete
- Scope notes:
  - Slimmed the base pack down to the Phase 2 infrastructure files only: `GROVE.md` and `INDEX.md`.
  - Added minimal built-in `memory`, `commands`, `knowledge`, and `project-context` packs, each with a tiny installable template and a generic INDEX injection so the pack becomes visible immediately after `init` or `add`.
  - Removed the old base pack legacy scaffolding templates (`plans/`, `handoffs/`, `decisions/`) from the active install surface.
  - Added integration coverage to verify base-only installs stay slim and that each new pack can be added successfully after init.
- Commands run:
  - `uv run pytest -n auto tests/unit/core/test_registry.py tests/unit/core/test_composer.py tests/integration/test_phase2_base_pack_slimming.py tests/integration/test_add_sync_configure.py -k "base_pack or discover_packs or compose or add"` -> PASS
  - `uv run grove init --root tmp/phase2d-smoke --pack base` -> PASS
  - `uv run grove add memory --root tmp/phase2d-smoke` -> PASS
  - `uv run grove add commands --root tmp/phase2d-smoke` -> PASS
- Acceptance evidence:
  - Base-only install now writes `.grove/GROVE.md`, `.grove/INDEX.md`, and `.grove/manifest.toml` without `plans/`, `handoffs/`, or `decisions/`.
  - The new slim packs materialize usable artifacts at `.grove/memory/README.md`, `.grove/commands/README.md`, `.grove/docs/knowledge.md`, and `.grove/docs/project-context.md`.
  - `INDEX.md` includes pack-provided pointers for the new artifacts through the generic injection path.

### Phase 2E - 2026-03-20

- Status: Complete
- Scope notes:
  - Added a generic `tool_hooks` contribution pipeline in `src/grove/core/tool_hooks.py` with hook collection, rendering, deterministic ordering, and write strategies keyed by `hook_type`.
  - Added `ToolHookSpec` to the core models and introduced a built-in `codex` integration pack that contributes the repo-root `AGENTS.md` shim as a managed block.
  - Wired tool hook application into flag-based init, TUI final apply, `grove add`, manage-mode add flow, and `grove sync`.
  - Added unit coverage for generic hook collection/application and integration coverage for Codex `AGENTS.md` append/update behavior.
- Commands run:
  - `uv run pytest -n auto tests/unit/core/test_tool_hooks.py tests/integration/test_phase2_codex_agents_shim.py -k shim` -> PASS
  - `uv run pytest -n auto tests/integration/test_init.py tests/integration/test_add_sync_configure.py -k "init or add or sync"` -> PASS
  - `just quality-check` -> PASS
  - `just quality` -> PASS
  - `just test` -> PASS
- Acceptance evidence:
  - Init with `--pack base --pack codex` preserves pre-existing user content in repo-root `AGENTS.md` and appends the Grove-managed Codex shim block pointing to `.grove/GROVE.md` and `.grove/INDEX.md`.
  - `grove sync` refreshes only the Codex managed shim block when it becomes stale.
  - The generic tool hook pipeline is pack-owned: adding the `codex` pack enables Codex integration without introducing a Codex-only orchestration path in core.
