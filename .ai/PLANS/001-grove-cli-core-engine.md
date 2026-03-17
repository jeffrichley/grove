# Feature: Grove CLI — Core Engine (Phase 1)

The following plan should be complete, but it's important to validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Implement the core engine for the Grove CLI: pack registry, repo analyzer, composition/install planner, template renderer, file operations, and manifest read/write. No interactive TUI in this phase. Delivers a non-interactive or flag-driven `grove init` that can install the Base Pack and one capability pack (e.g. Python) into `.grove/` and record state in `manifest.toml`. This enables later phases (TUI, add/sync/manage) to build on a working pipeline.

## User Story

As a developer adopting Grove
I want to run a single command (e.g. `grove init --non-interactive` or with flags) so that my repo gets a minimal, correct `.grove/` layout with Base + one pack and a manifest, without manual file creation.

## Problem Statement

Grove needs a reproducible way to install its context-engineering system into a repo. Without a core engine (registry, analyzer, composer, renderer, manifest), every setup would be manual and inconsistent. Phase 1 establishes the pipeline that later TUI and lifecycle commands will use.

## Solution Statement

Add a structured Python package under `src/grove/` with: (1) a pack registry that loads pack manifests (e.g. `pack.yaml`) from built-in pack directories; (2) an analyzer with detectors for Python, uv, pytest, ruff, etc., producing a `ProjectProfile`; (3) a composer that combines user selections + profile + pack metadata into an `InstallPlan`; (4) a template renderer (e.g. Jinja2) with variable injection; (5) file operations with preview/dry-run and collision handling; (6) manifest schema and read/write. Ship a Base Pack and a Python capability pack as data (manifests + templates). Expose a CLI entry point that runs the pipeline end-to-end for init.

## Feature Metadata

**Feature Type:** New Capability
**Estimated Complexity:** High
**Primary Systems Affected:** `src/grove/` (new modules), `pyproject.toml` (entry point, optional deps), tests
**Dependencies:** Python 3.12+, Jinja2 (or equivalent), PyYAML, Pydantic; optional: Typer for CLI. **TUI (later phase):** [Textual](https://textual.textualize.io/) — we use Textual for the interactive setup and manage screens.

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `None` (Grove CLI is the product; no SI-XXX in this repo)
- Debt items: `None`
- If not applicable, write: **No SI/DEBT mapping for this feature.**

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/001-grove-cli-core-engine.md`
- Branch: `feat/001-grove-cli-core-engine`

Commands (must be executable as written):

```bash
PLAN_FILE=".ai/PLANS/001-grove-cli-core-engine.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `pyproject.toml` (full file) — Why: Package name `grove`, build config, dev deps, ruff/mypy/pytest config; add CLI deps and entry point here
- `justfile` (lines 1–50) — Why: Validation commands (`just lint`, `just format-check`, `just types`, `just test`, `just quality`) to use in task VALIDATE
- `src/grove/__init__.py` — Why: Package root; keep `__all__` and docstring consistent when adding subpackages
- `tests/unit/test_placeholder.py` — Why: Test layout and import pattern; mirror for new tests under `tests/unit/` or `tests/integration/`
- `.ai/RULES.md` (lines 1–55) — Why: No plan no code; quality gates; use `uv run python`; no silent fallbacks; strict typing
- `.ai/REF/plan-authoring.md` — Why: Intent locks, branch setup, execution report expectations
- `.ai/REF/testing-and-gates.md` — Why: Final gate `just quality && just test`

### New Files to Create

- `src/grove/cli/__init__.py` — CLI package
- `src/grove/cli/app.py` — Typer app and `init` command (or minimal CLI entry)
- `src/grove/core/__init__.py` — Core package
- `src/grove/core/models.py` — Pydantic models: ProjectProfile, PackManifest, InstallPlan, ManifestState, etc.
- `src/grove/core/manifest.py` — Manifest load/save and schema
- `src/grove/core/registry.py` — Pack discovery and metadata loading
- `src/grove/core/composer.py` — Install plan computation from profile + selections + packs
- `src/grove/core/renderer.py` — Template rendering with variables
- `src/grove/core/file_ops.py` — Safe write, preview, dry-run, collision handling
- `src/grove/analyzer/__init__.py` — Analyzer package
- `src/grove/analyzer/engine.py` — Runs detectors, returns ProjectProfile
- `src/grove/analyzer/detectors/` — Detector modules (e.g. python, uv, pytest)
- `src/grove/packs/__init__.py` — Packs package
- `src/grove/packs/loader.py` — Load pack manifests and resolve paths
- `src/grove/packs/builtins/base/` — Base Pack (pack.yaml + templates)
- `src/grove/packs/builtins/python/` — Python Pack (pack.yaml + templates)
- `tests/unit/` — Unit tests for registry, analyzer, composer, renderer, manifest, file_ops
- `tests/integration/` or `tests/e2e/` — One test: run init on fixture repo, assert `.grove/` and manifest exist

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [Jinja2 Template Designer](https://jinja.palletsprojects.com/templates/) — Why: Variable injection, conditionals, filters if using Jinja2
- [Pydantic V2](https://docs.pydantic.dev/latest/) — Why: Models for profile, manifest, plan; validation
- [Typer](https://typer.tiangolo.com/) — Why: CLI structure and flags if using Typer
- [Textual](https://textual.textualize.io/) — Why: TUI framework for interactive setup and `grove manage` (Screens, Widgets, reactive state). Use for later phase; not required in Phase 1.
- Grove CLI PRD (when present): `.ai/SPECS/003-grove-cli/PRD.md` — Why: Phase 1 scope, pack model, manifest design
- **Grove concept (source of truth):** `docs/concept.md` — Why: Base Pack content and commands must align with the GROVE framework; see below.

### Grove Concept Alignment (from docs/concept.md)

Use the [GROVE Context System](docs/concept.md) as **source of truth** for how Grove’s installed content should work in general. We are not copying it exactly; we are aligning to the same ideas.

**Framework (G — R — O — V — E, from docs/concept.md):**

1. **G — Grow Knowledge** — Externalize knowledge into durable artifacts. Base Pack: plans, handoffs, decisions, commit guidance (optional `Context:` when .grove assets change). Goal: agents write knowledge into the Grove.

2. **R — Root Tasks** — Tasks anchored in clear structure and isolated workflows. Base Pack: plan template (ordered tasks), execute convention (read plan, run in order, validate). Goal: clear roots in the system.

3. **O — Optimize Context** — Layered context; just-in-time, not just-in-case. Base Pack implements:
   - **Tier 1 (always loaded):** One lean global rules file — e.g. GROVE.md, under ~500 lines. Project structure, essential commands, architecture overview, universal conventions.
   - **Tier 2 (on-demand rules):** Scoped rule files that load when the agent touches matching paths. In WISC, rules use frontmatter `paths: ["**/*.test.ts", "packages/cli/**"]`. In Grove, pack manifests can declare path triggers for rules so the same idea applies (e.g. Python pack rule loads when touching `src/**/*.py` or `tests/**`).
   - **Tier 3 (reference docs):** Heavy docs not auto-loaded; loaded on demand or by a scout. In WISC these live in `.claude/docs/` with a “Purpose / When to use / Size” header. Base Pack can install a `docs/` (or `ref/`) directory and a convention that these are for targeted loading only.

2. **Command set (Write / Select / Compress)**
   - **Prime (Select):** In WISC, prime is a *process* (steps to run, files to read, output report), not a single blob. E.g. prime-backend: list dirs, read orchestrator, read command-handler, read session state, output structured summary. Base Pack should provide a prime *template* or command spec that follows this pattern (analyze structure → read core docs → key entry points → current state → concise report).
   - **Plan (Write):** Plan is written to a file (e.g. `.claude/archon/plans/{kebab}.md`) and consumed by execute. Grove uses `.ai/PLANS/<NNN>-<feature>.md`; Base Pack can generate a plan template and optionally a `.grove/plans/` convention that mirrors this (or points at .ai/PLANS).
   - **Execute (Write):** Read plan, execute tasks in order, run validation, output execution report. Our execute command and plan format already match; Base Pack templates should reinforce this.
   - **Handoff (Write + Compress):** WISC handoff is a structured HANDOFF.md: Goal, Completed, In Progress / Next Steps, Key Decisions, Dead Ends, Files Changed, Current State, Context for Next Session, Recommended first action. Base Pack must ship a HANDOFF_TEMPLATE (or handoffs/ template) that matches this structure so sessions can compress and hand off cleanly.
   - **Commit (Write):** Enriched conventional commit with optional `Context:` section when AI context assets change (rules, commands, docs). Base Pack should document this and optionally provide a commit template or guidance.

3. **Rules and path triggers**
   - In WISC, each rule file has YAML frontmatter `paths: ["glob", "patterns"]`. Grove pack manifests should support declaring path triggers for contributed rules (e.g. in `contributes.rules[].paths` or equivalent) so that installed packs can provide scoped, auto-loaded rules in the same spirit.

4. **What we do not copy**
   - WISC is Claude/Archon-specific (CLAUDE.md, Archon packages). Grove is tool-agnostic and uses GROVE.md and .grove/. We keep our own naming and layout.
   - WISC puts plans under `.claude/archon/plans/`; we keep using `.ai/PLANS/` or document a clear mapping. Base Pack content should be generic enough to work with any AI coding tool.

When implementing the Base Pack (Phase 2 and Phase 6), read the WISC README and at least one of each: a command (e.g. handoff.md, plan-feature.md), a rules-example file (e.g. testing.md or cli.md for paths frontmatter), and a docs-example header (e.g. architecture-deep-dive.md) so the generated GROVE.md, plan template, handoff template, and rules/docs layout align with how WISC works in general.

### Patterns to Follow

- **Naming:** snake_case for modules and functions; PascalCase for classes and Pydantic models. Match existing `grove` package style.
- **Imports:** Use absolute imports from `grove.*`; no relative imports across top-level packages (per ruff ban in pyproject.toml).
- **Typing:** Full annotations; `disallow_untyped_defs` in mypy. Use `pathlib.Path` for paths.
- **Tests:** Pytest markers `@pytest.mark.unit` / `@pytest.mark.integration`; `tmp_path` for temp dirs; mirror `test_placeholder.py` layout.
- **Validation:** Every task ends with a concrete `VALIDATE` command from justfile or pytest.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Foundation — Models and Manifest

Set up Pydantic models and manifest schema so registry, analyzer, and composer can share structured data.

**Intent Lock**

- Source of truth: This plan (Phase 1), `.ai/RULES.md` (typing, no silent fallbacks). Manifest schema is defined in this plan (OUTPUT CONTRACT, Phase 1 tasks); `.ai/SPECS/003-grove-cli/PRD.md` is optional if present.
- Must: All new code under `src/grove/`; models in `core/models.py`; manifest schema versioned and documented
- Must Not: No unvalidated dicts for manifest or plan; no bare `dict` return types where a model exists
- Acceptance gates: `just types`, `just lint`, `just test` (tests for model validation and manifest round-trip)

**Tasks:**

- [x] CREATE `src/grove/core/__init__.py` and export public models
- [x] CREATE `src/grove/core/models.py` with ProjectProfile, PackManifest (from pack.yaml), InstallPlan, PlannedFile, ManifestState (manifest.toml shape)
- [x] CREATE `src/grove/core/manifest.py` with load/save for manifest; schema matching PRD (grove version, project root, analysis summary, installed packs, generated_files list)
- [x] ADD unit tests for models (valid/invalid manifest, plan serialization)
- [x] VALIDATE: `just types && just lint && just test`

### Phase 2: Pack Registry and Loader

Discover and load pack manifests from built-in pack directories; no file writing yet.

**Intent Lock**

- Source of truth: This plan (Phase 2), pack manifest schema in Phase 1 models
- Must: Registry discovers packs from `src/grove/packs/builtins/` (or configurable path); each pack has a manifest file (e.g. pack.yaml)
- Must Not: No hard-coded pack names in registry logic; no writing to repo
- Acceptance gates: Unit tests that load Base and Python packs and assert metadata; `just types && just lint && just test`

**Tasks:**

- [x] CREATE `src/grove/packs/__init__.py`
- [x] CREATE `src/grove/packs/loader.py` — load single pack manifest, resolve template paths relative to pack root
- [x] CREATE pack manifest schema (in models or loader) for id, name, version, depends_on, compatible_with, activates_when, contributes (templates, setup_questions). Support path triggers for rules (e.g. contributes.rules[].paths) so scoped rules align with Grove Optimize (on-demand by path; see docs/concept.md).
- [x] CREATE `src/grove/core/registry.py` — discover packs in builtins dir, return list of PackManifest; resolve dependencies (base required)
- [x] CREATE `src/grove/packs/builtins/base/` directory and `pack.toml` for Base Pack with minimal metadata and template list (see NOTES: builtins use TOML; loader may support YAML too)
- [x] CREATE `src/grove/packs/builtins/python/` directory and `pack.toml` for Python pack, depends_on base
- [x] ADD unit tests: registry returns base + python when both present; dependency order correct
- [x] VALIDATE: `just types && just lint && just test`

### Phase 3: Analyzer and Detectors

Implement repo analyzer that produces ProjectProfile for composer and templates.

**Intent Lock**

- Source of truth: This plan (Phase 3), Phase 1 ProjectProfile model
- Must: Analyzer runs detectors (e.g. pyproject, uv, pytest, ruff, mypy); returns single ProjectProfile with confidence/evidence where useful
- Must Not: No mutation of repo; no network calls in MVP detectors
- Acceptance gates: Unit tests for each detector and engine; profile populated for a fixture repo with pyproject.toml + uv

**Detector robustness (non-brittle)**

- **Evidence-only population:** Set `test_framework`, `tools`, and other optional fields only when there is explicit config or file evidence. Do not infer or default (e.g. do not set `test_framework = "pytest"` just because it’s a Python repo). Leave field empty/default when no evidence.
- **Documented detection rules:** Each detector must document what it considers “present” (e.g. pytest: `[tool.pytest.ini_options]` or pytest in dependencies; ruff: `[tool.ruff]` or `.ruff.toml`; mypy: `[tool.mypy]` or `mypy.ini`). Prefer standard locations (pyproject.toml `[project]`, `[tool.*]`) over ad-hoc path assumptions.
- **No silent fallbacks:** If a required field for a detector is missing or invalid, do not guess; skip that contribution or fail with a clear, field-specific error per .ai/RULES.md.
- **Single source of truth:** Detection rules live in detector code/docstrings (or a single spec) so they stay maintainable and reviewable.

**Tasks:**

- [x] CREATE `src/grove/analyzer/__init__.py`
- [x] CREATE `src/grove/analyzer/models.py` (or use core.models) — DetectedFact, confidence, evidence
- [x] CREATE `src/grove/analyzer/detectors/base.py` — base detector protocol/ABC
- [x] CREATE detectors: pyproject (language, name), uv (package_manager), pytest, ruff, mypy (tools)
- [x] CREATE `src/grove/analyzer/engine.py` — run all detectors, merge into ProjectProfile
- [x] ADD unit tests: engine on fixture dir with pyproject.toml returns python + uv; optional pytest/ruff/mypy from config
- [x] VALIDATE: `just types && just lint && just test`

### Phase 4: Composer and Install Plan

Compute install plan from ProjectProfile + selected pack ids + registry.

**Intent Lock**

- Source of truth: This plan (Phase 4), Phase 1 InstallPlan/PlannedFile, Phase 2 registry; `.ai/RULES.md` (no silent fallbacks, validate required fields).
- Must: Composer takes profile, list of pack ids, install root path; returns InstallPlan (list of PlannedFile with src, dst, variables, managed flag). Resolve template specs from each pack’s `contributes.templates` (paths relative to pack root). For activates_when/compatible_with: either filter (exclude pack or template when profile does not match) or warn (include and surface mismatch); implementation must choose one and document it.
- Must Not: No file I/O in composer; no TUI logic; no silent fallback for missing pack id (fail with clear error).
- Acceptance gates: Unit tests: (1) plan includes Base + Python files when both selected (per pack contributes.templates); (2) variables include project_name, package_manager, test_framework from profile; (3) plan.install_root and plan.files structure correct. Run `just types && just lint && just test`.

**Tasks:**

- [x] CREATE `src/grove/core/composer.py` — input: profile, selected_packs, install_root; output: InstallPlan
- [x] Resolve template specs from selected packs; apply activates_when/compatible_with to filter or warn
- [x] Compute variables for each template from profile and pack contributes
- [x] ADD unit tests: plan has expected .grove/ paths; variables populated
- [x] VALIDATE: `just types && just lint && just test`

### Phase 5: Renderer and File Operations

Render templates to content; write files with preview and collision handling.

**Intent Lock**

- Source of truth: This plan (Phase 5), .ai/RULES.md (no silent overwrite)
- Must: Renderer fills templates with variable dict; FileOps writes PlannedFiles to disk, supports dry_run and preview (list of path + content or diff)
- Must Not: No overwrite without explicit overwrite/keep/rename decision in API
- Acceptance gates: Unit tests: renderer produces expected content; file_ops dry_run does not write; file_ops apply creates files and manifest

**Tasks:**

- [x] CREATE `src/grove/core/renderer.py` — render(template_path, variables) -> str; use Jinja2 or minimal engine
- [x] CREATE `src/grove/core/file_ops.py` — preview(plan) -> list of (path, content); apply(plan, manifest, options) -> write files + update manifest
- [x] Handle collision: if path exists, require caller to pass strategy (overwrite | skip | rename) or fail
- [x] ADD dependency: jinja2 (and pyyaml if pack manifests are YAML) in pyproject.toml
- [x] ADD unit tests: renderer with mock template; file_ops dry_run; file_ops apply on tmp_path
- [x] VALIDATE: `just types && just lint && just test`

### Phase 6: CLI Entry and End-to-End Init

Wire CLI entry point and non-interactive init that runs analyzer -> composer -> file_ops -> manifest save.

**Intent Lock**

- Source of truth: This plan (Phase 6), .ai/REF/project-types/cli-tool.md (deterministic success/failure, explicit errors)
- Must: CLI command `grove init` (or `grove init --non-interactive`); accepts --root, --pack, --dry-run; runs full pipeline and writes .grove/ + manifest
- Must Not: No interactive prompts in Phase 1; no silent fallbacks for missing required args
- Acceptance gates: Integration test: run `grove init` in fixture repo, assert .grove/GROVE.md (or equivalent), .grove/manifest.toml, and manifest lists installed packs

**Tasks:**

- [x] ADD Typer (or argparse) to pyproject.toml dependencies; add console_scripts entry point `grove`
- [x] CREATE `src/grove/cli/__init__.py` and `src/grove/cli/app.py` — Typer app, `init` command with --root, --pack (multiple), --dry-run
- [x] Wire: init invokes analyzer on cwd (or --root), composer with default or specified packs, renderer + file_ops, manifest save
- [x] CREATE Base Pack templates: GROVE.md.j2, manifest.toml template, plans/ handoffs/ decisions/ dirs
- [x] **Align Base Pack with docs/concept.md:** Read `docs/concept.md` in full; ensure GROVE.md.j2 describes the five pillars (G/R/O/V/E), layered context (Tier 1/2/3), and mental model; handoff template matches structure (Goal, Completed, Next Steps, Key Decisions, Dead Ends, Files Changed, Current State, Recommended first action); plan template supports execute-style consumption.
- [x] CREATE Python pack templates: rules/python.md.j2, one skill template
- [x] ADD integration test: fixture repo (pyproject.toml), run `uv run grove init --dry-run`, then without dry-run; assert .grove/ structure and manifest
- [x] VALIDATE: `just quality && just test`

---

## STEP-BY-STEP TASKS (Summary for Execution Agent)

Execute in phase order. Each phase’s tasks are atomic and testable.

### Phase 1

- **CREATE** `src/grove/core/__init__.py`, `core/models.py`, `core/manifest.py`
- **IMPLEMENT**: Pydantic models (ProjectProfile, PackManifest, InstallPlan, ManifestState); manifest load/save
- **VALIDATE**: `just types && just lint && just test`

### Phase 2

- **CREATE** `src/grove/packs/loader.py`, `core/registry.py`, `packs/builtins/base/`, `packs/builtins/python/` with pack manifests
- **IMPLEMENT**: Registry discovers packs, loads manifest, resolves deps
- **VALIDATE**: `just types && just lint && just test`

### Phase 3

- **CREATE** `src/grove/analyzer/engine.py`, `analyzer/detectors/*`
- **IMPLEMENT**: Detectors for pyproject, uv, pytest, ruff, mypy; engine merges into ProjectProfile
- **VALIDATE**: `just types && just lint && just test`

### Phase 4

- **CREATE** `src/grove/core/composer.py`
- **IMPLEMENT**: Composer(profile, selected_packs, install_root) -> InstallPlan with variables
- **VALIDATE**: `just types && just lint && just test`

### Phase 5

- **CREATE** `src/grove/core/renderer.py`, `core/file_ops.py`; ADD jinja2 (and pyyaml) deps
- **IMPLEMENT**: Render templates; file_ops preview/apply with collision handling
- **VALIDATE**: `just types && just lint && just test`

### Phase 6

- **ADD** Typer + console_scripts entry point; **CREATE** `src/grove/cli/app.py`, Base and Python pack templates
- **IMPLEMENT**: `grove init` command; full pipeline; integration test
- **VALIDATE**: `just quality && just test`

---

## TESTING STRATEGY

### Unit Tests

- Models: valid/invalid manifest, InstallPlan serialization, PackManifest from YAML/TOML
- Registry: discovery, dependency order, missing base fails
- Analyzer: each detector returns expected facts; engine merges
- Composer: plan contains expected paths and variables
- Renderer: variable substitution, missing variable fails
- File_ops: dry_run no write; apply creates files; collision requires strategy

### Integration Tests

- One test: temporary repo with pyproject.toml, run `grove init` (or subprocess), assert `.grove/` exists, `manifest.toml` present and lists base + python

### Edge Cases

- Empty repo: analyzer returns minimal profile; init still creates Base
- Repo with existing .grove/: collision path; test skip/overwrite behavior
- Missing pack dependency: composer or registry fails with clear error

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

- `just format-check`
- `just lint-check`

### Level 2: Types

- `just types`

### Level 3: Unit Tests

- `just test`

### Level 4: Full Gate

- `just quality && just test`

### Level 5: Manual

- From repo root: `uv run grove init --dry-run` (after Phase 6); then `uv run grove init` and inspect `.grove/` and `.grove/manifest.toml`

---

## OUTPUT CONTRACT (Required For User-Visible Features)

- Exact output artifacts:
  - `.grove/` directory under project root (or --root)
  - `.grove/manifest.toml` with [grove], [project], [packs], [[generated_files]]
  - `.grove/GROVE.md`, `.grove/plans/`, `.grove/handoffs/`, `.grove/decisions/`, `.grove/rules/`, `.grove/skills/` as per installed packs
- Verification commands:
  - `uv run grove init --dry-run` (no write, exit 0)
  - `uv run grove init` then `test -f .grove/manifest.toml` and `grep -q 'packs' .grove/manifest.toml`

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)

- A human can directly verify completion by:
  - Running `uv run grove init` in a Python repo and opening `.grove/manifest.toml` and `.grove/GROVE.md`
  - Confirming manifest lists installed packs and generated files and that Base + Python content is present

## INPUT/PREREQUISITE PROVENANCE (Required When Applicable)

- Generated during this feature: `.grove/` and `.grove/manifest.toml` via `uv run grove init`
- Pre-existing: pyproject.toml (or fixture); no external API

---

## ACCEPTANCE CRITERIA

- [x] All six phases implemented in order; each phase’s validation passes before the next
- [x] `just quality && just test` passes
- [x] Unit tests for registry, analyzer, composer, renderer, manifest, file_ops
- [x] At least one integration test: init on fixture repo, assert .grove/ and manifest
- [x] CLI `grove init` runs end-to-end with --dry-run and without
- [x] No regressions in existing tests (test_placeholder)
- [x] Code follows project conventions (ruff, mypy, no relative imports from grove)
- [x] Output contract and Definition of Visible Done are satisfied

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each phase validation passed before proceeding
- [x] Full test suite passes (unit + integration)
- [x] No lint or type errors
- [x] Manual run of `grove init` confirms .grove/ and manifest
- [x] Acceptance criteria all met

---

## EXECUTION REPORT

(Append here as phases complete: command run, pass/fail, artifact verified.)

### Phase 1: Foundation — Models and Manifest (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (created/verified).
- **Intent lock:** Phase 1 Intent Lock present; phase-intent-check run in prior session.
- **Tasks completed:**
  - Created `src/grove/core/__init__.py` exporting InstallPlan, ManifestState, PackManifest, PlannedFile, ProjectProfile, load_manifest, save_manifest.
  - Created `src/grove/core/models.py` with ProjectProfile, PackManifest, InstallPlan, PlannedFile, ManifestState (GroveSection, ProjectSection, InstalledPackRecord, GeneratedFileRecord). Schema version 1 documented in manifest.py and models.
  - Created `src/grove/core/manifest.py` with load_manifest/save_manifest; TOML [grove], [project], [packs], [[generated_files]]; schema version check on load.
  - Added `tests/unit/core/test_models.py` (PackManifest, ProjectProfile, PlannedFile, InstallPlan, ManifestState validation and serialization).
  - Added `tests/unit/core/test_manifest.py` (round-trip, missing file, invalid sections).
- **Dependencies added:** pydantic>=2.0, tomli-w>=1.0.0 (pyproject.toml).
- **Validation:**
  - `just types` — pass (mypy -p grove).
  - `just lint` — pass (ruff check).
  - `just test` — pass (17 tests, including unit tests for models and manifest round-trip).
- **Artifacts:** No user-facing artifacts; core package and tests only.

### Phase 2: Pack Registry and Loader (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (unchanged).
- **Intent lock:** Phase 2 Intent Lock present; phase-intent-check run in prior session.
- **Tasks completed:**
  - Created `src/grove/packs/__init__.py` exporting load_pack_manifest.
  - Created `src/grove/packs/loader.py`: load_pack_manifest(pack_root), discovery order pack.toml then pack.yaml/pack.yml (TOML only implemented; YAML raises clear error); _parse_pack_toml with contributes.rules[].paths support; template paths relative to pack root by convention.
  - Pack manifest schema: Phase 1 PackManifest used; loader parses TOML into it; contributes (templates, setup_questions, rules with paths) documented in loader docstring.
  - Created `src/grove/core/registry.py`: discover_packs(builtins_dir=None), default_builtins_dir(); discovers by directory scan (no hard-coded pack names); dependency order (base before python); raises if pack depends on missing pack.
  - Created `src/grove/packs/builtins/base/pack.toml` and `src/grove/packs/builtins/python/pack.toml` (TOML, python depends_on base; python has contributes.rules[].paths).
  - Added `tests/unit/packs/test_loader.py` (load TOML, missing manifest, missing/empty required fields).
  - Added `tests/unit/core/test_registry.py` (default_builtins_dir, discover base+python and metadata, custom dir, dependency order, missing dependency raises, nonexistent dir raises).
- **Dependencies added:** None (tomllib stdlib for pack TOML).
- **Validation:**
  - `just types` — pass.
  - `just lint` — pass.
  - `just test` — pass (28 tests).
- **Artifacts:** No writing to repo; read-only discovery and load.

### Phase 3: Analyzer and Detectors (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (unchanged).
- **Intent lock:** Phase 3 Intent Lock + Detector robustness (evidence-only, documented rules) present.
- **Tasks completed:**
  - Created `src/grove/analyzer/__init__.py` exporting analyze, ProjectProfile.
  - Created `src/grove/analyzer/models.py`: DetectedFact (key, value, confidence, evidence).
  - Created `src/grove/analyzer/detectors/base.py`: DetectorProtocol (detect(repo_root) -> list[DetectedFact]).
  - Created detectors with documented evidence rules: pyproject ([project].name, requires-python, build-system), uv (uv.lock or [tool.uv]), pytest ([tool.pytest.ini_options] → tool.pytest.ini_options, pytest.ini, or deps), ruff ([tool.ruff] or .ruff.toml), mypy ([tool.mypy] or mypy.ini). No mutation, no network.
  - Created `src/grove/analyzer/engine.py`: analyze(repo_root), _apply_fact merge, _facts_to_profile; returns single ProjectProfile.
  - Added `tests/unit/analyzer/test_detectors.py` (each detector: empty dir, config present, evidence-only no guess).
  - Added `tests/unit/analyzer/test_engine.py` (empty dir minimal profile, pyproject name+language, uv, optional pytest/ruff/mypy from config, no tools without config).
- **Dependencies added:** None (tomllib stdlib).
- **Validation:**
  - `just types` — pass.
  - `just lint` — pass.
  - `just test` — pass (43 tests).
- **Artifacts:** Read-only analysis; no repo mutation.

### Phase 4: Composer and Install Plan (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (unchanged).
- **Intent lock:** Phase 4 Intent Lock present; phase-intent-check run in prior session.
- **Tasks completed:**
  - Created `src/grove/core/composer.py`: `compose(profile, selected_pack_ids, install_root, packs)` → InstallPlan. Resolves template specs from each pack’s `contributes.templates` (paths relative to pack root); builds variables from profile (project_name, language, package_manager, test_framework, tools, raw). Compatibility: include all selected packs (no filter/warn in this phase; documented in module).
  - Added `pack_id` to `PlannedFile` in `core/models.py` so renderer can resolve template paths per pack.
  - Exported `compose` from `grove.core`.
  - Added `tests/unit/core/test_composer.py`: plan includes base + python files when both selected; variables include profile fields; plan structure; missing pack id raises; empty selection; base-only.
- **Dependencies added:** None.
- **Validation:**
  - `just types` — pass.
  - `just lint` — pass.
  - `just test` — pass (49 tests).
- **Artifacts:** No file I/O; composer is pure computation.

### Phase 5: Renderer and File Operations (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (unchanged).
- **Intent lock:** Phase 5 Intent Lock present; phase-intent-check run in prior session.
- **Tasks completed:**
  - Created `src/grove/core/renderer.py`: `render(template_path, variables) -> str` using Jinja2 with `StrictUndefined` (no silent fallback for missing variables).
  - Created `src/grove/core/file_ops.py`: `preview(plan, pack_roots) -> list[(Path, str)]`; `apply(plan, manifest, options, pack_roots) -> ManifestState` with `ApplyOptions(dry_run, collision_strategy)`. Collision strategies: overwrite, skip, rename (next available path). No overwrite without explicit strategy.
  - Added `jinja2>=3.1.0` to pyproject.toml (PyYAML deferred per plan NOTES until YAML pack support).
  - Exported `render`, `preview`, `apply`, `ApplyOptions` from `grove.core`.
  - Added `tests/unit/core/test_renderer.py`: variable substitution, conditionals, missing variable raises, template not found raises.
  - Added `tests/unit/core/test_file_ops.py`: preview path+content, missing pack raises, dry_run no write, apply creates files and updates manifest, collision skip/rename/overwrite.
- **Dependencies added:** jinja2>=3.1.0.
- **Validation:**
  - `just types` — pass.
  - `just lint` — pass.
  - `just test` — pass (60 tests).
- **Artifacts:** No user-facing artifacts; renderer and file_ops ready for Phase 6 CLI wire-up.

### Phase 6: CLI Entry and End-to-End Init (completed)

- **Branch:** `feat/001-grove-cli-core-engine` (unchanged).
- **Intent lock:** Phase 6 Intent Lock present; phase-intent-check run in prior session.
- **Tasks completed:**
  - Added Typer and `[project.scripts]` entry point `grove = "grove.cli.app:main"` in pyproject.toml.
  - Created `src/grove/cli/__init__.py` and `src/grove/cli/app.py`: Typer app with callback for help; `init` command with --root, --pack (multiple), --dry-run. Init resolves builtins via importlib.resources as_file, runs analyzer(root) -> compose(profile, selected, install_root, packs) -> apply(plan, manifest, options, pack_roots) -> save_manifest when not dry_run.
  - Base Pack: GROVE.md.j2 (five pillars G/R/O/V/E, Tier 1/2/3, mental model from docs/concept.md); plans/.gitkeep.j2, handoffs/.gitkeep.j2, handoffs/HANDOFF_TEMPLATE.md.j2 (Goal, Completed, Next Steps, Key Decisions, Dead Ends, Files Changed, Current State, Recommended first action), decisions/.gitkeep.j2. Updated base pack.toml contributes.templates.
  - Python pack: rules/python.md.j2, skills/python-testing.md.j2. Updated python pack.toml contributes.templates.
  - Integration tests: tests/integration/test_init.py — dry_run does not create .grove/; init creates .grove/, manifest.toml, GROVE.md and manifest lists base + python (run via python -m grove.cli.app).
- **Dependencies added:** typer>=0.15.0.
- **Validation:**
  - `just quality` — pass.
  - `just test` — pass (62 tests including 2 integration).
- **Artifacts:** `uv run grove init` and `uv run grove init --dry-run`; .grove/ and .grove/manifest.toml per OUTPUT CONTRACT.

---

## NOTES

- Base Pack must stay small (~6–10 files) to avoid process sprawl.
- **Pack manifest format:** Allow both TOML and YAML for flexibility. **Builtins use TOML** (`pack.toml`) for consistency with `.grove/manifest.toml` and existing tooling (tomllib/tomli-w). Loader discovers a pack by presence of `pack.toml` or `pack.yaml`/`pack.yml` (prefer `pack.toml` when both exist). Document discovery order and schema in loader; add PyYAML only when YAML support is implemented.
- Later phases (TUI, add, sync, manage) will reuse registry, analyzer, composer, renderer, file_ops, and manifest.
- **TUI stack:** We use [Textual](https://textual.textualize.io/) for the interactive installer and `grove manage` dashboard. When adding the TUI, add `textual` to dependencies and follow Textual’s App/Screen/Widget model and CSS.
