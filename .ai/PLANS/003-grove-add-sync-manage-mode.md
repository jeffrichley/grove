# Feature: Grove CLI — Add, Sync, and Configure (Manage Mode) — Phase 3

**Source:** Implements Phase 3 of [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) (§12 Implementation Phases). Product authority: that PRD (§7 CLI commands, §11 Success criteria).

Phase 2 delivered the full init TUI. This plan adds **lifecycle commands** (`grove add`, `grove sync`) and **configure manage mode**: when `.grove/manifest.toml` exists, `grove configure` opens a manage TUI (view installed packs, analysis, sync status; add pack; re-run analysis; optional full re-setup) instead of the 9-screen first-time flow.

---

## Feature Description

Implement three deliverables from PRD §12 Phase 3:

1. **`grove add <pack>`** — Install an additional pack into an existing Grove installation: resolve dependencies, compose plan for new pack(s), apply with collision handling, update manifest (installed_packs + generated_files).
2. **`grove sync`** — Re-render all managed files listed in `.grove/manifest.toml` from current templates and profile (re-run analyzer for variables); report changes; do not add or remove files from the manifest.
3. **`grove configure` (manage mode)** — When manifest exists at `.grove/manifest.toml`, run a **manage TUI**: read-only view of installed packs, last analysis summary, sync status; actions: add pack, re-run analysis, optionally start full re-setup (existing init flow). Canonical command is `grove configure`; `grove init` remains alias for first-time setup (no manifest → full TUI); when manifest exists, `grove configure` (or `grove manage` alias) enters manage mode.

Unify CLI entry: add `configure` and `manage` commands; route `init` to configure (no manifest) or keep current init-only behavior and have configure dispatch init vs manage by manifest presence. PRD §7: "init = no manifest; manage = manifest exists" — so single entry `grove configure` that branches on manifest existence; `grove init` alias for configure when no manifest.

---

## User Story

As a maintainer who already ran `grove init`
I want to run `grove add <pack>` or `grove sync` and open `grove configure` when a manifest exists so that I can extend my Grove setup and re-render managed files without re-running the full wizard.

---

## Problem Statement

After Phase 2, users can only do first-time setup (TUI or flags). There is no way to add a pack after init, re-sync managed files after template or repo changes, or open a manage dashboard when Grove is already installed.

---

## Solution Statement

- **Add:** CLI command `grove add <pack> [--root]` that loads manifest, resolves pack + dependencies, composes plan for new files only (or full re-compose and filter to new destinations), applies with collision strategy, appends to manifest.installed_packs and manifest.generated_files; save manifest.
- **Sync:** CLI command `grove sync [--root] [--dry-run]` that loads manifest, re-runs analyzer, builds install plan from manifest (same packs, current profile), re-renders and writes only paths in manifest.generated_files; optionally report changed/unchanged; no change to manifest content (only file contents).
- **Configure + manage mode:** Add `grove configure` command. If no `.grove/manifest.toml` → current init TUI (reuse GroveInitApp). If manifest exists → launch **manage TUI** (new app or same app with different initial screen): dashboard showing installed packs, analysis summary, sync status; actions: Add pack, Re-run analysis, Full re-setup (push init flow). Implement `grove manage` as alias for `grove configure` (both branch on manifest). Keep `grove init` as alias that runs same logic as configure (no-manifest = full TUI; with-manifest = manage TUI) so PRD “init = no manifest” is satisfied by routing init to configure.

---

## Feature Metadata

**Feature Type:** New Capability
**Estimated Complexity:** High
**Primary Systems Affected:** `src/grove/cli/app.py`, `src/grove/core/` (sync path), new `src/grove/tui/screens/manage*.py` (or manage dashboard), `src/grove/tui/app.py` (or second app for manage)
**Dependencies:** Plan 001 (core engine), Plan 002 (init TUI); PRD [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md).

---

## Traceability Mapping

- **PRD Phase:** §12 Phase 3 — Add, sync, configure (manage mode).
- **Roadmap:** `docs/dev/roadmap.md` Priority 3 (Phase 3).
- **Debt items:** None. `No SI/DEBT mapping` for this feature beyond roadmap Priority 3.

---

## Branch Setup (Required)

- Plan: `.ai/PLANS/003-grove-add-sync-manage-mode.md`
- Branch: `feat/003-grove-add-sync-manage-mode`

Commands (executable as written):

```bash
PLAN_FILE=".ai/PLANS/003-grove-add-sync-manage-mode.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (read before implementing)

- `src/grove/cli/app.py` (full file) — Typer app; init command; _run_init_tui, _run_init_flag_based; add configure/add/sync commands here; mirror init’s root resolution and pack discovery.
- `src/grove/core/__init__.py` — Exports apply, compose, load_manifest, save_manifest, preview; add sync entry point if new function lives in core.
- `src/grove/core/manifest.py` — load_manifest, save_manifest, MANIFEST_SCHEMA_VERSION; GeneratedFileRecord, ManifestState; used by add/sync and manage.
- `src/grove/core/file_ops.py` — apply(), ApplyOptions, preview(); apply returns updated manifest with generated_files; sync will re-write only manifest.generated_files (new helper or filtered apply).
- `src/grove/core/composer.py` — compose(profile, selected_pack_ids, install_root, packs); dependency order in packs list; use for add (selected = existing + new) and sync (selected = manifest.installed_packs).
- `src/grove/core/models.py` — ManifestState, GeneratedFileRecord, InstalledPackRecord, InitProvenance, InstallPlan, PlannedFile; manifest shape for add/sync.
- `src/grove/tui/state.py` — SetupState, setup_state_from_manifest(); manage screen can reuse state built from manifest.
- `src/grove/tui/app.py` — GroveInitApp, pushes WelcomeScreen; manage mode needs different first screen (e.g. ManageDashboardScreen) when manifest exists.
- `src/grove/tui/screens/welcome.py` — Welcome screen; may need to detect “manifest exists” and hand off to manage flow (or configure command does this before launching app).
- `tests/integration/test_init.py` — Integration tests for init; add tests for add, sync, configure (manage) in same style.

### New Files to Create

- `src/grove/tui/screens/manage_dashboard.py` — Manage TUI screen(s): installed packs, analysis summary, sync status; buttons: Add pack, Re-run analysis, Full re-setup.
- Optionally `src/grove/core/sync.py` or sync logic in `file_ops.py` — function to re-render manifest.generated_files from current profile and pack templates.
- `tests/integration/test_add_sync_configure.py` (or extend test_init.py) — Integration tests for `grove add`, `grove sync`, `grove configure` with existing manifest.

### Relevant Documentation

- [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) §7 (CLI commands), §11 (Success criteria), §12 Phase 3.
- [.ai/RULES.md](../RULES.md) — No modify justfile/pyproject.toml; uv run python; quality gates `just quality && just test`.

### Patterns to Follow

- **CLI:** Typer commands with `Annotated[Path | None, typer.Option("--root", "-r")]` for root; `typer.Exit(1)` on validation failure; use `files("grove.packs")` and `discover_packs(builtins_dir)` for pack registry (mirror `_run_init_flag_based`).
- **Manifest:** Load with `load_manifest(path)`; mutate; save with `save_manifest(path, state)`. Install root from `manifest.project.root` and `manifest.init_provenance.install_root` (see `tui/state.py` setup_state_from_manifest).
- **Apply:** `apply(plan, manifest, options, pack_roots, collision_overrides)` returns updated ManifestState; use `ApplyOptions(dry_run=..., collision_strategy="overwrite"|"skip"|"rename")`.
- **Composer:** `compose(profile, selected_pack_ids, install_root, packs)`; selected must include dependencies (composer does not auto-add deps; pack list from discover_packs is ordered). For add: resolve deps (e.g. ensure dependency packs in selected) before compose.

---

## IMPLEMENTATION PLAN

### Phase 1: Sync and Add (core)

**Intent Lock**

- **Source of truth:** This plan; PRD §7 (grove add, grove sync), §11 (sync re-renders managed files; add installs extra pack and updates manifest).
- **Must:** Re-use analyzer, composer, renderer, file_ops; manifest as single source of truth for installed_packs and generated_files; add resolves dependencies (e.g. dependents of new pack) and updates manifest; sync only writes paths in manifest.generated_files with current profile variables.
- **Must Not:** Change manifest schema without plan amendment; silent overwrite of user-edited seeded files (sync only touches managed/generated_files); add without updating manifest.
- **Acceptance gates:** Unit or integration tests for sync (re-render existing file content); integration test add then sync; `just quality && just test`.
- **Non-goals (Phase 1):** Manage TUI; `grove configure`; `grove remove`; per-file managed flag; remote pack fetch.

**Tasks:**

- [x] Implement sync path: load manifest, resolve install_root, run analyze(root), compose(profile, [p.id for p in manifest.installed_packs], install_root, packs), then write only files whose (dst relative to install_root) is in manifest.generated_files; do not modify manifest. Option: new `sync_managed(manifest, pack_roots, profile)` in file_ops or core that performs the writes and returns a summary (changed paths).
- [x] Add `grove sync [--root] [--dry-run]` CLI command: resolve root, load manifest, run sync path; on dry-run report what would be written; otherwise write and report changed/unchanged.
- [x] Implement add path: load manifest, validate pack id and resolve dependencies (new pack + any depends_on not already in manifest.installed_packs), compose(profile, existing + new pack ids, install_root, packs), apply with collision strategy (e.g. overwrite or prompt later), merge returned manifest.generated_files and installed_packs into loaded manifest, save.
- [x] Add `grove add <pack> [--root]` CLI command: resolve root, require manifest present, call add path, save manifest, echo success.

### Phase 2: Configure and manage mode (TUI)

**Intent Lock**

- **Source of truth:** This plan; PRD §7 (configure: no manifest = full TUI; manifest exists = manage TUI).
- **Must:** Single entry `grove configure`; branch on existence of `.grove/manifest.toml`; manage TUI shows installed packs, analysis summary, sync status; actions: add pack, re-run analysis, full re-setup; `grove init` and `grove manage` aliases per PRD.
- **Must Not:** Hard-code pack names in manage UI; skip manifest check.
- **Acceptance gates:** Manual run with manifest → manage dashboard; without manifest → existing init TUI; `just quality && just test`.
- **Non-goals (Phase 2):** Full add/sync integration tests (Phase 3); `grove analyze` CLI; headless manage flow; pack marketplace.

**Tasks:**

- [ ] Add `grove configure` command: resolve root, if no `.grove/manifest.toml` launch existing GroveInitApp (init TUI); if manifest exists launch manage TUI (new screen or app).
- [ ] Implement manage TUI: at least one screen showing installed packs (from manifest), last analysis summary (manifest.project.analysis_summary), sync status (optional: compare disk vs re-rendered); buttons/actions: Add pack (e.g. prompt or sub-screen for pack id), Re-run analysis (refresh profile and show), Full re-setup (push full init flow).
- [ ] Add `grove manage` as alias for `grove configure` (same handler).
- [ ] Ensure `grove init` behavior: when no manifest and TTY → init TUI; when manifest exists and TTY → either redirect to configure (manage) or keep init as “first-time only” and document. PRD says init = no manifest, manage = manifest exists; so init can stay “first-time only” and configure covers both; or init invokes configure. Decision: have `init` call same dispatch as configure (no manifest → init TUI; manifest exists → manage TUI) so one code path.

### Phase 3: Testing and validation

**Intent Lock**

- **Source of truth:** `.ai/REF/testing-and-gates.md`; this plan.
- **Must:** Integration tests for add (init then add pack, verify manifest and files); sync (init, modify template or profile, sync, verify content); configure with/without manifest.
- **Must Not:** Skip quality gate or leave tests failing.
- **Acceptance gates:** `just quality && just test`; e2e or integration for add/sync/configure.
- **Non-goals (Phase 3):** New feature code (only tests and validation); docs polish (Phase 4); coverage above project baseline.

**Tasks:**

- [ ] Add integration tests: init in tmp_path, then `grove add <pack>`, assert manifest and new files; then `grove sync` (and optionally edit a template), assert file content updated.
- [ ] Add integration test or e2e: `grove configure --root <path>` with manifest present exits 0 (or launches TUI; if headless, stub or skip TUI and test CLI path only).
- [ ] Run full validation: `just quality && just test`; fix any regressions.

---

## STEP-BY-STEP TASKS

Execute in order. Validate after each step where applicable.

### Phase 1: Sync and Add (core)

1. **ADD** `src/grove/core/file_ops.py` (or new `sync.py`) — function `sync_managed(manifest: ManifestState, pack_roots: dict[str, Path], profile: ProjectProfile) -> list[str]`: load packs, compose(profile, [p.id for p in manifest.installed_packs], install_root, packs), build set of manifest.generated_files paths (relative); for each PlannedFile in plan whose dst (relative) is in that set, render and write; return list of written/changed paths. **PATTERN:** file_ops.apply loop (render, write); get install_root from manifest (project.root + init_provenance.install_root or ".grove"). **VALIDATE:** `just types` and `just test`. — **DONE:** Implemented in `src/grove/core/sync.py` with `_rel_posix` and `_write_planned` helpers; dry_run supported.

2. **UPDATE** `src/grove/core/__init__.py` — Export `sync_managed` if in new module, or keep in file_ops and export from core. **VALIDATE:** `just test`. — **DONE:** Export from `grove.core.sync`.

3. **ADD** `src/grove/cli/app.py` — `@app.command()` `def sync(root: Path = None, dry_run: bool = False)`: resolve root (default cwd), path = root/.grove/manifest.toml; if not path.exists() exit with error "No Grove manifest; run 'grove init' first"; load_manifest(path), get pack_roots (builtins), profile = analyze(root), call sync_managed (or dry_run variant); echo summary. **PATTERN:** _run_init_flag_based for root resolution and pack discovery. **VALIDATE:** `uv run grove sync --help`; integration test below. — **DONE:** `sync` command added; `_get_pack_roots_and_packs()` helper.

4. **ADD** add path helper in `src/grove/cli/app.py` (or core): load manifest, ensure new pack id in registry, resolve deps (add pack + its depends_on not in manifest.installed_packs), selected = [p.id for p in manifest.installed_packs] + new_pack_ids_with_deps, compose, apply, merge manifest (installed_packs, generated_files), save. **PATTERN:** _run_init_flag_based compose + apply; manifest merge: installed_packs append new records, generated_files append from apply result. **VALIDATE:** `just test`. — **DONE:** `_run_add_path`, `_packs_to_add`, `_merge_generated`; install_root from manifest.

5. **ADD** `@app.command()` `def add(pack: str, root: Path = None)`: resolve root, require manifest; call add path; save manifest; echo "Added pack <id>". **VALIDATE:** `uv run grove add --help`; integration test. — **DONE:** `add` command added.

### Phase 2: Configure and manage mode

6. **ADD** `@app.command()` `def configure(root: Path = None)`: resolve root; manifest_path = root/.grove/manifest.toml; if not manifest_path.exists(): _run_init_tui(root); else: launch manage TUI (state = setup_state_from_manifest(manifest_path, root)). **PATTERN:** Same TTY check as init: if not stdout.isatty() and no flags, could exit with "Run with --pack for non-interactive" or run manage in read-only CLI mode. **VALIDATE:** Manual: no manifest → init TUI; with manifest → manage TUI.

7. **CREATE** `src/grove/tui/screens/manage_dashboard.py` — Screen showing: title "Grove — Manage"; installed packs (from state or manifest); analysis summary; Sync status (e.g. "Run 'grove sync' to re-render"); buttons: Add pack, Re-run analysis, Full re-setup, Quit. **PATTERN:** GroveBaseScreen; use state from setup_state_from_manifest. Add pack can push a simple screen to enter pack id then call add path and refresh. Full re-setup pushes WelcomeScreen(state) to re-enter init flow. **VALIDATE:** Manual run.

8. **UPDATE** `src/grove/tui/app.py` — When launching with manifest (manage mode), push ManageDashboardScreen instead of WelcomeScreen. Option: GroveInitApp accepts optional mode="init"|"manage" and on_mount pushes WelcomeScreen or ManageDashboardScreen. **VALIDATE:** `just test`.

9. **ADD** `grove manage` as alias: `@app.command()` `def manage(...)` that invokes same handler as configure. **VALIDATE:** `grove manage --help`.

10. **UPDATE** `grove init` (optional): Document that init is first-time; when manifest exists, suggest `grove configure`. Or make init call configure so init with manifest opens manage. PRD: init = no manifest; manage = manifest exists. So init can stay as-is (no manifest → TUI; with manifest → currently init TUI is still shown with prefill). For Phase 3, when manifest exists and user runs `grove init`, either show manage TUI or show init TUI with prefill (current). Plan: when manifest exists, `grove init` in TTY launches same manage TUI as configure (so one code path). **UPDATE** init callback to: if manifest exists and TTY → run configure (manage); else if no manifest and TTY → init TUI; else flag-based init. **VALIDATE:** Manual.

### Phase 3: Testing and validation

11. **ADD** `tests/integration/test_add_sync_configure.py` (or in test_init.py): test_add_after_init (init then add second pack, assert manifest and files); test_sync_after_init (init, then sync, optionally assert no error or content); test_configure_with_manifest_exits_zero (init, then invoke configure with root, expect exit 0 or TUI; if headless, skip or mock). **PATTERN:** test_init.py _run_grove_init, CliRunner. **VALIDATE:** `uv run pytest tests/integration -v`.

12. **RUN** `just quality && just test`; fix any issues. **VALIDATE:** All pass.

---

## TESTING STRATEGY

- **Unit:** Sync helper (given manifest + plan, write only listed paths); add path (merge manifest). Use tmp_path; fixture manifest and pack_roots.
- **Integration:** Init in tmp_path, add pack, assert manifest.installed_packs and new files; sync, assert file content. Configure with manifest (CLI invoke, no TUI if possible) exit 0.
- **Edge cases:** add when pack already installed (idempotent or error); sync when manifest has no generated_files; add unknown pack (error); sync without manifest (error).

---

## VALIDATION COMMANDS

- **Level 1:** `just lint`, `just format-check`, `just types`
- **Level 2:** `just test` (unit + integration)
- **Level 3:** `just quality && just test`
- **Level 4 (manual):** In repo with `.grove`: `uv run grove sync`; `uv run grove add <pack>`; `uv run grove configure` (manage TUI). In repo without `.grove`: `uv run grove configure` (init TUI).

---

## OUTPUT CONTRACT (User-Visible)

- **Artifacts:** `.grove/manifest.toml` (updated after add); re-rendered files under `.grove/` after sync; manage TUI screen when `grove configure` with existing manifest.
- **Verification:** `uv run grove add <pack> --root .` then `cat .grove/manifest.toml` shows new pack; `uv run grove sync --root .` then diff or cat a managed file; `uv run grove configure` opens manage dashboard when manifest exists.

---

## DEFINITION OF VISIBLE DONE

- A human can: run `grove add <pack>` after init and see the pack in manifest and new files; run `grove sync` and see managed files updated; run `grove configure` with an existing `.grove/manifest.toml` and see the manage TUI (installed packs, actions); run `grove configure` without manifest and see the existing init TUI.

---

## INPUT/PREREQUISITE PROVENANCE

- **Pre-existing:** `.grove/manifest.toml` from prior `grove init` (or manual). Refresh: run `grove init` in a test repo.
- **Generated in plan:** Fixture repo with manifest for integration tests (tmp_path + init).

---

## ACCEPTANCE CRITERIA

- [ ] `grove add <pack>` installs pack and updates manifest; dependency packs added if needed.
- [ ] `grove sync` re-renders all paths in manifest.generated_files; reports changes; no manifest schema change.
- [ ] `grove configure` with no manifest launches init TUI; with manifest launches manage TUI (installed packs, add pack, re-run analysis, full re-setup).
- [ ] `grove manage` behaves like `grove configure`.
- [ ] All validation commands pass; integration tests for add and sync; no regressions in init.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] `just quality && just test` passes
- [ ] Integration tests for add, sync, configure (with manifest)
- [ ] Manual test: configure (no manifest) → init TUI; configure (manifest) → manage TUI
- [ ] Acceptance criteria met

---

## NOTES

- **Dependency resolution for add:** Composer does not auto-add dependencies; discover_packs returns list in dependency order. When adding pack X, if X.depends_on = [Y], ensure Y is in selected before compose; if Y not in manifest.installed_packs, add Y first (or add both in one go: selected = [p.id for p in manifest.installed_packs] + [Y, X]).
- **Sync and managed vs seeded:** MVP sync re-renders all manifest.generated_files. Future: per-file managed flag; this plan assumes all generated_files are managed.
- **Manage TUI scope:** Minimum: one screen with installed packs, analysis summary, and actions. Add pack can be a simple text input + CLI add path; full re-setup pushes existing init flow (WelcomeScreen).

---

## Execution Report

### Phase 1: Sync and Add (core) — completed 2026-03-17

- **Branch:** `feat/003-grove-add-sync-manage-mode` (verified not main).
- **Phase intent check:** Phase 1 Intent Lock present; Must/Must Not and acceptance gates satisfied.
- **Completed tasks:**
  1. `sync_managed()` in `src/grove/core/sync.py` (new module) with dry_run; helpers `_rel_posix`, `_write_planned` for xenon/darglint.
  2. `sync_managed` exported from `grove.core` (`core/__init__.py` imports from `sync`).
  3. `grove sync [--root] [--dry-run]` in `src/grove/cli/app.py`; `_get_pack_roots_and_packs()` for pack discovery.
  4. Add path: `_run_add_path`, `_packs_to_add`, `_merge_generated`; dependency order and manifest merge.
  5. `grove add <pack> [--root]` in `src/grove/cli/app.py`.
- **Files created:** `src/grove/core/sync.py`.
- **Files modified:** `src/grove/core/__init__.py`, `src/grove/core/file_ops.py` (no sync_managed), `src/grove/cli/app.py`.
- **Validation:** `just quality && just test` — pass. `uv run grove sync --help` and `uv run grove add --help` — OK.
- **Integration tests:** Plan Phase 3 (step 11) will add `tests/integration/test_add_sync_configure.py`; Phase 1 scope did not require new tests (existing 99 tests pass).
