# PRD: Grove CLI — Context-Engineering System Installer

**Author:** Derived from Project Grove conversation (2026-03-16)
**Audience:** Product + Engineering
**Status:** Draft v1
**Date:** 2026-03-16
**Related:** [docs/concept.md](../../docs/concept.md) (GROVE framework), chat transcript `tmp/2026-03-16_22-21-33__Project-Grove-Grove-Development-Process__chat.json`

---

## 1. Executive Summary

Grove CLI is a **template-driven installer and lifecycle manager** for the Grove context-engineering system. It does not replace Grove’s philosophy (Grow, Root, Optimize, Verify, Enrich); it **materializes** it into a repo in a minimal, reproducible, and configurable way.

**Core value proposition:** Instead of manually curating a large `.ai`-style tree (rules, commands, plans, specs) that tends to grow out of control, users run a CLI/TUI that analyzes the repo, lets them select which capabilities they want (base + optional packs), and writes a lean `.grove/` structure with the right rules, plans, handoffs, decisions, and **project-specific skills** generated from templates and repo facts. Grove becomes *assembled*, not dumped.

**MVP goal:** Deliver a working Grove CLI that can initialize a Grove installation in a repo via an interactive TUI, driven by a **dynamic pack registry** (no hard-coded menus), with a required Base Pack and at least 2–3 optional capability packs (e.g. Python, CLI, LangGraph), and that records all installed state in a manifest for safe sync, add, and later removal.

---

## 2. Mission

**Mission:** Make Grove the default way to bootstrap and maintain a context-engineering operating system in any software project—reproducible, small by default, and expandable on purpose.

**Core principles:**

1. **Context is the scarce resource.** The CLI exists to prevent context rot and ceremony sprawl, not to add more of it.
2. **Registry-driven, not hard-coded.** Packs, setup questions, templates, and recommendations are data-driven (e.g. `pack.toml`, manifest) so new packs can be added without changing core code.
3. **Manifest-backed lifecycle.** Every install is tracked in `.grove/manifest.toml` so the CLI knows what it owns, can regenerate managed files, detect drift, and remove packs safely.
4. **Analysis informs; user decides.** Repo analysis suggests packs and defaults, but the user can override. No silent assumptions.
5. **Assembled, not dumped.** Start tiny; opt into packs; generate only what is needed; support later expansion.

---

## 3. Target Users

### Primary personas

| Persona | Technical comfort | Key needs |
|--------|-------------------|-----------|
| **Developer adopting Grove** | Intermediate (CLI, YAML/TOML) | One-command setup, clear preview, no surprise overwrites |
| **Project lead / maintainer** | Intermediate to advanced | Reproducible onboarding, consistent rules/skills across repos |
| **Pack author (later)** | Advanced | Add new capability packs without forking the CLI |

### Key pain points addressed

- Manually maintaining dozens of context files (rules, commands, plans) that drift and balloon.
- One-size-fits-all process blobs that don’t match project type (Python vs monorepo vs research).
- No way to “regenerate” or “sync” after repo or tooling changes.
- Skills and rules that are generic instead of grounded in the repo’s real structure and commands.

---

## 4. MVP Scope

### In scope

#### Core functionality

- ✅ CLI entry point: `grove configure` (unified TUI: first-time setup or manage existing), `grove analyze`, `grove add`, `grove sync`. `grove init` and `grove manage` are aliases for `grove configure` (init = no manifest; manage = manifest exists).
- ✅ Interactive TUI (e.g. Textual) for first-time setup: welcome → analyze → core install → pack selection → pack configuration (dynamic questions) → preview → conflicts → apply → finish.
- ✅ Dynamic pack registry: discover base + capability packs from manifests (e.g. `pack.toml`); no hard-coded pack list in TUI.
- ✅ Required Base Pack: always installed; provides `GROVE.md`, `manifest.toml`, `plans/`, `handoffs/`, `decisions/`, skill schema/templates; target ~6–10 files.
- ✅ At least 2–3 optional capability packs (e.g. Python, CLI, LangGraph) with rules + skill templates + contributed setup questions.
- ✅ Repo analyzer: detect language(s), package manager, test/lint/type tools, frameworks (e.g. Typer, LangGraph); output structured `ProjectProfile`; suggest packs from registry rules.
- ✅ Composition/install planner: combine user choices + analysis + pack metadata → compute which files to create/update; resolve dependencies; support preview and dry-run.
- ✅ Template rendering: fill templates (e.g. Jinja2) with variables from analysis and setup answers; support conditional inclusion.
- ✅ Manifest: record installed packs, generated file paths, source template, managed vs seeded, checksums; support `sync` (re-render managed files) and safe `add`/later `remove`.
- ✅ Project-specific skill generation: render skills from pack templates + repo facts (e.g. real test/lint commands, paths) so skills feel native to the repo.

#### Technical and structure

- ✅ Single install root: `.grove/` (configurable in manifest).
- ✅ Clear ownership: managed (Grove regenerates) vs seeded (user edits, don’t overwrite).
- ✅ Conflict handling: on overwrite, support preview/diff, overwrite/keep/rename.

### Out of scope (MVP)

- ❌ `grove remove` (defer to post-MVP; MVP focuses on configure, add, sync).
- ❌ `grove doctor` (defer; optional post-MVP).
- ❌ `grove generate-skill` as a standalone CLI (skill generation can be part of init/add/sync; dedicated command later).
- ❌ Community pack marketplace / remote pack install.
- ❌ Anchored file updates (e.g. inserting blocks into existing README).
- ❌ Pack version migrations and upgrade flows.

---

## 5. User Stories

1. **As a developer**, I want to run `grove configure` (or `grove init`) in a repo and complete a short TUI so that I get a minimal, correct Grove setup without editing files by hand.
2. **As a developer**, I want the TUI to show what was detected (language, tools, frameworks) and what will be installed so that I can correct or accept before any write.
3. **As a developer**, I want to choose only the packs I need (e.g. Base + Python + CLI) so that my `.grove/` stays small and relevant.
4. **As a developer**, I want setup questions (e.g. package manager, validation style) to come from the selected packs automatically so that I don’t see irrelevant options.
5. **As a maintainer**, I want a manifest that tracks what Grove installed so that I can re-run `grove sync` after changing the repo or templates and keep managed files up to date.
6. **As a maintainer**, I want to run `grove add <pack>` or open `grove configure` (manage mode) later so that I can extend Grove without re-running the full setup wizard.
7. **As a developer**, I want generated skills to reference real commands and paths from my repo (e.g. `uv run pytest`, `src/`) so that agents get actionable guidance.

---

## 6. Core Architecture & Patterns

### High-level layers

- **CLI:** Commands (`configure`, `analyze`, `add`, `sync`) call application services; `configure` has two modes—no manifest = full setup flow, manifest exists = manage dashboard; support scripting/CI where useful.
- **TUI:** Multi-screen flow (welcome, analyze, core install, pack selection, pack config, preview, conflicts, finish); state object (e.g. `SetupState`) shared across screens; widgets stay dumb, logic in services.
- **Registry:** Loads pack manifests; answers “what packs exist?”, “what do they require?”, “what setup questions do they contribute?”, “what templates do they generate?”; no hard-coded menus.
- **Analyzer:** Plugin-style detectors (e.g. Python, uv, pytest, ruff, Typer, LangGraph); each emits structured facts + confidence; engine builds a single `ProjectProfile`.
- **Composer:** Combines user selections + analysis + pack metadata; resolves dependencies; produces install plan (files to create/update, variables).
- **Renderer:** Renders templates with variables; supports conditionals and simple inheritance.
- **File ops:** Preview, create dirs, write files, handle collisions (overwrite/keep/rename), dry-run.
- **Lifecycle/state:** Maintain manifest; track installed packs and generated files; support sync and add.

### Directory structure (product layout)

```
.grove/
  GROVE.md           # Core rules (always-loaded)
  manifest.toml      # Installed packs, generated files, options
  plans/
  handoffs/
  decisions/
  rules/             # Scoped rules from packs
  skills/            # Generated + pack-provided skills
  (optional) memory/
  (optional) templates/
```

### Key design patterns

- **Pack as data:** A pack is primarily a manifest (e.g. `pack.toml`) + templates; optional code only for advanced logic. New packs can be added without changing CLI core.
- **Setup questions contributed by packs:** Each pack declares questions (id, type, label, options, default_from_analysis, show_when). TUI aggregates and orders them; only shows questions whose conditions are met.
- **Managed vs seeded files:** Managed = Grove can regenerate; seeded = create once, user edits, don’t overwrite.

---

## 7. Tools / Features

### CLI commands (MVP)

| Command | Purpose |
|---------|---------|
| `grove configure` | **Unified setup and manage.** No `.grove/manifest.toml` → full TUI flow (welcome → … → finish). Manifest exists → manage TUI: view installed packs, analysis, sync status; add pack, re-run analysis, optional full re-setup. Aliases: `grove init` (same as configure when no manifest), `grove manage` (same as configure when manifest exists). |
| `grove analyze` | Inspect repo only; print structured project profile and pack recommendations. |
| `grove add <pack>` | Install an additional pack; resolve deps; render new files; update manifest. |
| `grove sync` | Re-render all managed files from current manifest and templates; report changes. |

### TUI flow (first-time setup)

1. **Welcome** — Explain what Grove does; confirm repo root; detect existing `.grove/manifest.toml`.
2. **Repository analysis** — Run detectors; show language, package manager, frameworks, tools; allow override.
3. **Core install** — Confirm Base Pack; choose install root; toggles for ADRs, handoffs, scoped rules, memory, skills dir.
4. **Recommended packs** — Show required / recommended / available / incompatible from registry; toggle selection; view details.
5. **Pack configuration** — Dynamic questions from selected packs (e.g. package manager, typing strictness, LangGraph style).
6. **Components preview** — List folders/files to create, files that exist, skills to generate; managed vs unmanaged.
7. **Conflicts** — For collisions: overwrite / keep existing / rename / diff.
8. **Final review** — Summary; apply installation.
9. **Finish** — Success message; next commands (`grove doctor`, `grove configure`, `grove sync`).

### Pack model

- **Base pack (required):** GROVE.md, manifest schema, plan/handoff/ADR/skill templates, minimal layout. Must stay small (~6–10 files).
- **Capability packs (optional):** e.g. Python, CLI, LangGraph; add scoped rules, skill templates, setup questions, analyzer references. Dependencies (e.g. LangGraph depends on Python) resolved by composer.

### Skill generation

- Skills are rendered from pack templates + `ProjectProfile` (and optional path scope).
- Include real repo facts: test command, lint command, type checker, key dirs. Outcome: skills are operational and repo-specific, not generic philosophy docs.

---

## 8. Technology Stack

- **Language:** Python 3.12+.
- **CLI:** Typer (or similar) for commands and flags.
- **TUI:** Textual for multi-screen installer and configure (setup / manage) dashboard.
- **Templates:** Jinja2 (or equivalent) wrapped with template descriptors (path, variables, conditions, managed flag).
- **Config/data:** TOML for manifest and pack manifests (e.g. `pack.toml`).
- **Models:** Pydantic for ProjectProfile, PackManifest, SetupQuestion, InstallPlan, ManifestState, etc.
- **Package/build:** pyproject.toml, hatchling; package name `grove` (this repo).
- **Testing:** pytest; unit tests for analyzer, composer, renderer, file ops; integration tests for init/sync with fixture repos.

---

## 9. Security & Configuration

- **Trust:** Treat repo content and user-provided paths as untrusted; no arbitrary code execution from pack templates (templates are render-only; optional hooks if added later must be explicit and documented).
- **Configuration:** Install root and options (e.g. include_adrs, package_manager) stored in `.grove/manifest.toml`; no secrets in manifest; env vars only if needed for future remote/API features.
- **Scope:** MVP is local-only (local packs, local files); no network fetch of packs in MVP.
- **Deployment:** Distributed as Python package; run from repo root; no elevated privileges required.

---

## 10. API Specification

MVP is a CLI/TUI product; no REST API. Internal “API” is the service layer consumed by CLI and TUI (e.g. `Analyzer.run()`, `Composer.plan()`, `Installer.apply()`). Exact signatures and Pydantic schemas to be defined in a technical design doc. Not included in this PRD.

---

## 11. Success Criteria

### MVP success definition

- A developer can run `grove configure` (or `grove init`) in a Python (uv + pytest) repo, complete the TUI with Base + Python + CLI packs, and get a valid `.grove/` with GROVE.md, manifest.toml, rules, plans, handoffs, decisions, and at least one generated skill that references real commands (e.g. `uv run pytest`).
- `grove sync` re-renders managed files without breaking user-edited seeded files.
- `grove add <pack>` installs an extra pack and updates the manifest correctly.
- `grove configure` (with existing manifest) opens a TUI that shows installed packs and allows adding a pack or re-running analysis.
- Adding a new capability pack (e.g. “research”) requires only adding a directory under `packs/builtins/` with `pack.toml` and templates—no changes to TUI screen logic or hard-coded pack lists.

### Functional requirements

- ✅ All MVP CLI commands implemented and callable.
- ✅ TUI flow covers welcome → analyze → pack selection → dynamic questions → preview → apply.
- ✅ Base Pack plus ≥2 optional packs (e.g. Python, CLI) shipped and installable.
- ✅ Manifest tracks every installed file and pack; sync uses it for re-render.
- ✅ Analyzer produces a structured profile that drives recommendations and template variables.
- ✅ Conflict handling (preview/diff/overwrite/keep) for existing files.

### Quality indicators

- Tests for analyzer, composer, renderer, and file ops; at least one end-to-end test for init in a fixture repo.
- No hard-coded pack names or question text in TUI flow logic; both come from registry/manifests.

---

## 12. Implementation Phases

### Phase 1: Core engine (no TUI) — **Done**

- **Goal:** Registry, analyzer, composer, renderer, file ops, manifest read/write; Base Pack and one capability pack (e.g. Python); no interactive UI.
- **Deliverables:** ✅ Pack loader and registry; ✅ Analyzer with 3–5 detectors (Python, uv, pytest, ruff, Typer); ✅ Composer producing install plan; ✅ Template renderer; ✅ File writer with preview/dry-run; ✅ Manifest schema and write; ✅ Base + Python pack with templates.
- **Status:** Implemented. Configure/init is **flag-based**: `grove init` (alias for configure) with `--root`, `--pack`, `--dry-run` (no TUI). Default packs: base, python.
- **Validation:** Unit tests; `grove init` or `grove init --dry-run` produces correct `.grove/` and manifest in fixture repo.

### Phase 2: CLI and configure flow — **Done**

- **Goal:** Full `grove configure` (init mode) with non-interactive (flag-based) and interactive TUI path. Canonical command is `grove configure`; `grove init` retained as alias for first-time / full setup.
- **Deliverables:** ✅ Typer CLI; ✅ TUI screens (welcome, analyze, pack selection, config, preview, conflicts, finish); ✅ Shared setup state; ✅ Integration with composer and installer.
- **Status:** Implemented. Plan 002 complete: all 9 TUI screens, Apply with per-path conflict choices, manifest + init provenance; flag-based `grove init --pack …` unchanged. (Manage mode / dashboard in Phase 3.)
- **Validation:** Manual run of `grove configure` or `grove init` in a real repo; all screens reachable; install matches manifest.

### Phase 3: Add, sync, and configure (manage mode)

- **Goal:** Lifecycle commands and configure’s “manage” mode when manifest exists.
- **Deliverables:** ✅ `grove add <pack>`; ✅ `grove sync`; ✅ `grove configure` when manifest exists → manage TUI (read-only + add pack, re-run analysis); ✅ Conflict resolution in TUI and CLI.
- **Validation:** Add a second pack after init; run sync after editing a template; `grove configure` (existing manifest) shows correct state.

### Phase 4: Polish and packaging

- **Goal:** Robustness, docs, and distribution.
- **Deliverables:** ✅ Error handling and clear messages; ✅ User-facing docs (README, command help); ✅ Pack author guide (pack.toml schema, template conventions). No doctor stub—doctor is post-MVP when it has real behavior.
- **Validation:** New contributor can add a new pack following the guide; CLI installable via uv/pip.

---

## 13. Future Considerations

- **Post-MVP:** `grove remove`, `grove doctor` (drift, broken refs, stale files), `grove generate-skill` as standalone command, community/remote packs.
- **Integration:** IDE/editor hints (e.g. “Open Grove manifest”), CI step to run `grove sync --check` to detect drift.
- **Advanced:** Anchored file updates, pack version migrations, marketplace or registry server.

---

## 14. Risks & Mitigations

| Risk | Mitigation |
|------|-------------|
| Base Pack or default install grows into “.ai sprawl” again | Enforce size budget (~6–10 files for Base); review any new “always installed” content; keep heavy material in optional packs. |
| TUI becomes hard-coded and brittle | Registry-driven questions and pack list; no pack names or question text in TUI code; add tests that add a new pack and assert it appears in flow. |
| Manifest and managed-file semantics get ambiguous | Define and document managed vs seeded clearly; store source template and checksum per file; sync only touches managed. |
| Repo analysis wrong or noisy | Expose overrides in TUI; store overrides in manifest; document detector confidence; allow “rescan” from configure (manage mode). |
| Template variables missing or wrong | Schema for required variables per template; composer fails fast with clear error; pack author guide with examples. |

---

## 15. Appendix

### Related documents

- [docs/concept.md](../../docs/concept.md) — GROVE framework (Grow, Root, Optimize, Verify, Enrich).
- Chat transcript: `tmp/2026-03-16_22-21-33__Project-Grove-Grove-Development-Process__chat.json` (source of CLI/TUI, pack model, registry, TUI flow, manifest design).

### Key dependencies

- Grove CLI is the **installer** for the Grove context system; the system it installs (rules, plans, handoffs, skills) is used by agents and humans in the repo. This PRD does not define the agent runtime.

### Repository structure (this repo)

- `src/grove/` — Grove package (CLI, core, analyzer, packs; TUI in later phases).
- `.ai/SPECS/001-grove-cli/` — This PRD; technical design (schemas, exact layouts) to be added here or in a sibling doc.
