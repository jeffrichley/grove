# Feature: Grove CLI — TUI and Full Init Flow (Phase 2)

**Source:** Implements Phase 2 of [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) (§12 Implementation Phases). Product and UX authority: that PRD (TUI flow §7, success criteria §11).

The core engine (Plan 001) delivers flag-based `grove init`. This plan adds the **interactive TUI path** so users can run `grove configure` (or `grove init`, alias) without flags and step through welcome → analyze → pack selection → config → preview → conflicts → apply. Per PRD, the canonical command is `grove configure`; with no manifest this is the full setup flow; with an existing manifest, configure becomes the “manage” flow (Phase 3).

---

## Feature Description

Add an interactive TUI (Textual) to `grove configure` / `grove init`: multi-screen flow with shared setup state, driven by the existing analyzer, composer, and installer. Keep the existing flag-based path; when no `--pack` (or equivalent) is given and stdout is a TTY, launch the TUI. Deliverables: TUI screens (welcome, analyze, pack selection, pack config, preview, conflicts, finish), shared `SetupState`, and integration with the Phase 1 pipeline so the install matches the manifest. (Canonical command: `grove configure`; `grove init` is an alias for this first-time / full-setup mode.)

---

## User Story

As a developer adopting Grove
I want to run `grove init` with no arguments and complete a short TUI so that I get a minimal, correct Grove setup without editing files by hand or memorizing flags.

---

## Problem Statement

Phase 1 only supports flag-based init (`--root`, `--pack`, `--dry-run`). The PRD requires an interactive path for first-time setup so users can see what was detected, choose packs, answer pack-contributed questions, and preview before applying—without reading CLI help.

---

## Solution Statement

Introduce a Textual TUI app that: (1) shares state (e.g. `SetupState`: root, profile, selected packs, answers, plan); (2) implements the PRD’s first-time setup flow (welcome → repository analysis → core install → recommended packs → pack configuration → components preview → conflicts → final review → finish); (3) uses the existing analyzer, composer, renderer, and file_ops; (4) is invoked from the Typer `init` command (and later `configure`) when interactive mode is chosen (TTY + no conflicting flags). Retain all existing flag-based behavior.

---

## Feature Metadata

**Feature Type:** New Capability
**Estimated Complexity:** High
**Primary Systems Affected:** `src/grove/cli/`, new `src/grove/tui/` (or equivalent), `pyproject.toml` (Textual dep)
**Dependencies:** Plan 001 (core engine); Textual for TUI. PRD: [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md).

---

## Traceability Mapping

- **PRD Phase:** §12 Phase 2 — CLI and init flow.
- **Roadmap:** `docs/dev/roadmap.md` Priority 2 (Phase 2 TUI + full init flow).
- Debt items: None.

---

## Branch Setup (Required)

- Plan: `.ai/PLANS/002-grove-cli-tui-init-flow.md`
- Branch: `feat/002-grove-cli-tui-init-flow`

Commands (executable as written):

```bash
PLAN_FILE=".ai/PLANS/002-grove-cli-tui-init-flow.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## Implementation Plan

This plan is a single phase: **TUI and full init flow**. Lock intent before coding; run `.ai/COMMANDS/phase-intent-check.md` with this plan and the phase heading below if splitting into sub-phases later.

### Phase: TUI and Full Init Flow

Add interactive Textual TUI to `grove init`; preserve existing flag-based path. Shared setup state; screen flow per PRD §7; integration with analyzer, composer, file_ops, manifest.

**Intent Lock**

- **Source of truth:** This plan; [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) §7 (TUI flow), §11 (success criteria), §12 Phase 2; `.ai/RULES.md` (no silent fallbacks, validate required fields); `.ai/REF/project-types/cli-tool.md` (CLI UX).
- **Must:** Use existing analyzer, composer, renderer, file_ops; no hard-coded pack list or question text in TUI (drive from registry/pack manifests); TTY check and flag check before launching TUI; preserve `grove init --root/--pack/--dry-run` behavior unchanged; shared state (e.g. `SetupState`) passed through all screens; install result must match manifest.
- **Must Not:** No silent fallback for missing required state; no skipping PRD screens (welcome → … → finish); no interactive prompts when flags specify full selection; no mutation of repo until user confirms in TUI (preview before apply).
- **Acceptance gates:** Unit tests for `SetupState` and testable TUI logic; `just quality && just test`; manual run of `grove init` (no args) in a real repo with all screens reachable and resulting `.grove/` and `manifest.toml` matching choices; `grove init --pack base --pack python` still works (flag-based, no TUI).

**Acceptance criteria**

- Running `grove init` with no args in a TTY launches the TUI.
- TUI flow: Welcome → Repository analysis → Core install → Recommended packs → Pack configuration → Components preview → Conflicts (if any) → Final review → Finish.
- User can complete the flow and get a valid `.grove/` and `manifest.toml` reflecting selected packs and choices.
- Flag-based init (`--root`, `--pack`, `--dry-run`) unchanged and does not start TUI.

**Non-goals (this phase)**

- `grove add`, `grove sync`, `grove configure` when manifest exists (Phase 3).
- Pack-contributed setup questions UI (can be stubbed or minimal; full dynamic questions in scope but not required for “all screens reachable”).
- Headless/CI mode for TUI flow (optional integration test only).

**Tasks**

- [x] Add Textual dependency; create `src/grove/tui/` (or agreed package) and app entry.
- [x] Define `SetupState` (root, profile, selected pack ids, config answers, install plan, manifest) and pass through screens.
- [x] Implement TUI screens per PRD §7: Welcome → Repository analysis → Core install → Recommended packs → Pack configuration → Components preview → Conflicts → Final review → Finish.
- [x] Wire screens to analyzer (profile), composer (plan from selection + profile), and file_ops + manifest save (apply).
- [x] From Typer `init`: detect TTY and absence of pack-selection flags; launch TUI when interactive, else keep current flag-based flow.
- [x] Manual validation: run `grove init` in a real repo; reach every screen; complete install; verify `.grove/` and manifest match choices.

---

## TUI pages and widgets

Each page is a Textual `Screen`. Widgets are Textual built-ins; layout uses `VerticalScroll`, `Horizontal`, `Grid`, or `Container` as needed. Navigation: **Next** / **Back** buttons (and **Quit** where appropriate); key bindings (e.g. Enter to continue, q to quit) per screen.

| # | Page (PRD §7) | Purpose | Widgets |
|---|----------------|---------|--------|
| 1 | **Welcome** | Explain Grove; confirm repo root; detect existing `.grove/manifest.toml`. | **Static** (markdown or rich text): short blurb on what Grove does. **Input** (read-only or editable): repo root path (default `Path.cwd()`). **Static**: message if `.grove/manifest.toml` exists (e.g. “Existing Grove found; re-run will update.”). **Button**: “Next”, “Quit”. Optional **Footer** with hint (e.g. “Enter = Next”). |
| 2 | **Repository analysis** | Show detector results; allow override. | **DataTable** or **Static** (formatted): language, package manager, test framework, tools (from `ProjectProfile`). **Static** labels per field. Optional **Input**/dropdowns for overrides (or “Edit” → modal). **Button**: “Next”, “Back”, “Re-run analysis”. **Footer**. |
| 3 | **Core install** | Confirm Base Pack; install root; toggles for ADRs, handoffs, scoped rules, memory, skills dir. | **Static**: “Base Pack (required) will be installed.” **Input**: install root (default `.grove`). **Checkbox** (or **Switch**): include ADRs, handoffs, scoped rules, memory, skills dir (defaults from PRD or plan). **Button**: “Next”, “Back”. **Footer**. |
| 4 | **Recommended packs** | Show required / recommended / available / incompatible; toggle selection; view details. | **DataTable** or **Tree**: pack id, name, status (required / recommended / available / incompatible). **Checkbox** per row or selection list: which optional packs to install. **Static** or **Collapsible**: “Details” for selected pack (description, templates). **Button**: “Next”, “Back”. **Footer**. |
| 5 | **Pack configuration** | Dynamic questions from selected packs (e.g. package manager, typing strictness). | **Static**: “Configure selected packs.” **VerticalScroll** of questions: each question = **Label** + **Input** (text), **Select** (single choice), or **Checkbox** (bool), driven by pack `setup_questions`. **Button**: “Next”, “Back”. **Footer**. |
| 6 | **Components preview** | List folders/files to create, existing files, skills to generate; managed vs unmanaged. | **DataTable** or **Tree**: path, type (dir/file), status (new / exists / managed / seeded). **Static** summary: “X files to create, Y existing.” **Button**: “Next”, “Back”. **Footer**. |
| 7 | **Conflicts** | For collisions: overwrite / keep existing / rename / diff. | Shown only if conflicts exist. **DataTable** or **List**: conflicting path + action. **Select** or **RadioSet** per row: Overwrite / Keep existing / Rename / Show diff. **Button**: “Apply choices”, “Back”. **Footer**. |
| 8 | **Final review** | Summary; apply installation. | **Static** (markdown): summary (root, packs, file count, conflict resolution). **Button**: “Apply installation”, “Back”, “Quit”. **Footer**. |
| 9 | **Finish** | Success message; next commands. | **Static** (markdown): “Grove initialized at …” and suggested next commands (`grove doctor`, `grove configure`, `grove sync`). **Button**: “Done” (exit app). **Footer**. |

**Screen checklist**

- [x] 1 — Welcome
- [x] 2 — Repository analysis
- [x] 3 — Core install
- [x] 4 — Recommended packs
- [x] 5 — Pack configuration
- [x] 6 — Components preview
- [x] 7 — Conflicts
- [x] 8 — Final review
- [x] 9 — Finish

**Shared / app-level**

- **Header** (optional): title “Grove init” and step indicator (e.g. “Step 1 of 9”).
- **Footer**: global key hints (e.g. “Enter Next  B Back  Q Quit”).
- **SetupState** passed into each screen (e.g. via app state or dependency injection); screens read/update state and push next screen.

**Widget reference (Textual)**

- `Screen`, `Static`, `Button`, `Input`, `Select`, `Checkbox`, `DataTable`, `Tree`, `Label`, `VerticalScroll`, `Horizontal`, `Container`, `Footer`, `Header`, `RadioSet`. Use `Rich` or markdown-capable `Static` for formatted text. Modals (e.g. for “Show diff”) can use a separate `Screen` or `ModalScreen`.

---

## Required Tests and Gates

- Unit tests for `SetupState` and any pure TUI logic that can be tested without a full TUI run.
- Integration test: optional “headless” or fixture-driven path that exercises the same flow as TUI (e.g. state machine or screen sequence) without displaying.
- Final gate: `just quality && just test`.
- PRD validation: manual run of `grove configure` or `grove init` in a real repo; all screens reachable; install matches manifest (per PRD Phase 2 validation).

---

## Definition of Visible Done

- A human can run `grove configure` or `grove init` (no args) in a terminal, see the TUI, move through welcome → analysis → pack selection → config → preview → conflicts (if any) → apply, and end with a valid `.grove/` and `manifest.toml` that reflect their choices.
- `grove init --root . --pack base --pack python` (or `--dry-run`) still works as today (flag-based, no TUI). When the CLI is extended with `grove configure`, init remains an alias for configure (no-manifest / full-setup mode).

---

## Execution Report

### 2026-03-17 — Phase 2 complete (full TUI flow)

- **Branch:** `feat/002-grove-cli-tui-init-flow` (per Branch Setup).
- **Completed:**
  - All 9 TUI screens: Welcome, Repository analysis, Core install, Recommended packs, Pack configuration, Components preview, Conflicts (if any), Final review, Finish.
  - SetupState extended with conflict_choices, init provenance; state passed through all screens; analyzer, composer, file_ops, manifest save wired.
  - Final review Apply: builds manifest (with InitProvenance), calls file_ops.apply with collision_overrides from conflict_choices, saves manifest, pushes Finish screen.
  - file_ops.apply extended with optional collision_overrides for per-path strategy (overwrite / skip / rename).
  - Provenance: init choices stored in manifest `[init]` for re-run prefill; setup_state_from_manifest used on TUI startup.
- **Validation:** `just quality && just test` — all pass. Manual: `grove init` (no args) in a TTY runs full flow; flag-based `grove init --pack base --pack python` unchanged.
- **Artifacts:** `src/grove/tui/*` (app, state, screens 1–9, CSS), `src/grove/cli/app.py`, `src/grove/core/file_ops.py` (collision_overrides), `tests/unit/tui/test_state.py`, `pyproject.toml` (textual).

### 2026-03-17 — Phase 2 first slice (branch, TUI skeleton, init wiring)

- **Branch:** `feat/002-grove-cli-tui-init-flow` created per Branch Setup.
- **Completed:** Textual dependency; `src/grove/tui/` with app, state, Welcome screen; TTY + flag check in Typer init; unit tests for SetupState.
- **Artifacts:** `src/grove/tui/*`, `src/grove/cli/app.py` (TUI branch + refactor), `tests/unit/tui/test_state.py`, `pyproject.toml` (textual dep).
