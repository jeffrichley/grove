# Feature: Grove Remove and Doctor

This plan covers two post-MVP lifecycle commands together because they share the same ownership model:

1. `grove remove <pack>` comes first and is the primary implementation target.
2. `grove doctor` follows on top of the same provenance/ownership system.

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, models, and manifest surfaces. Import from the right files and preserve current CLI/runtime behavior outside the new command paths.

## Feature Description

Implement two new lifecycle commands for Grove:

- **`grove remove <pack>`** safely removes a non-base installed pack from an existing Grove installation, recomposes all shared outputs from the remaining pack set, deletes orphaned pack-owned artifacts, removes pack-owned tool surfaces and repo-local skills, and updates `.grove/manifest.toml` atomically.
- **`grove doctor`** performs a read-only health check of the current Grove installation: manifest validity, dependency coherence, managed-file drift, anchor integrity, tool integration health, repo-local skill correctness, and pack-owned custom diagnostics via a generic doctor hook/check pipeline.

This plan intentionally sequences **remove before doctor**. The ownership rules and provenance needed for safe removal become the foundation for doctor’s health and correctness checks.

## User Story

As a Grove maintainer
I want to safely remove installed packs and diagnose invalid or drifted Grove outputs
So that I can evolve a repo’s Grove installation without manual cleanup and quickly detect broken lifecycle/tooling states.

## Problem Statement

Grove currently supports `init`, `add`, `sync`, and configure/manage flows, but it cannot:

- remove an installed pack safely
- prove which files and tool outputs are exclusively owned by one pack
- diagnose stale or invalid managed outputs before a user discovers the problem reactively
- verify semantic correctness of tool-facing artifacts such as Codex skills

The current manifest stores `generated_files` with only `path` and `pack_id`, which is enough for `sync`, but not enough for precise lifecycle mutation and diagnostics across:

- shared anchor-composed files
- repo-root tool hook outputs like `AGENTS.md`
- repo-local `.agents/skills/*`
- future pack-specific health invariants

Without a stronger ownership model, `remove` risks deleting too much or too little, and `doctor` risks devolving into weak existence-only checks.

## Solution Statement

Introduce an explicit **ownership and diagnostics model** that extends Grove’s lifecycle surfaces:

- teach Grove how to compute **exclusive vs shared ownership** for:
  - whole-file generated outputs
  - anchor-based contributions inside shared files
  - tool hook outputs
  - repo-local Codex skill outputs
- implement `grove remove <pack>` using recomposition plus deletion of orphaned pack-owned artifacts
- implement `grove doctor` as a generic diagnostic engine with:
  - core checks for manifest/dependencies/drift/anchor integrity/tool surfaces
  - pack-owned doctor checks for tool-specific and domain-specific invariants
  - semantic correctness checks for outputs, including required front matter in Codex skills

## Feature Metadata

**Feature Type:** New Capability
**Estimated Complexity:** High
**Primary Systems Affected:** `src/grove/cli/app.py`, `src/grove/core/models.py`, `src/grove/core/manifest.py`, `src/grove/core/composer.py`, `src/grove/core/tool_hooks.py`, new remove/doctor core modules, builtin integration packs, unit/integration tests
**Dependencies:** Existing lifecycle commands (`init`, `add`, `sync`), Phase 2 composition/tool hook pipeline, manifest/provenance surfaces, Typer CLI, pytest suite

## Traceability Mapping

- Roadmap system improvements: None
- Debt items: None
- If not applicable, write: **No SI/DEBT mapping for this feature.**

## Branch Setup

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/006-grove-remove-and-doctor.md`
- Branch: `feat/006-grove-remove-and-doctor`

Commands (must be executable as written):

```bash
PLAN_FILE=".ai/PLANS/006-grove-remove-and-doctor.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING

- `src/grove/core/models.py:12-113` - Why: current pack contribution models (`InjectionSpec`, `ToolHookSpec`, `CodexSkillSpec`) and the model surface that must be extended for ownership/doctor checks.
- `src/grove/core/models.py:151-293` - Why: `PlannedFile`, sync provenance, and manifest record shapes; current manifest lacks doctor/remove-specific ownership fields.
- `src/grove/core/manifest.py:14-156` - Why: current manifest parsing/writing and schema-version rules.
- `src/grove/core/composer.py:15-233` - Why: current composition pipeline and where pack contribution ownership is already partially available for shared files.
- `src/grove/core/tool_hooks.py:19-408` - Why: current hook/skill collection and writing model; remove and doctor both need mirrored ownership logic here.
- `src/grove/cli/app.py:44-438` - Why: existing CLI command patterns, error handling, and lifecycle command registration.
- `src/grove/core/sync.py:36-307` - Why: current managed-file rewrite boundary, drift reporting, and provenance handling that doctor should reuse.
- `src/grove/packs/loader.py:16-190` - Why: pack manifest discovery/normalization; doctor hook/check contributions must follow this normalization model.
- `src/grove/packs/builtins/codex/pack.toml:1-30` - Why: concrete example of current tool hook + codex skill pack ownership surfaces.
- `src/grove/packs/builtins/codex/skills/planning-execution/SKILL.md.j2` - Why: current skill template missing front matter; doctor must catch this correctness issue.
- `src/grove/packs/builtins/codex/skills/memory-writeback/SKILL.md.j2` - Why: same correctness issue as above; use as the second example.
- `tests/integration/test_add_sync_configure.py:20-170` - Why: current lifecycle integration testing style and error assertions for add/sync.
- `tests/unit/core/test_tool_hooks.py:44-200` - Why: current deterministic ordering and repo-local skill materialization test patterns to mirror for remove/doctor.
- `tests/integration/test_phase2_codex_skills_materialization.py:20-65` - Why: current integration behavior for repo-local skills; remove and doctor must extend this coverage.
- `.ai/SPECS/001-grove-cli/PRD.md:45-53` - Why: MVP explicitly deferred `remove` and `doctor`; this is the lifecycle authority for adding them post-MVP.
- `.ai/SPECS/002-grove-phase2-composition/PRD.md:108-126` - Why: anchor-owned sync, tool hook ownership, and repo-local skill materialization are the architectural constraints remove/doctor must respect.

### New Files to Create

- `src/grove/core/remove.py` - Orchestration entry point for pack removal.
- `src/grove/core/remove_impl.py` - Ownership computation, dependency validation, recomposition/delete planning.
- `src/grove/core/remove_apply.py` - Filesystem application layer for deletion + recomposition + manifest update.
- `src/grove/core/doctor.py` - Core doctor engine, report models, and command entrypoint logic.
- `src/grove/core/doctor_checks.py` - Generic doctor checks (manifest, drift, anchors, tool outputs, skill correctness).
- `tests/unit/core/test_remove.py` - Unit tests for removal planning and dependency safety.
- `tests/unit/core/test_doctor.py` - Unit tests for doctor report generation and core checks.
- `tests/integration/test_remove.py` - Integration tests for `grove remove`.
- `tests/integration/test_doctor.py` - Integration tests for `grove doctor`.

### Existing Files Likely To Update

- `src/grove/core/models.py` - Add doctor report models and explicit ownership/doctor-check contribution specs.
- `src/grove/core/manifest.py` - Serialize/deserialize any new manifest ownership fields.
- `src/grove/core/tool_hooks.py` - Expose ownership/introspection and reversible planning for hook/skill artifacts.
- `src/grove/cli/app.py` - Register `remove` and `doctor`.
- `src/grove/packs/loader.py` - Parse/normalize `contributes.doctor_checks` and/or similar pack-owned doctor contribution shapes.
- `README.md` - Add `remove`/`doctor` CLI docs once implemented.
- `docs/cli.md` - Document command behavior, errors, and examples.
- `docs/pack-author-guide.md` - Document pack-owned doctor contributions.
- `docs/dev/roadmap.md` and `docs/dev/status.md` - Track Plan 006 progress and completion.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING

- `.ai/SPECS/001-grove-cli/PRD.md#13-future-considerations`
  - Why: explicitly identifies `grove remove` and `grove doctor` as deferred post-MVP lifecycle features.
- `.ai/SPECS/002-grove-phase2-composition/PRD.md#4-mvp-scope`
  - Why: defines the authoritative ownership boundaries for anchors, tool hooks, and repo-local skills.
- `.ai/RULES.md`
  - Why: plan-before-code, no silent fallbacks, required final gate, no destructive shortcuts, no main-branch direct work.
- `docs/concept.md`
  - Why: doctor should preserve Grove’s “Verify” principle and remove should leave the ecosystem stronger, not partially broken.

### Patterns to Follow

**CLI Pattern**

- Register commands via Typer in `src/grove/cli/app.py`.
- Resolve project roots via `_resolve_root()`.
- Surface actionable failures through `_exit_with_error(...)`.

**Manifest Pattern**

- Keep manifest schema versioned in `src/grove/core/manifest.py`.
- Use strongly typed Pydantic models in `src/grove/core/models.py`.
- Do not introduce silent defaults for required fields.

**Lifecycle Pattern**

- `add` and `sync` are orchestrated in small core modules (`add.py`, `sync.py`) with helpers split out.
- Dry-run support should return explicit paths/changes rather than mutate the filesystem.

**Testing Pattern**

- Use `CliRunner` integration tests for command behavior.
- Use pytest `@pytest.mark.integration` / `@pytest.mark.unit`.
- Assert behavior and safety constraints, not fragile full error strings.

**Tool Integration Pattern**

- Tool-native artifacts are pack-owned and rendered through `tool_hooks.py`.
- Codex skills currently materialize directly to `.agents/skills/<skill>/SKILL.md`.
- Current skill templates have **no front matter**, which is a known correctness gap and should become a concrete doctor failure case.

---

## PLAN PATCH

### Plan Patch - Remove Before Doctor

This plan intentionally implements `grove remove` before `grove doctor`, even though doctor is lower risk in isolation.

Reason:
- remove forces Grove to formalize ownership across composed files, tool hooks, and repo-local skills
- doctor should then inspect the same ownership graph rather than inventing a second diagnostic-only model

### Plan Patch - Base Pack Is Non-Removable

`base` is required and cannot be removed. This is a hard rule, not a warning-level recommendation.

### Plan Patch - Doctor Must Validate Output Correctness

Doctor must inspect semantic validity of tool-facing outputs. For the initial implementation, this explicitly includes:
- Codex skill front matter presence
- Codex skill front matter parseability
- required front matter keys agreed during implementation

### Plan Patch - Pack-Owned Doctor Checks

Doctor must support pack-owned verification hooks/checks. Core checks are required, but pack-specific invariants must not be hard-coded into doctor as one-off logic.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Ownership Model and Manifest Extension

Formalize the ownership data required by both remove and doctor.

**Acceptance criteria**

- ownership/report models are explicit and typed
- any required manifest schema changes are versioned and round-trip tested
- doctor-related pack contribution shapes are normalized by the loader

**Non-goals**

- implementing remove filesystem mutation
- implementing doctor command behavior

**Intent Lock**

- **Source of truth:** `src/grove/core/models.py`, `src/grove/core/manifest.py`, `src/grove/core/composer.py`, `src/grove/core/tool_hooks.py`, this plan’s Plan Patches.
- **Must:**
  - define explicit ownership/introspection surfaces for whole-file outputs, shared anchors, tool hooks, and repo-local skills
  - keep ownership deterministic and derivable from selected packs plus current pack manifests
  - add schema/version handling if manifest shape changes
- **Must Not:**
  - rely on path heuristics alone for removal
  - make `remove` or `doctor` scrape rendered markdown to infer ownership when structured provenance is available
  - introduce destructive defaults
- **Provenance map:**
  - whole-file ownership comes from `GeneratedFileRecord.pack_id`
  - anchor ownership comes from `PlannedFile.anchor_provenance`
  - tool hook ownership comes from `ToolHookSpec`
  - skill ownership comes from `CodexSkillSpec`
- **Acceptance gates:**
  - unit tests for new ownership models and manifest round-trip
  - `just types && just lint && just test`

**Tasks**

- [x] Extend `src/grove/core/models.py` with explicit ownership/report models needed by remove and doctor.
- [x] Decide whether manifest needs new persisted sections (for example tool outputs, skill outputs, or doctor metadata). If yes, version the schema and document the migration path.
- [x] Add normalized pack-owned doctor contribution specs to the model surface (for example `DoctorCheckSpec` or equivalent).
- [x] Update `src/grove/packs/loader.py` to normalize any new doctor-related contribution keys.
- [x] Add unit coverage for model parsing and manifest read/write compatibility.

### Phase 2: `grove remove` Core Planning and Safety Rules

Implement the removal planner before any filesystem mutation.

**Acceptance criteria**

- remove planner rejects `base`
- remove planner rejects packs with installed dependents
- planner classifies artifacts into delete/rewrite/preserve safely
- dry-run planning is available without filesystem mutation

**Intent Lock**

- **Source of truth:** this plan, `src/grove/core/composer.py`, `src/grove/core/tool_hooks.py`, `.ai/SPECS/001-grove-cli/PRD.md` deferred lifecycle intent.
- **Must:**
  - reject removal of `base`
  - reject removal when other installed packs depend on the target pack
  - support `--dry-run`
  - compute all four ownership classes: whole files, shared anchors, tool hooks, repo-local skills
  - recompute remaining desired state from the remaining pack set
- **Must Not:**
  - delete shared files that still have remaining contributors
  - blindly remove `AGENTS.md` if other managed/user content remains
  - remove `.agents/skills` directories still needed by remaining packs
- **Non-goals:**
  - interactive cascading dependent removal in v1
  - removing multiple packs in one command
- **Acceptance gates:**
  - unit tests for dependency blocking, base-pack blocking, dry-run planning, orphan detection
  - targeted integration tests for remove planning behavior

**Tasks**

- [x] CREATE `src/grove/core/remove_impl.py` with:
  - dependency validation
  - remaining-pack selection
  - desired-state recomposition
  - artifact ownership diffing
  - deletion/rewrite plan models
- [x] Explicitly classify artifacts into:
  - delete entirely
  - rewrite from remaining packs
  - preserve untouched
- [x] Add helper(s) in `src/grove/core/tool_hooks.py` to plan reversible tool hook/skill ownership from selected packs.
- [x] Ensure remove planning can distinguish:
  - shared `AGENTS.md` managed block removal
  - deleting orphaned repo-local skills
  - preserving user-owned text outside managed blocks

### Phase 3: `grove remove` Apply Path and CLI Command

Implement the actual lifecycle mutation.

**Acceptance criteria**

- `grove remove <pack>` exists with `--dry-run`
- successful remove updates manifest atomically
- remove rewrites shared outputs and deletes orphaned exclusive artifacts correctly
- CLI output is explicit about what changed

**Non-goals**

- interactive removal wizard
- multi-pack removal in one invocation

**Intent Lock**

- **Source of truth:** Phase 2 remove planner, `src/grove/cli/app.py`, existing `add`/`sync` command behavior.
- **Must:**
  - expose `grove remove <pack> [--root] [--dry-run]`
  - update manifest atomically on successful non-dry-run remove
  - emit a clear removal report: deleted files, rewritten files, preserved files
  - keep command errors actionable
- **Must Not:**
  - mutate manifest on dry-run
  - partially remove a pack and leave manifest inconsistent
  - leave stale pack-owned repo-local skills if they are no longer selected
- **Acceptance gates:**
  - integration tests for remove success, remove blocked by dependent, remove blocked for base, dry-run non-mutating
  - `just quality && just test`

**Tasks**

- [x] CREATE `src/grove/core/remove_apply.py` for ordered delete/rewrite application.
- [x] CREATE `src/grove/core/remove.py` as the orchestration entrypoint.
- [x] UPDATE `src/grove/cli/app.py` to add the `remove` command following existing CLI patterns.
- [x] Ensure removal of a tool integration pack updates/removes only its managed block in target files rather than deleting the whole file when user content or other pack content remains.
- [x] Ensure repo-local `.agents/skills/<skill>/SKILL.md` is removed when the removed pack exclusively owns that skill.
- [x] Add dry-run output analogous to sync’s explicit change reporting.

### Phase 4: `grove doctor` Core Checks and Report Model

Implement the generic doctor engine on top of the ownership model built for remove.

**Acceptance criteria**

- `grove doctor` exists and runs read-only checks
- doctor reports manifest/dependency/drift/anchor/tool/skill issues
- healthy repos produce a clean report
- broken repos produce categorized findings

**Non-goals**

- auto-fix mode
- network-backed diagnostics

**Intent Lock**

- **Source of truth:** this plan, `src/grove/core/sync.py`, manifest/tool hook/skill ownership surfaces.
- **Must:**
  - keep doctor read-only by default
  - validate manifest existence/schema/pack availability/dependency coherence
  - detect missing tracked files, orphaned files, drifted files, unsafe anchor states
  - verify tool integration outputs and repo-local skills
  - support human-readable report first; JSON output optional but encouraged
- **Must Not:**
  - mutate files in the base `doctor` command
  - implement “fix” mode in v1
  - reduce doctor to presence-only checks
- **Acceptance gates:**
  - unit tests for report generation and issue categorization
  - integration tests for healthy repo vs broken repo cases

**Tasks**

- [x] CREATE `src/grove/core/doctor_checks.py` with generic checks for manifest validity, pack availability, dependency coherence, drift, anchors, tool outputs, and skills.
- [x] CREATE `src/grove/core/doctor.py` with doctor report models, issue aggregation, and top-level `run_doctor(...)`.
- [x] UPDATE `src/grove/cli/app.py` to add `doctor`.
- [x] Decide whether v1 includes `--json` and `--strict`; if implemented, document exact exit behavior in a plan patch during execution if scope changes.

### Phase 5: Pack-Owned Doctor Checks and Output Correctness

Add pack-owned diagnostics and semantic validation, starting with Codex skill front matter.

**Acceptance criteria**

- packs can contribute doctor-specific checks through a generic schema
- Codex integration pack ships the first concrete doctor checks
- doctor detects missing/malformed/mis-specified skill front matter
- Codex skill templates are updated to satisfy the new correctness contract

**Non-goals**

- implementing every future integration pack check in this phase
- validating arbitrary file formats without explicit pack-owned schemas

**Intent Lock**

- **Source of truth:** this plan’s “Pack-Owned Doctor Checks” and “Doctor Must Validate Output Correctness” patches, current codex pack manifests/templates.
- **Must:**
  - define a generic pack-owned doctor-check contribution model
  - allow packs to verify pack-specific requirements without hard-coding each one into core
  - include concrete Codex checks for skill front matter validity
  - fail doctor when skill files are present but unusable by the target tool
- **Must Not:**
  - hard-code every future integration check in core
  - require network calls or external APIs for doctor
  - make doctor parse arbitrary formats without an explicit schema
- **Acceptance gates:**
  - unit tests for pack-owned doctor-check loading/execution
  - integration tests where Codex skills without front matter are reported correctly

**Tasks**

- [x] Extend pack contribution schema with a generic doctor check mechanism.
- [x] Implement the first concrete pack-owned check set in the Codex integration pack.
- [x] Define and document the required SKILL front matter contract used by doctor.
- [x] Update Codex skill templates to include valid front matter once the contract is defined.
- [x] Add doctor checks for:
  - missing front matter
  - malformed front matter
  - required key omissions
  - missing `SKILL.md` in expected skill directories

### Phase 6: Docs, Status Surfaces, and Final Validation

Complete documentation and close the feature cleanly.

**Acceptance criteria**

- README/CLI docs describe remove and doctor accurately
- pack author guide explains doctor-check contributions and skill front matter
- roadmap/status reflect Plan 006 progress and completion
- final gates pass

**Non-goals**

- unrelated docs rewrites
- roadmap reprioritization beyond recording this feature

**Intent Lock**

- **Source of truth:** this plan, `README.md`, `docs/cli.md`, `docs/pack-author-guide.md`, `docs/dev/roadmap.md`, `docs/dev/status.md`.
- **Must:**
  - document `remove` and `doctor` command behavior and limitations
  - document pack-owned doctor checks in the pack author guide
  - update roadmap/status with Plan 006 progress
  - capture execution evidence in this plan’s `## Execution Report`
- **Must Not:**
  - leave command help/docs inconsistent
  - merge with failing quality/test gates
- **Acceptance gates:**
  - `just quality && just test`
  - `just test-cov`
  - `just docs-check`
  - `just status-ready`

**Tasks**

- [x] UPDATE `README.md` and `docs/cli.md` for `remove` and `doctor`.
- [x] UPDATE `docs/pack-author-guide.md` for doctor-check contributions and skill front-matter requirements.
- [x] UPDATE roadmap/status and mark the plan complete when finished.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1

1. **UPDATE** `src/grove/core/models.py`
   - **IMPLEMENT:** ownership models for removable tool outputs/skills and doctor report/check specs.
   - **PATTERN:** existing `ToolHookSpec`, `CodexSkillSpec`, `SyncFileChange` models in `src/grove/core/models.py:71-205`.
   - **GOTCHA:** avoid ad-hoc dict payloads; use strongly typed Pydantic models.
   - **VALIDATE:** `just types && uv run pytest -n auto tests/unit/core/test_models.py`

2. **UPDATE** `src/grove/core/manifest.py`
   - **IMPLEMENT:** manifest schema extension and serialization if new persisted ownership sections are required.
   - **PATTERN:** current schema guards in `src/grove/core/manifest.py:14-156`.
   - **GOTCHA:** if schema changes, update versioning and test round-trip explicitly.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_manifest.py`

3. **UPDATE** `src/grove/packs/loader.py`
   - **IMPLEMENT:** normalize any doctor-check contribution shapes.
   - **PATTERN:** `_normalize_contributes` and `_parse_pack_toml` in `src/grove/packs/loader.py:97-190`.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/packs/test_loader.py`

### Phase 2

4. **CREATE** `src/grove/core/remove_impl.py`
   - **IMPLEMENT:** dependency blocking, base-pack blocking, remaining-pack recomposition, orphan classification.
   - **PATTERN:** `src/grove/core/add_impl.py` for focused lifecycle helpers; `src/grove/core/composer.py:15-233` for desired-state recomposition.
   - **GOTCHA:** target file deletion must distinguish shared composed files from exclusive whole-file outputs.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_remove.py -k planning`

5. **UPDATE** `src/grove/core/tool_hooks.py`
   - **IMPLEMENT:** reversible ownership planning helpers for tool hooks and repo-local skills.
   - **PATTERN:** collection/render paths in `src/grove/core/tool_hooks.py:67-182`.
   - **GOTCHA:** managed-block files like `AGENTS.md` may need block removal, not file deletion.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_tool_hooks.py tests/unit/core/test_remove.py -k hook`

### Phase 3

6. **CREATE** `src/grove/core/remove_apply.py`
   - **IMPLEMENT:** ordered delete/rewrite/preserve application with dry-run summaries.
   - **PATTERN:** `src/grove/core/sync.py:36-307` for explicit changed-path reporting.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_remove.py -k apply`

7. **CREATE** `src/grove/core/remove.py`
   - **IMPLEMENT:** manifest load, planning call, apply path, updated manifest return.
   - **PATTERN:** `src/grove/core/add.py` and `src/grove/core/sync.py`.
   - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_remove.py`

8. **UPDATE** `src/grove/cli/app.py`
   - **IMPLEMENT:** `grove remove <pack> [--root] [--dry-run]`.
   - **PATTERN:** existing `add` and `sync` commands.
   - **GOTCHA:** keep errors actionable and reject `base` removal explicitly.
   - **VALIDATE:** `uv run grove remove --help`

9. **ADD** `tests/integration/test_remove.py`
   - **IMPLEMENT:** success remove, `base` blocked, dependent blocked, dry-run no mutation, repo-local skills removed, `AGENTS.md` managed block behavior.
   - **PATTERN:** `tests/integration/test_add_sync_configure.py` and `tests/integration/test_phase2_codex_skills_materialization.py`.
   - **VALIDATE:** `uv run pytest -n auto tests/integration/test_remove.py`

### Phase 4

10. **CREATE** `src/grove/core/doctor_checks.py`
    - **IMPLEMENT:** generic checks for manifest validity, pack availability, dependencies, drift, anchors, hook outputs, skills.
    - **PATTERN:** reuse `compose(...)`, `run_sync(...)`-style desired-state computation rather than duplicate logic.
    - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_doctor.py -k generic`

11. **CREATE** `src/grove/core/doctor.py`
    - **IMPLEMENT:** doctor report models, issue aggregation, CLI-facing run function.
    - **GOTCHA:** default mode must be read-only.
    - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_doctor.py`

12. **UPDATE** `src/grove/cli/app.py`
    - **IMPLEMENT:** `grove doctor [--root]` and optional `--json`/`--strict` if included.
    - **VALIDATE:** `uv run grove doctor --help`

### Phase 5

13. **UPDATE** `src/grove/core/models.py` and `src/grove/packs/loader.py`
    - **IMPLEMENT:** pack-owned doctor-check contribution schema.
    - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_doctor.py tests/unit/packs/test_loader.py -k pack`

14. **UPDATE** `src/grove/packs/builtins/codex/pack.toml`
    - **IMPLEMENT:** first doctor-check contribution entries for Codex skill/output health.
    - **PATTERN:** current tool hook and codex skill declarations in `src/grove/packs/builtins/codex/pack.toml:12-30`.
    - **VALIDATE:** `uv run pytest -n auto tests/unit/core/test_doctor.py tests/integration/test_doctor.py -k codex`

15. **UPDATE** `src/grove/packs/builtins/codex/skills/*/SKILL.md.j2`
    - **IMPLEMENT:** required front matter contract.
    - **GOTCHA:** doctor must fail before this change and pass after it; test both broken and fixed cases.
    - **VALIDATE:** `uv run pytest -n auto tests/integration/test_doctor.py tests/integration/test_phase2_codex_skills_materialization.py`

16. **ADD** `tests/integration/test_doctor.py`
    - **IMPLEMENT:** healthy install, drifted file, missing anchor, missing skill file, malformed skill front matter, missing tool shim block.
    - **VALIDATE:** `uv run pytest -n auto tests/integration/test_doctor.py`

### Phase 6

17. **UPDATE** `README.md`, `docs/cli.md`, and `docs/pack-author-guide.md`
    - **IMPLEMENT:** command docs and doctor-check/front-matter guidance.
    - **VALIDATE:** `just docs-check`

18. **UPDATE** `docs/dev/roadmap.md`, `docs/dev/status.md`, and this plan
    - **IMPLEMENT:** progress and completion updates with execution evidence.
    - **VALIDATE:** `just status-ready`

19. **RUN** full validation and manual smoke
    - **VALIDATE:** `just quality && just test && just test-cov`

---

## TESTING STRATEGY

### Unit Tests

- removal dependency graph and base-pack rejection
- ownership classification for:
  - whole-file outputs
  - anchor-contributed shared files
  - managed-block tool hooks
  - repo-local Codex skills
- doctor issue generation and severity/category mapping
- pack-owned doctor-check parsing/loading
- manifest round-trip if schema changes

### Integration Tests

- init base + codex, then remove codex:
  - repo-local skills deleted
  - Codex shim block removed or rewritten correctly
  - remaining Grove surfaces preserved
- init base + python + dependent case, then remove dependency:
  - command fails clearly
- doctor on healthy repo:
  - exits success and reports healthy state
- doctor on drifted repo:
  - flags drift and unsafe anchor states
- doctor on Codex skills without front matter:
  - reports semantic correctness failure

### Edge Cases

- remove unknown pack
- remove already absent pack
- remove `base`
- remove pack with dependents
- dry-run remove
- doctor with no manifest
- doctor with unsupported manifest schema
- doctor when installed pack no longer exists in builtins
- doctor when `AGENTS.md` managed block end marker is missing
- doctor when `.agents/skills/<skill>/SKILL.md` exists but front matter is malformed

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

- `just format-check`
- `just lint-check`
- `just types`

### Level 2: Focused Unit Tests

- `uv run pytest -n auto tests/unit/core/test_remove.py`
- `uv run pytest -n auto tests/unit/core/test_doctor.py`
- `uv run pytest -n auto tests/unit/core/test_tool_hooks.py tests/unit/packs/test_loader.py`

### Level 3: Focused Integration Tests

- `uv run pytest -n auto tests/integration/test_remove.py`
- `uv run pytest -n auto tests/integration/test_doctor.py`
- `uv run pytest -n auto tests/integration/test_phase2_codex_skills_materialization.py`

### Level 4: Full Gate

- `just quality && just test`
- `just test-cov`
- `just docs-check`
- `just status-ready`

### Level 5: Manual Validation

```bash
uv run grove init --root <fixture> --pack base --pack python --pack codex
uv run grove remove codex --root <fixture> --dry-run
uv run grove remove codex --root <fixture>
uv run grove doctor --root <fixture>
```

Manual checks:
- confirm `base` cannot be removed
- confirm dependent-pack removal is blocked
- confirm `.agents/skills/*` for removed packs disappear only when orphaned
- confirm `AGENTS.md` user content survives integration-pack removal
- confirm doctor reports malformed/missing Codex skill front matter

---

## OUTPUT CONTRACT

- Exact output artifacts/surfaces:
  - `grove remove <pack>` CLI command and dry-run output
  - `grove doctor` CLI command and doctor report output
  - updated `.grove/manifest.toml` after successful remove
  - updated repo-local tool surfaces such as `AGENTS.md`
  - updated repo-local `.agents/skills/*`
- Verification commands:
  - `uv run grove remove codex --root <fixture> --dry-run`
  - `uv run grove remove codex --root <fixture>`
  - `uv run grove doctor --root <fixture>`

## DEFINITION OF VISIBLE DONE

- A human can directly verify completion by:
  - running `grove remove <pack>` and observing that the selected non-base pack disappears from `.grove/manifest.toml`, its orphaned files/tool outputs are removed, and shared Grove files are recomposed correctly
  - running `grove doctor` on a healthy install and seeing a clean report
  - intentionally breaking a Codex skill’s front matter or deleting a managed hook block and seeing doctor flag the problem clearly
  - confirming `grove remove base` fails with an explicit non-removable error

## INPUT/PREREQUISITE PROVENANCE

- Generated during this feature:
  - fixture Grove installs via `uv run grove init --root <fixture> --pack ...`
  - broken doctor scenarios via direct test mutations to managed files and skill files
- Pre-existing dependency:
  - built-in packs under `src/grove/packs/builtins/`
  - existing lifecycle/tool hook/sync behavior in current `main`

---

## ACCEPTANCE CRITERIA

- [x] `grove remove <pack>` exists and rejects removal of `base`
- [x] `grove remove <pack>` rejects removal when installed dependents exist
- [x] `grove remove <pack>` recomposes shared files and deletes orphaned exclusive artifacts safely
- [x] `grove remove <pack> --dry-run` reports planned changes without mutating files or manifest
- [x] `grove doctor` exists and validates manifest, dependencies, drift, anchors, tool surfaces, and repo-local skills
- [x] doctor supports pack-owned diagnostic contributions
- [x] doctor flags Codex skill front matter issues as correctness failures
- [x] all validation commands pass
- [x] docs and status surfaces are updated
- [x] no regressions in existing init/add/sync/manage behavior

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed immediately
- [x] All validation commands executed successfully
- [x] Full test suite passes
- [x] Coverage gate remains green
- [x] Manual remove/doctor testing confirms expected behavior
- [x] Acceptance criteria all met
- [x] Code reviewed for lifecycle safety and maintainability

---

## NOTES

- The current Codex skill templates under `src/grove/packs/builtins/codex/skills/*/SKILL.md.j2` have no front matter. This is a real correctness gap to fix and to test in doctor.
- If manifest schema changes are not strictly required, prefer deriving ownership from current manifests plus selected-pack recomposition. Persist only what must survive independently of pack re-discovery.
- Remove should prefer **recomposition over deletion** whenever a file is shared.
- Doctor should prefer **structured issue reporting over prose-only warnings** so future JSON/CI surfaces stay viable.

## Confidence Score

8.5/10 that one-pass implementation will succeed if the execution agent follows this plan top-to-bottom and keeps scope fixed.

## Execution Report

- 2026-03-20, Phase 1 complete: added explicit ownership/report models in `src/grove/core/models.py` (`ToolHookOutputRecord`, `CodexSkillOutputRecord`, `DoctorCheckSpec`, `DoctorIssue`, `DoctorReport`); documented that manifest schema remains v1 because ownership stays derivable from existing generated-file records plus composition/tool spec provenance; updated loader/test coverage for doctor-check contribution parsing. Validation: `uv run pytest -n auto tests/unit/core/test_models.py` PASS, `uv run pytest -n auto tests/unit/packs/test_loader.py` PASS, `just types` PASS, `just lint` PASS, `just test` PASS.
- 2026-03-20, Phase 2 complete: added `src/grove/core/remove_impl.py` with non-mutating remove planning (`RemoveContext`, `RemovePlan`, `RemovePathPlan`), remaining-pack recomposition, dependency/base-pack guards, and delete/rewrite/preserve classification for managed files, tool hooks, and repo-local Codex skills; extended `src/grove/core/tool_hooks.py` with reversible target-state planning helpers for managed hook blocks and materialized skills. Validation: `uv run pytest -n auto tests/unit/core/test_remove.py` PASS, `uv run pytest -n auto tests/unit/core/test_tool_hooks.py` PASS, `uv run pytest -n auto tests/integration/test_remove.py` PASS, `just types` PASS, `just lint` PASS.
- 2026-03-20, Phase 3 complete: added `src/grove/core/remove_apply.py` and `src/grove/core/remove.py` for ordered delete/rewrite execution plus replace-based manifest persistence; added `grove remove <pack> [--root] [--dry-run]` in `src/grove/cli/app.py` with explicit deleted/rewritten/preserved reporting; verified managed-file rewrites, managed-block hook removal in `AGENTS.md`, pack-local skill deletion, dry-run non-mutation, and blocked removal cases. Validation: `uv run pytest -n auto tests/integration/test_remove.py` PASS, `uv run pytest -n auto tests/unit/core/test_remove.py tests/unit/core/test_tool_hooks.py` PASS, `just types` PASS, `just quality` PASS, `just test` PASS.
- 2026-03-20, Phase 4 complete: added `src/grove/core/doctor_checks.py` and `src/grove/core/doctor.py` with read-only manifest, dependency, managed-file drift, anchor integrity, tool-hook target, and pack-local skill diagnostics; added `grove doctor` in `src/grove/cli/app.py` with human-readable reporting and nonzero exit on unhealthy repos; decided to defer `--json` and `--strict` until a later phase. Validation: `uv run pytest -n auto tests/unit/core/test_doctor.py` PASS, `uv run pytest -n auto tests/integration/test_doctor.py` PASS, `uv run grove doctor --help` PASS, `just types` PASS, `just quality` PASS, `just test` PASS.
- 2026-03-20, Phase 5 complete: added generic pack-owned doctor check collection/execution in `src/grove/core/doctor_checks.py`, wired pack-owned checks into `run_doctor(...)`, added first concrete Codex `skill_front_matter` checks in `src/grove/packs/builtins/codex/pack.toml`, and updated built-in Codex skill templates to include required front matter (`name`, `description`). Validation: `uv run pytest -n auto tests/unit/core/test_doctor.py` PASS, `uv run pytest -n auto tests/integration/test_doctor.py tests/integration/test_phase2_codex_skills_materialization.py` PASS, `uv run pytest -n auto tests/unit/packs/test_loader.py` PASS, `just types` PASS, `just quality` PASS, `just test` PASS.
- 2026-03-20, Phase 6 complete: updated `README.md`, `docs/cli.md`, and `docs/pack-author-guide.md` for `remove`, `doctor`, pack-owned `doctor_checks`, and Codex skill front matter; updated roadmap/status to mark Plan 006 complete; final gates passed. Validation: `just quality` PASS, `just test` PASS, `just test-cov` PASS, `just docs-check` PASS, `just status-ready` PASS.
