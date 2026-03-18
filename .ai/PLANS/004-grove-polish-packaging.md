# Feature: Grove CLI — Phase 4 Polish and Packaging

**Source:** Implements Phase 4 of [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) (§12 Implementation Phases). Product authority: that PRD. No doctor stub—doctor is post-MVP when it has real behavior.

Plans 001–003 delivered core engine, TUI init flow, and add/sync/configure (manage mode). This plan delivers **robustness, user-facing docs, and pack author guidance** so the CLI is installable, understandable, and extensible by contributors.

---

## Feature Description

Phase 4 has four deliverables:

1. **Error handling and clear messages** — Audit CLI and core for consistency: all user-facing errors go through `GroveError` subclasses; messages are actionable (what went wrong, what to do). No silent failures or generic "Error: ..." without context.
2. **MkDocs documentation system** — Full documentation site with MkDocs and Material theme: `docs/` as source, `just docs-serve` to browse locally, `just docs-build` / `just docs-check` for build and validation. Nav: Home, GROVE concept, CLI reference, Pack author guide, Development (roadmap, status, debt). Ensures solid adoption via a single, well-structured doc site.
3. **User-facing docs** — README and command help are sufficient for a new user to install, run `grove init` or `grove configure`, and understand init/add/sync/manage. README links to the doc site; extend or refine as needed and ensure `grove --help` / per-command `--help` are accurate.
4. **Pack author guide** — A single doc (`docs/pack-author-guide.md`) that describes the `pack.toml` schema, `contributes` (templates, setup_questions, rules), template conventions (Jinja2, variables from profile and setup answers), and how to add a new builtin pack. Validation: a new contributor can add a new pack by following the guide.

**Out of scope:** `grove doctor` stub (no stubbing; doctor when it has real behavior post-MVP). No changes to manifest schema or core APIs beyond message strings and docs.

---

## User Story

As a developer or pack author
I want clear error messages, accurate CLI/docs, and a pack author guide
So that I can install Grove, use it without guesswork, and add new packs by following documentation.

---

## Problem Statement

After Plan 003 the CLI is feature-complete for MVP but: (1) some errors may be generic or unactionable; (2) README and help text may be minimal or drift from behavior; (3) there is no single place that explains how to create a pack (pack.toml schema, templates, conventions). Phase 4 closes these gaps so the project is robust and contributor-friendly.

---

## Solution Statement

- **Errors:** Review all `GroveError` raise sites and CLI `typer.echo(..., err=True)` paths; ensure each error type has a clear message and, where helpful, a one-line suggestion (e.g. "Run 'grove init' first"). Document in plan any message standards (e.g. "Error: <type>: <what> — <suggestion>").
- **MkDocs:** Add MkDocs + Material theme; `mkdocs.yml` with nav (index, concept, cli, pack-author-guide, dev). `docs/index.md` (home/quick start), `docs/cli.md` (CLI reference), `docs/pack-author-guide.md` (pack schema and conventions). Justfile: `docs-serve`, `docs-build`, `docs-check` (strict build). README links to doc site; `just quality` includes `docs-check`.
- **Docs:** README remains the main user entry; ensure CLI section and Development section are accurate. Verify `grove <cmd> --help` for init, configure, manage, add, sync and fix any mismatches.
- **Pack author guide:** One new file `docs/pack-author-guide.md` (or under `docs/dev/` if preferred). Content: pack layout, required `pack.toml` fields (id, name, version, depends_on, compatible_with, activates_when, contributes), `contributes.templates` (paths relative to pack root, .j2), `contributes.setup_questions` (structure used by TUI), `contributes.rules` (path triggers); template variables (profile + setup answers); how to add a builtin (where to put files, how registry discovers packs). Reference `src/grove/packs/builtins/base/pack.toml` and `src/grove/packs/builtins/python/pack.toml` as examples.
- **Validation:** New contributor can add a new pack following the guide; CLI installable via `uv pip install .` or equivalent (already true; confirm and document in README if missing).

---

## Feature Metadata

**Feature Type:** Enhancement (docs + message polish)
**Estimated Complexity:** Low–Medium
**Primary Systems Affected:** `src/grove/cli/app.py`, `src/grove/exceptions.py`, `src/grove/core/` (error messages only), `README.md`, `mkdocs.yml`, `docs/` (index, cli, pack-author-guide, existing concept + dev), justfile (docs targets)
**Dependencies:** Plans 001–003 done; PRD [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) §12 Phase 4.

---

## Traceability Mapping

- **PRD Phase:** §12 Phase 4 — Polish and packaging (no doctor stub).
- **Roadmap:** To be added as Priority 4 in `docs/dev/roadmap.md` when this plan is started.
- **Debt items:** None. `No SI/DEBT mapping` for this feature.

---

## Branch Setup (Required)

- Plan: `.ai/PLANS/004-grove-polish-packaging.md`
- Branch: `feat/004-grove-polish-packaging`

Commands (executable as written):

```bash
PLAN_FILE=".ai/PLANS/004-grove-polish-packaging.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (read before implementing)

- `src/grove/cli/app.py` — All commands and error handling; init, configure, manage, add, sync; `GroveError` catch and `typer.echo(..., err=True)`.
- `src/grove/exceptions.py` — `GroveError`, `GroveConfigError`, `GroveManifestError`, `GrovePackError`; ensure messages are set at raise sites.
- `src/grove/core/sync.py` — `sync_managed`; `GroveManifestError` and any user-facing messages.
- `src/grove/core/add.py` (and add_impl/add_apply) — Add path errors; `GroveManifestError`, `GrovePackError`.
- `src/grove/packs/loader.py` — `load_pack_manifest`; `FileNotFoundError`, `ValueError` messages; docstring describes pack.toml discovery.
- `src/grove/core/models.py` — `PackManifest` (id, name, version, depends_on, compatible_with, activates_when, contributes); reference for schema doc.
- `src/grove/core/composer.py` — `_template_paths_from_contributes`; contributes.templates list.
- `src/grove/tui/screens/pack_config.py` — `_collect_setup_questions`; structure of setup_questions from contributes.
- `README.md` — Current CLI and Development sections.
- `src/grove/packs/builtins/base/pack.toml` — Minimal base pack example.
- `src/grove/packs/builtins/python/pack.toml` — Pack with depends_on, contributes.templates, contributes.rules.

### New Files to Create

- `docs/pack-author-guide.md` (or `docs/dev/pack-author-guide.md`) — Pack author guide per Solution Statement.

### Relevant Documentation

- [.ai/SPECS/001-grove-cli/PRD.md](../SPECS/001-grove-cli/PRD.md) §12 Phase 4, §6 (architecture), §7 (CLI).
- [.ai/RULES.md](../RULES.md) — Quality gates `just quality && just test`; do not modify justfile/pyproject.toml unless plan allows.

### Patterns to Follow

- **Errors:** Raise `GroveConfigError`/`GroveManifestError`/`GrovePackError` with a short, actionable message. CLI catches `GroveError` and prints `Error: {e}`; message should stand alone.
- **Docs:** Keep README concise; link to pack author guide for pack creation. Use same tone as existing README (brief bullets).

---

## IMPLEMENTATION PLAN

### Phase 1: Error handling and message audit

**Intent Lock**

- **Source of truth:** This plan; PRD §12 Phase 4 (error handling and clear messages).
- **Must:** Every CLI-visible failure path uses a `GroveError` subclass with an actionable message; no silent fallbacks; suggest next step where helpful (e.g. "run 'grove init' first").
- **Must Not:** Change exception hierarchy or add new exception types unless justified; break existing tests.
- **Acceptance gates:** `just quality && just test`; manual scan of `grove init/add/sync/configure/manage` error paths (missing root, no manifest, unknown pack, not TTY) show clear messages.

**Tasks:**

- [ ] Audit `src/grove/exceptions.py`: ensure docstrings describe when each type is used.
- [ ] Audit `src/grove/cli/app.py`: for each command, list raise/catch paths and ensure message is actionable; add or adjust messages as needed.
- [ ] Audit `src/grove/core/sync.py`, `add.py` (and add_impl/add_apply): ensure `GroveManifestError`/`GrovePackError` messages are clear.
- [ ] Audit `src/grove/packs/loader.py`: `FileNotFoundError` and `ValueError` messages (loader is used by core; messages surface to CLI).
- [ ] Optionally add a short "Error message conventions" note in plan or in .ai/REF for future contributors.

### Phase 2a: MkDocs documentation system

**Intent Lock**

- **Source of truth:** This plan; PRD §12 Phase 4 (user-facing docs); goal of solid adoption via well-structured documentation.
- **Must:** MkDocs + Material theme; `mkdocs.yml` with nav covering Home, Concept, CLI reference, Pack author guide, Development (roadmap, status, debt). `just docs-serve`, `just docs-build`, `just docs-check` (strict); `just quality` includes `docs-check`. Docs source in `docs/`; build output in `site/` (gitignored).
- **Must Not:** Change core CLI or pack behavior; break existing `docs/` content (concept.md, dev/).
- **Acceptance gates:** `just docs-build` and `just docs-check` pass; `just quality` passes (includes docs-check); README links to doc site.

**Tasks:**

- [x] Add MkDocs and mkdocs-material to dev dependency group in pyproject.toml.
- [x] CREATE `mkdocs.yml`: site_name, theme material, nav (index, concept, cli, pack-author-guide, dev/roadmap, dev/status, dev/debt).
- [x] CREATE `docs/index.md`: home/quick start, link to concept, CLI, pack guide, dev.
- [x] CREATE `docs/cli.md`: CLI reference (init, configure, manage, add, sync) and error messages.
- [x] Add justfile targets: `docs-build`, `docs-serve`, `docs-check` (mkdocs build --strict). Replace no-op docs-check with real validation.
- [x] UPDATE README: add Documentation section (just docs-serve, docs-build, docs-check); link to docs; add Docs bullet under Development.
- [x] VALIDATE: `just docs-check` and `just quality` pass.

### Phase 2b: User-facing docs (README and command help)

**Intent Lock**

- **Source of truth:** This plan; PRD §12 Phase 4 (user-facing docs).
- **Must:** README CLI section and Development section accurate; each command's `--help` matches behavior; install instructions (uv/pip) present if not already.
- **Must Not:** Remove or shorten existing README content without replacing with equivalent; change CLI behavior.
- **Acceptance gates:** README describes init, configure, manage, add, sync correctly; `uv run grove --help` and `uv run grove <cmd> --help` for each command are correct; `just quality && just test` pass.

**Tasks:**

- [ ] Review README.md: CLI bullets, Development (setup, quality, docs, commit). Add or fix install line (e.g. `uv pip install .` or `pip install -e .`) if missing.
- [ ] Run `grove init --help`, `grove configure --help`, `grove manage --help`, `grove add --help`, `grove sync --help`; diff against actual behavior and fix Typer docstrings in `src/grove/cli/app.py` if needed.
- [ ] Ensure no stale references (e.g. "grove doctor" only in future/post-MVP context if at all).

### Phase 3: Pack author guide

**Intent Lock**

- **Source of truth:** This plan; PRD §12 Phase 4 (pack author guide); `src/grove/core/models.py` (PackManifest); `src/grove/packs/loader.py`; composer/renderer/template usage.
- **Must:** Single doc that explains pack.toml schema, contributes (templates, setup_questions, rules), template conventions (Jinja2, variables), and how to add a builtin pack; references base and python packs as examples.
- **Must Not:** Implement new pack features; change loader or composer behavior.
- **Acceptance gates:** A reader can add a new builtin pack by following the guide; `just quality && just test` pass; `just docs-check` (or equivalent) passes if it validates docs.

**Tasks:**

- [ ] CREATE `docs/pack-author-guide.md` (or `docs/dev/pack-author-guide.md`): structure per Solution Statement (pack layout, pack.toml fields, contributes, template conventions, adding a builtin). Use base and python pack.toml + directory layout as examples.
- [ ] Cross-link README to pack author guide (e.g. under Development: "To add a new pack, see docs/pack-author-guide.md" or similar).
- [ ] VALIDATE: run through steps in the guide mentally or in a scratch dir to ensure instructions are complete (discovery order pack.toml/pack.yaml/pack.yml; YAML not supported yet—note in guide).

### Phase 4: Validation and packaging confirmation

**Intent Lock**

- **Source of truth:** PRD §12 Phase 4 validation: "New contributor can add a new pack following the guide; CLI installable via uv/pip."
- **Must:** Final gate `just quality && just test`; confirm install path (e.g. `uv pip install .`) works and is documented.
- **Must Not:** Introduce new dependencies or change pyproject.toml build backend.
- **Acceptance gates:** `just quality && just test` pass; README or pack guide mentions install; roadmap/status updated when plan is complete.

**Tasks:**

- [ ] Run `just quality && just test`; fix any regressions.
- [ ] Confirm install: `uv pip install .` (or `pip install -e .`) and run `grove --help` from a clean env; document in README if not already.
- [ ] Update `docs/dev/roadmap.md`: add Priority 4 "Phase 4: Polish and packaging" with status Next (or Done when complete); link to this plan.
- [ ] Update `docs/dev/status.md`: set Current Focus to this plan while in progress; move to Recently Completed when done; add diary entry.

---

## STEP-BY-STEP TASKS

Execute in order. Validate after each step where applicable.

### Phase 1: Error handling and message audit

1. **READ** `src/grove/exceptions.py` — Ensure each exception docstring states when it is raised. **VALIDATE:** No code change required if already clear.
2. **AUDIT** `src/grove/cli/app.py` — For init, configure, manage, add, sync: list every `raise typer.Exit(1)` and preceding `GroveError`/message. Ensure message includes what went wrong and, where possible, what to do (e.g. "No Grove manifest; run 'grove init' first"). **UPDATE** any message that is generic or misleading. **VALIDATE:** `just quality && just test`; manually run error paths (e.g. `grove add python --root /nonexistent`, `grove sync --root /tmp` with no manifest).
3. **AUDIT** `src/grove/core/sync.py` — `GroveManifestError` and any user-facing strings; same clarity standard. **VALIDATE:** `just test`.
4. **AUDIT** `src/grove/core/add.py` and add_impl/add_apply — `GroveManifestError`/`GrovePackError` messages. **VALIDATE:** `just test`.
5. **AUDIT** `src/grove/packs/loader.py` — `FileNotFoundError` and `ValueError` messages. **VALIDATE:** `just test`.

### Phase 2a: MkDocs system

6. **ADD** MkDocs + mkdocs-material to dev dependency group in `pyproject.toml`. **CREATE** `mkdocs.yml` (Material theme, nav: index, concept, cli, pack-author-guide, dev/roadmap, dev/status, dev/debt). **CREATE** `docs/index.md` (home, quick start). **CREATE** `docs/cli.md` (CLI reference). **UPDATE** justfile: `docs-build`, `docs-serve`, `docs-check` (mkdocs build --strict). **UPDATE** README: Documentation section, link to docs. **VALIDATE:** `just docs-check` and `just quality`. — **DONE:** 2026-03-17; Execution Report entry above.

### Phase 2b: User-facing docs (README and command help)

7. **READ** `README.md` — Check CLI section and Development section. **UPDATE:** Add install instruction if missing. Fix any inaccuracy. **VALIDATE:** manual read-through.
8. **RUN** `uv run grove init --help`, etc. **UPDATE** docstrings in `src/grove/cli/app.py` for any command where help text does not match behavior. **VALIDATE:** `just quality && just test`.

### Phase 3: Pack author guide

9. **CREATE** `docs/pack-author-guide.md` — Sections: Overview; Pack layout (directory, pack.toml location); pack.toml schema (id, name, version, depends_on, compatible_with, activates_when, [contributes]); contributes.templates (list of paths relative to pack root, .j2); contributes.setup_questions (structure for TUI); contributes.rules (path triggers, e.g. [[contributes.rules]] paths = [...]); Template conventions (Jinja2, variables from profile and setup answers); Adding a builtin pack (where to put pack under src/grove/packs/builtins/, discovery). Reference `src/grove/packs/builtins/base/pack.toml` and `src/grove/packs/builtins/python/pack.toml`. Note: YAML pack manifests not yet supported. **VALIDATE:** `just quality && just test`; `just docs-check`. *(Already created in Phase 2a; review/expand here if needed.)*
10. **UPDATE** `README.md` — Add one line under Development (or CLI) linking to pack author guide for creating packs. **VALIDATE:** `just quality && just test`. *(README already links to docs site which includes pack guide.)*

### Phase 4: Validation and packaging confirmation

11. **RUN** `just quality && just test`; fix any issues. **VALIDATE:** All pass.
12. **CONFIRM** install: from repo root, `uv pip install .` (or equivalent); run `grove --help` in a clean env. **UPDATE** README if install step was missing or wrong.
13. **UPDATE** `docs/dev/roadmap.md` — Add row: Priority 4 | Phase 4: Polish and packaging | Next (or Done) | Link to this plan. **UPDATE** `docs/dev/status.md` — Current focus = this plan; diary entry. **VALIDATE:** `just status-ready`.

---

## TESTING STRATEGY

- No new test files required unless we add explicit tests for error message content (optional). Existing integration tests already cover error paths (no manifest, unknown pack, etc.).
- If we change any error message string, ensure integration tests that assert on stderr use substrings or documented constants rather than brittle exact match (per .ai/RULES.md).

### Edge Cases

- Commands with invalid --root, missing manifest, unknown pack, non-TTY for configure/manage: all must print a clear, actionable message.

---

## VALIDATION COMMANDS

### Level 1: Lint and types

- `just lint` — pass
- `just format-check` — pass
- `just types` — pass

### Level 2: Full quality and tests

- `just quality && just test` — pass

### Level 3: Docs and status

- `just docs-check` — pass
- `just status-ready` — pass

### Level 4: Manual

- Run `grove init --help`, `grove configure --help`, `grove manage --help`, `grove add --help`, `grove sync --help` and confirm accuracy.
- Run error paths: `grove add python --root /nonexistent`; `grove sync --root <tmp_path_without_manifest>`; confirm messages are clear.
- Follow pack author guide in a scratch directory to add a minimal pack and confirm steps work.

---

## OUTPUT CONTRACT

- **Artifacts:** README.md (updated if needed); docs/pack-author-guide.md (new); docs/dev/roadmap.md and docs/dev/status.md (updated); CLI docstrings and error messages in src/grove.
- **Verification:** `just quality && just test`; `grove <cmd> --help` for each command; manual error-path and install check.

---

## DEFINITION OF VISIBLE DONE

- A human can: (1) read README and install Grove with the documented command; (2) run any CLI command and see accurate --help; (3) hit an error (e.g. no manifest) and see a clear, actionable message; (4) open docs/pack-author-guide.md and follow it to add a new builtin pack.

---

## ACCEPTANCE CRITERIA

- [ ] All CLI and core user-facing error messages are clear and actionable.
- [ ] README CLI and Development sections are accurate; install path documented.
- [ ] Pack author guide exists and describes pack.toml schema, contributes, templates, and adding a builtin.
- [ ] README links to pack author guide for pack creation.
- [ ] `just quality && just test` pass.
- [ ] Roadmap and status updated; new contributor can add a pack by following the guide.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] `just quality && just test` passes
- [ ] Manual check: error paths and --help accurate; install works
- [ ] Pack author guide reviewed for completeness
- [ ] Acceptance criteria met

---

## NOTES

- Pack discovery: builtins live under `src/grove/packs/builtins/`; registry uses `get_builtin_pack_roots_and_packs()` (cli/app.py) and loader loads pack.toml (pack.yaml/pack.yml discovered but YAML not yet supported).
- Template variables: composer and renderer pass profile (ProjectProfile) and setup answers; see composer.py and renderer.py for how variables are merged into template context.
- No doctor stub: PRD updated to exclude optional doctor stub; doctor will be added post-MVP when it has real behavior.

---

## Execution Report

### Phase 2a: MkDocs documentation system — completed 2026-03-17

- **Branch:** (implemented on current branch; plan 004 not yet started on feature branch)
- **Phase intent check:** Phase 2a Intent Lock satisfied; MkDocs + Material theme, nav covering Home, Concept, CLI, Pack author guide, Development; `just docs-serve`, `just docs-build`, `just docs-check`; `just quality` includes docs-check.
- **Completed tasks:**
  - MkDocs and mkdocs-material added to dev dependency group in pyproject.toml.
  - Created `mkdocs.yml` (Material theme, nav: index, concept, cli, pack-author-guide, dev/roadmap, dev/status, dev/debt/debt_tracker).
  - Created `docs/index.md` (home, quick start, next steps).
  - Created `docs/cli.md` (CLI reference for all commands and error messages).
  - Created `docs/pack-author-guide.md` (pack layout, pack.toml schema, contributes, template conventions, adding a builtin; referenced in Phase 3 but delivered early with MkDocs).
  - Justfile: `docs-build`, `docs-serve`, `docs-check` (mkdocs build --strict); replaced no-op docs-check.
  - README: Documentation section (just docs-serve, docs-build, docs-check), link to docs; Docs bullet under Development.
- **Files created:** `mkdocs.yml`, `docs/index.md`, `docs/cli.md`, `docs/pack-author-guide.md`.
- **Files modified:** `pyproject.toml` (dev deps), `justfile` (docs targets), `README.md` (Documentation section, Development), `.ai/PLANS/004-grove-polish-packaging.md` (deliverables, Phase 2a/2b, step-by-step, this Execution Report).
- **Validation:** `just docs-check` and `just quality` pass. `just docs-serve` serves site at http://127.0.0.1:8000.

*(Append further phases here as they complete.)*
