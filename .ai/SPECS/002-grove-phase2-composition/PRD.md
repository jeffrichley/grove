# PRD: Grove Phase 2 — Robust Composition, Tool Hooks & Packs

**Author:** Derived from ChatGPT Project Grove conversation (2026-03-18)
**Audience:** Product + Engineering
**Status:** Draft v1
**Date:** 2026-03-18
**Related:** [001-grove-cli PRD](../001-grove-cli/PRD.md), [docs/concept.md](../../docs/concept.md), chat export `tmp/2026-03-18_16-39-13__ChatGPT-Project-Grove__chat.json`

---

## 1. Executive Summary

Phase 2 transforms Grove from “packs render whole files” into a **composable document system** with anchor-owned injection, safe sync with user-preserved regions, human-readable discovery (rendered into markdown), and **external tool hooks** so tools like Codex, Cursor, and Claude Code read from their native locations while Grove remains the source of truth. The base pack is stripped to minimal infrastructure; capability packs inject into shared files and contribute rules, commands, knowledge, and tool shims. Tool-specific integration is pack-owned, not hard-coded in Grove core.

**Core value proposition:** Agents get a lean always-loaded layer, scoped rules and docs loaded just-in-time, and a single source of truth (GROVE). Tool integrations are thin shims in each tool’s expected paths (e.g. `AGENTS.md`, `.cursor/rules/`), pointing back to `.grove/`. Commands and planning behavior are structured (TOML) and rendered into markdown. Optional packs (memory, knowledge, planning-execution, self-upgrade) make the system usable day-one and support agent writeback and self-improvement in a controlled way.

**MVP goal:** Deliver Phase 2 as a working composition engine (anchors + injections, user markers, sync that rebuilds anchor bodies), a minimal base pack, rendered INDEX and command/planning docs, a generic pack-driven tool hook pipeline with Codex as the first implemented integration, and a defined pack set (base, memory, python, commands, knowledge, project-context; optional planning-execution, self-upgrade, and tool-integration packs) with clear separation between GROVE context and tool-specific skills where applicable.

---

## 2. Mission

**Mission:** Make Grove’s instruction system composable, safe to re-sync, and natively discoverable by external AI tools without duplicating logic outside Grove.

**Core principles:**

1. **Structure over improvisation** — Explicit anchors and user regions; no freeform patching or “smart” merge magic.
2. **GROVE is the source of truth** — Tool hooks and skills point back to `.grove/`; adapters do not duplicate the full instruction system.
3. **Layered context (just-in-time)** — Always-loaded layer stays minimal; scoped rules and heavy docs are discoverable via INDEX and path/rules.
4. **Progressive disclosure under context constraints** — Assume Codex may truncate or prioritize context; adopt a 3-layer model (Tier 1: `AGENTS.md` + `.grove/GROVE.md`, Tier 2: `INDEX.md` + `rules/*` + `commands/*`, Tier 3: `docs/*` + `knowledge/*` + `memory/*`); keep Tier 1 extremely small, and treat anything that must be read on every run as “short by design”.
5. **Packs contribute; base owns structure** — Base pack defines skeleton and injection points; packs inject snippets, rules, commands, and tool shims.
6. **Tool integrations are packs** — Each external-system integration is delivered by a pack (or pack family) that declares the tool-native shims/hooks Grove should materialize.
7. **Human-readable routing** — Discovery/navigation is rendered into markdown (e.g. INDEX.md) for agents and humans; no required machine-only TOML for agents to query.

---

## 3. Target Users


| Persona                   | Technical comfort                  | Key needs                                                                                            |
| ------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Developer using Grove** | Intermediate (CLI, TOML, markdown) | One setup, safe re-sync, clear “when to use” guidance, tool (Codex/Cursor) just works                |
| **Pack author**           | Advanced                           | Inject into GROVE.md and INDEX, contribute tool hooks and commands without forking core              |
| **Agent (Codex, etc.)**   | N/A                                | Single entrypoint (e.g. AGENTS.md → GROVE.md), then INDEX/rules/commands; skills as procedural layer |


**Pain points addressed:**

- Packs cannot extend shared files (e.g. GROVE.md); only whole-file templates today.
- No first-class “when to use what” navigation; discovery was discussed as TOML but agents should not have to query a separate registry.
- External tools (Codex, Cursor) need files in *their* expected locations; Grove must generate those and point back to Grove.
- Base pack is too opinionated; should be minimal infrastructure so packs inject guidance.
- No structured commands or planning/subagent guidance; agents guess.
- No clear model for agent writeback (memory) or self-improvement (proposals) without bloating base.

---

## 4. MVP Scope

### In Scope

#### Core composition

- ✅ `contributes.injections`: multiple entries per pack; `anchor`, optional `target`, optional `source`, optional inline `content`, `order`, `id`.
- ✅ Anchor markers in base/authored files: `<!-- grove:anchor:<name>:start -->` / `<!-- grove:anchor:<name>:end -->`.
- ✅ User-editable markers: `<!-- grove:user:<region-id>:start -->` / `<!-- grove:user:<region-id>:end -->`; sync never replaces these.
- ✅ Sync rules: rebuild the full body of matched anchors; preserve user blocks and content outside anchor zones.
- ✅ Deterministic ordering and conflict detection for injections (e.g. duplicate ids, missing anchors).
- ✅ Separation of render stage (variables, conditions, snippets) vs compose stage (merge into destination files) vs sync stage (write/update only anchor bodies).

#### Rendered navigation (no discovery.toml for agents)

- ✅ Human-readable INDEX: `.grove/INDEX.md` with anchors for rules, commands, tools, docs; packs contribute content through the same generic injection system used for other files.
- ✅ “When to use” and routing guidance rendered into markdown; no requirement for agents to read a separate TOML discovery file.
- ✅ No file-specific composition logic for `INDEX.md`; it is just another anchor-enabled Grove file.

#### Minimal base pack

- ✅ `.grove/GROVE.md`: identity, GROVE acronym (G/R/O/V/E), one-line principle (“Agents do not hold knowledge — the grove does”), minimal operating model, anchors (guidance, commands, user notes, improvement).
- ✅ `.grove/INDEX.md`: anchors for index:rules, index:commands, index:tools, index:docs.
- ✅ `.grove/rules/README.md`, `.grove/docs/README.md`, `.grove/commands/README.md`: anchor targets for aggregation.
- ✅ `.grove/manifest.toml`: system state (existing schema extended as needed).
- ✅ Repo-root `AGENTS.md`: Codex shim pointing to `.grove/GROVE.md`, `.grove/INDEX.md`, and when relevant rules/docs/commands; if `AGENTS.md` already exists, Grove only appends/updates the Grove-managed shim block and preserves any existing user content.
- ✅ Base pack contains no language/framework/workflow opinions; only structure, philosophy, and injection points.

#### Tool hooks (generic pipeline; Codex first)

- ✅ Framework: “tool hooks” — Grove core knows how to discover, order, render, and apply pack-contributed hook outputs; it does not hard-code one tool’s integration behavior.
- ✅ Pack-owned integrations: Codex, Cursor, Claude Code, and future tools are declared by separate packs that contribute outputs for their native locations.
- ✅ Codex is the first implemented integration: ensure repo-root `AGENTS.md` exists and contains/updates the Grove-managed shim block; if `AGENTS.md` already exists, Grove appends/updates only that block (no wholesale overwrite).
- ✅ Hook files live where the tool expects them according to the selected integration pack (for Codex, repo-tree AGENTS.md; not dependent on ~/.codex/ for Phase 2).
- ✅ Pack contribution type: e.g. `[[contributes.tool_hooks]]` with `tool`, `hook_type`, `target`, `source`, `order`.

#### Commands and planning

- ✅ Structured commands: project-owned `.grove/commands.toml` (or equivalent) with `[[commands]]` (id, title, command, when_to_use, category); rendered into `.grove/commands/*.md` and into GROVE.md/INDEX.md.
- ✅ Commands pack provides schema and default structure; packs can contribute command entries; rendering pulls from TOML into markdown.
- ✅ Planning-execution pack (optional): teaches task decomposition, dependencies, parallel work, when to spawn subagents, reconciliation; optional `.grove/planning.toml`; content in `.grove/planning/` (e.g. PLANNING.md, subagents.md).

#### Phase 2 pack set

- ✅ Base (minimal), Memory, Python, Commands, Knowledge, Project-context.
- ✅ Optional: Self-upgrade (proposal-driven), Planning-execution, Tasks.
- ✅ Memory pack: `.grove/memory/` (e.g. MEMORY.md, decisions.md, preferences.md, current-status.md); commands: record decision, update memory, summarize state.
- ✅ Self-upgrade pack: `.grove/improvement/`, proposal-driven workflow; commands: propose improvement, refine rule, add command; no autonomous overwrite of Grove.
- ✅ Knowledge pack: curated libraries/tools, links to repos and best-practice docs; structure like When to use / When NOT to use / Common pitfalls / Recommended pattern / Example.

#### Skills and tool integrations

- ✅ Dual-layer: Grove = source of truth (rules, context, commands); Codex skills = procedural execution (workflows, delegation).
- ✅ Codex skills are installed into the Codex skills directory (default `~/.codex/skills` / `$CODEX_HOME/skills`); Grove must not contain the actual skill bodies under `.grove/` (only pointers/metadata).
- ✅ AGENTS.md is a minimal entrypoint that points to `.grove/GROVE.md` and `.grove/INDEX.md`; pack-generated guidance (rules/docs/commands) explains “which skill to use”, while Codex skills define “what to do”.
- ✅ Execution-critical behaviors that must reliably happen (e.g. planning/execution workflow, subagent delegation, memory writeback) are implemented as Codex skills, not only as prose in Grove.
- ✅ Hard rule: anything that must reliably happen during execution is encoded as a Codex skill (not only as prose in GROVE).
- ✅ No duplication: Grove defines what should be done; skills define how to do it procedurally.
- ✅ Tool-specific hooks and tool-specific skills belong to the corresponding integration pack rather than Grove core.

#### Validation and observability

- ✅ Dry-run compose and diff preview.
- ✅ Provenance: “why is this block here?” — which pack, which anchor, which source template (for debugging).
- ✅ Lint/validation for anchors, duplicate ids, unresolved references.

### Out of Scope (Phase 2)

- ❌ `discovery.toml` as a runtime artifact agents must query; discovery is rendered into markdown only.
- ❌ Full implementation of every external tool integration in Phase 2. The pipeline is generic, but only Codex is required as the first shipped integration in this phase.
- ❌ Global Codex config (~/.codex/...) as primary mechanism.
- ❌ Custom slash commands for Codex (unless verified and specified later).
- ❌ Arbitrary file patching or regex-based edits; only anchored injection into declared targets.
- ❌ Full implementation of every optional pack (e.g. research, multi-agent coordination) in Phase 2.

---

## 5. User Stories

1. **As a developer**, I want the base pack to be minimal so that packs can inject guidance without fighting a heavy default and the always-loaded layer stays small.
2. **As a developer**, I want to run `grove sync` and have full anchor bodies rebuilt while my edits in user regions and outside anchor zones are never overwritten.
3. **As a pack author**, I want to declare content for a named anchor, optionally narrowed to one target file, so that my pack extends shared docs without custom engine behavior for each file.
4. **As a tool integration pack author**, I want to declare hooks for a specific external system so that Grove can materialize that tool’s native shims without adding tool-specific logic to core.
5. **As a Codex user**, I want an `AGENTS.md` at the repo root that points to `.grove/GROVE.md` and INDEX so that Codex uses Grove as the canonical instruction system without me copying content.
6. **As an agent**, I want a single entrypoint (e.g. AGENTS.md → GROVE.md) and a clear INDEX so that I know when to load which rules and commands (just-in-time context).
7. **As a developer**, I want commands defined in a TOML file and rendered into Grove docs so that agents use canonical commands instead of guessing.
8. **As a developer**, I want optional memory and self-upgrade packs so that agents can record decisions and propose Grove improvements in a structured, reviewable way.
9. **As a developer**, I want procedural workflows (e.g. planning-execution, self-upgrade) as Codex skills that read Grove context so that capabilities are modular and Grove remains the source of truth.

---

## 6. Core Architecture & Patterns

### High-level layers

- **Render stage:** Resolve variables, conditions, snippets; produce content fragments from templates.
- **Compose stage:** Merge fragments into destination files (anchor resolution, ordering, anchor-body assembly).
- **Sync stage:** Rewrite only anchor bodies; preserve user regions and non-anchor content.
- **Tool hooks:** Per-tool contribution type; renderer emits files at tool-specific paths (e.g. `AGENTS.md`, later `.cursor/rules/*.mdc`); content is thin shim + pointers to Grove. Core provides the generic pipeline; packs own the tool-specific declarations and payloads.

### File output classes


| Class             | Purpose                                 | Example                                                      |
| ----------------- | --------------------------------------- | ------------------------------------------------------------ |
| Base docs         | Always-loaded, composed, anchor-enabled | `.grove/GROVE.md`                                            |
| Index             | Human-readable routing                  | `.grove/INDEX.md`                                            |
| Scoped rules      | Path-triggered, pack-owned              | `.grove/rules/python.md`                                     |
| Reference docs    | Heavyweight, on-demand                  | `.grove/docs/*.md`                                           |
| Commands          | Canonical command surface               | `.grove/commands/*.md`, rendered from `.grove/commands.toml` |
| Tool hook outputs | Shim files in tool-native locations     | `AGENTS.md`, later `.cursor/rules/`                          |


### Marker contract

- **Anchor markers** (in base/template): define Grove-owned insertion zones. Sync rebuilds the entire body inside an anchor pair.
- **User markers** (in template): define human-owned regions; sync must preserve exactly.
- **No managed markers in Phase 2:** ownership is by anchor body, not per injected block.

### Pack contribution types (Phase 2)

- `templates` — whole-file outputs (existing).
- `injections` — snippet into an anchor, optionally narrowed to a target file, with id, order, and either file-backed `source` or inline `content`.
- `tool_hooks` — generate file at target path for a given tool (e.g. Codex `AGENTS.md`, later Cursor/Claude Code surfaces), owned by the contributing integration pack.

### Design principles

- Do not let packs directly edit arbitrary files; only contribute into explicitly declared anchors.
- Tool hooks: “What files does this tool already honor?” → Grove emits compatible hook files that hand off to Grove.
- Skills: Grove describes rules/context; skills execute procedures and reference Grove.

---

## 7. Tools / Features

### Composition engine

- **Injection schema:** `[[contributes.injections]]` with `id`, required `anchor`, optional `target`, optional `source`, optional inline `content`, `order`.
- **Anchor parser:** Find anchor pairs in target files; validate presence before compose.
- **Composer:** Build composed document from base + ordered injections per anchor; inject rendered content into anchor bodies.
- **Conflict detection:** Duplicate injection ids, missing anchors, ordering collisions; fail or warn with clear messages.

### Sync behavior

- **Rewrite anchor bodies:** Scan for `grove:anchor:<name>:start` … `end`; rebuild the full content between the markers from current contributions.
- **Preserve user blocks:** Never change content between `grove:user:*:start` and `end`.
- **Preserve non-anchor content:** Do not rewrite outside anchor zones unless explicitly instructed (e.g. full re-render of a file).

### Minimal base pack file list

- `.grove/GROVE.md` — identity, GROVE principles, operating model, anchors (guidance, commands, user notes, improvement).
- `.grove/INDEX.md` — anchors for rules, commands, tools, docs.
- `.grove/rules/README.md`, `.grove/docs/README.md`, `.grove/commands/README.md` — anchor targets.
- `.grove/manifest.toml` — system state.
- `AGENTS.md` (repo root) — Codex shim.

Optional: `.grove/.gitignore` for generated/managed artifacts if needed.

### Tool integration hooks (Phase 2)

- **Generic contract:** Grove collects `[[contributes.tool_hooks]]` entries from selected packs, renders them, and applies them using the write strategy associated with `hook_type`.
- **Pack ownership:** The contributing pack is responsible for declaring the tool, target path, and shim content.
- **Codex first:** Root `AGENTS.md` is ensured to exist; it points to `.grove/GROVE.md`, `.grove/INDEX.md`; when relevant to rules/docs/commands. If `AGENTS.md` already exists, Grove appends/updates only the Grove-managed shim block and preserves any existing user content.
- **Manifest:** `[[contributes.tool_hooks]]` with `tool`, `hook_type`, `target`, `source`, `order`.

### Commands

- **Schema:** `.grove/commands.toml` with `[[commands]]` (id, title, command, when_to_use, category).
- **Rendering:** Into `.grove/commands/*.md` and into GROVE.md/INDEX.md command sections.
- **Commands pack:** Provides template/schema and default structure; packs can contribute entries (or project edits TOML).

### Planning-execution (optional pack)

- **Content:** Task decomposition, dependency awareness, when to use subagents, reconciliation.
- **Structured config (optional):** e.g. `.grove/planning.toml` for delegation patterns, max_parallel_tasks.
- **Rendered:** `.grove/planning/PLANNING.md`, subagents.md, etc.; referenced by skills.

### Skills integration

- **Source of truth:** Skill templates/sources live in pack-provided content; installation materializes actual Codex skills into the Codex skill directory (not into `.grove/`).
- **Install:** Automatic as part of Grove install/sync; Grove materializes the Codex skill bodies into Codex’s configured skills directory.
- **Bridge:** AGENTS.md points to `.grove/GROVE.md` (and optionally INDEX/rules/commands); pack-generated docs provide guidance on skill selection/use, and skills reference Grove context when executing.
- **Ownership boundary:** Hook shims and skill materialization for a given tool belong to that tool’s integration pack, even though Grove core executes the generic pipeline.

### Validation and provenance

- **Dry-run compose:** Output what would be written without writing.
- **Diff preview:** Show changes to anchor regions.
- **Provenance:** For any injected content, report pack id, injection id, anchor, and source/template origin (e.g. CLI or debug output).

---

## 8. Technology Stack

- **Language:** Python 3.12+ (existing Grove CLI).
- **Config/data:** TOML for manifest, pack manifests, commands.toml, planning.toml.
- **Templates:** Jinja2; single-file render; compose step merges fragments.
- **Models:** Pydantic for injection specs, command entries, tool hook specs (extend existing models).
- **Output:** Markdown for GROVE.md, INDEX.md, rules, docs, commands; tool-specific formats for hooks (e.g. AGENTS.md markdown).
- **Skills:** Codex skill format (SKILL.md, references/, scripts/ as needed); install path per Codex conventions.

---

## 9. Security & Configuration

- **Trust:** Treat repo and user-edited regions as trusted for sync; do not overwrite user markers or content outside anchor bodies.
- **Tool hooks:** Generated files are deterministic from pack content and profile; no arbitrary code execution in hook content.
- **Configuration:** Manifest and `.grove/commands.toml`, `.grove/planning.toml` are project-owned; no secrets in manifest.
- **Scope:** Phase 2 always generates repo-owned GROVE outputs (e.g. `.grove/` and tool hook files like `AGENTS.md`). Optional Codex skill installation may write to Codex’s configured skills directory, but Phase 2 does not require editing any external Codex config beyond the standard destination paths.

---

## 10. API Specification

No REST API. Internal “API” is the composition/sync pipeline and pack contribution schema:

- **Compose:** Input: profile, selected packs, install root, pack roots. Output: composed file graph (per target file: base content + rebuilt anchor bodies).
- **Sync:** Input: install root, manifest, composed graph, options (dry_run, collision strategy). Output: list of written paths and/or diff.
- **Injection spec:** `id`, required `anchor`, optional `target`, optional `source` (template path relative to pack), optional inline `content`, `order`.
- **Tool hook spec:** `id`, `tool`, `hook_type`, `target` (path relative to repo root), `source`, `order`.

Exact function signatures and Pydantic models to be defined in implementation plan.

---

## 11. Success Criteria

### Phase 2 success definition

- A pack can declare multiple injections by anchor, optionally narrowed to `.grove/GROVE.md`, `.grove/INDEX.md`, or another file; compose rebuilds the correct anchor bodies and sync preserves user regions.
- Base pack installs minimal GROVE.md (with acronym, principle, operating model, anchors), INDEX.md, rules/docs/commands READMEs, manifest, and repo-root AGENTS.md.
- Codex user opens repo; Codex reads AGENTS.md and is directed to `.grove/GROVE.md` and INDEX.
- Commands are defined in TOML and rendered into Grove markdown; agents see canonical commands.
- Optional memory and self-upgrade packs provide writeback and proposal workflows without bloating base.
- Dry-run and provenance output are available for debugging.

### Functional requirements

- ✅ Injection schema and anchor/user marker format implemented and documented.
- ✅ Sync rebuilds only anchor bodies; user regions and non-anchor content preserved.
- ✅ Base pack contains only structure, philosophy, and anchors; no heavy opinionated content.
- ✅ Generic tool hook pipeline implemented in core, with Codex as the first shipped integration pack.
- ✅ Codex root `AGENTS.md` generated and points to Grove.
- ✅ INDEX.md and command docs rendered from structured pack contributions and/or TOML.
- ✅ At least Base, Memory, Python, Commands packs usable; optional Knowledge, Project-context, Planning-execution, Self-upgrade defined and at least one implemented to the extent needed to validate schema.

### Quality indicators

- Tests for compose (anchor resolution, ordering, conflict detection), sync (anchor-body replace, user preserve), and tool hook generation.
- Documentation: marker contract, injection schema, tool hook schema, base pack file list, commands.toml and planning.toml schema.

---

## 12. Implementation Phases

### Phase 2A — Composition engine

- **Goal:** Anchored injection and composed output graph.
- **Deliverables:**
  - ✅ Introduce `contributes.injections` in pack manifest schema.
  - ✅ Anchor and user marker format specified and parsed.
  - ✅ Composer merges base + injections per anchor, with optional target narrowing and file-backed or inline payloads.
  - ✅ Deterministic ordering; duplicate-id and missing-anchor validation.
- **Validation:** Unit tests; integration test: install base + pack with injections, run sync, verify GROVE.md contains anchors and rebuilt anchor content.

- **Goal:** Sync only touches anchor bodies; user and non-anchor content preserved.
- **Deliverables:**
  - ✅ Sync logic: replace only content between anchor markers; preserve user markers and content outside anchor zones.
  - ✅ Re-sync idempotent for unchanged inputs.
- **Validation:** Tests with user-edited content and re-sync; no user region overwritten.

### Phase 2C — Rendered navigation and INDEX

- **Goal:** Human-readable INDEX and “when to use” in markdown; no discovery.toml required for agents.
- **Deliverables:**
  - ✅ INDEX.md with anchors; packs contribute navigation content through generic injections.
  - ✅ Renderer/composer produces consistent markdown without file-specific `INDEX.md` behavior.
- **Validation:** INDEX lists rules/commands/docs; content is readable and accurate.

### Phase 2D — Minimal base pack and pack set

- **Goal:** Base pack slimming and Phase 2 pack set (base, memory, python, commands, knowledge, project-context; optional others).
- **Deliverables:**
  - ✅ Base pack reduced to GROVE.md (minimal + acronym + anchors), INDEX.md, rules/docs/commands READMEs, manifest, AGENTS.md.
  - ✅ Memory, Commands, Python packs defined and at least partially implemented.
  - ✅ Knowledge and Project-context pack specified; optional Self-upgrade and Planning-execution specified.
- **Validation:** New install produces minimal base; adding packs adds injections and files as expected.

### Phase 2E — Generic tool hook pipeline + first Codex integration

- **Goal:** Grove supports pack-contributed tool integrations generically; Codex is the first implemented integration pack using that pipeline and ensures repo-root `AGENTS.md` contains the Grove-managed shim block (append if missing).
- **Deliverables:**
  - ✅ `contributes.tool_hooks` schema and generic hook application pipeline in core.
  - ✅ Tool-specific integrations are pack-owned; core contains no Codex-only orchestration path.
  - ✅ A Codex integration pack contributes the repo-root `AGENTS.md` shim hook.
  - ✅ Root `AGENTS.md` ensured/updated with a Grove-managed shim block (append if missing; update managed block if present).
  - ✅ Hooks live in actual tool-expected locations according to the selected integration pack.
- **Validation:** Install in test repo (with and without a pre-existing `AGENTS.md`); resulting `AGENTS.md` contains the Grove-managed shim block, and any pre-existing content outside the managed shim is preserved.

### Phase 2F — Commands and planning (structured)

- **Goal:** Commands from TOML rendered into markdown; optional planning-execution pack.
- **Deliverables:**
  - ✅ `.grove/commands.toml` schema; rendering into .grove/commands/* and GROVE/INDEX.
  - ✅ Commands pack provides template/schema.
  - ✅ Planning-execution pack content and optional planning.toml; when to use subagents, reconciliation.
- **Validation:** commands.toml drives rendered command docs; planning pack content present when pack installed.

### Phase 2G — Validation and provenance

- **Goal:** Dry-run, diff, and “why is this here” observability.
- **Deliverables:**
  - ✅ Dry-run compose and sync; diff preview for anchor regions.
  - ✅ Provenance output (pack id, injection id, anchor) for injected content.
  - ✅ Lint for anchors, duplicate ids, unresolved references.
- **Validation:** CLI or script can report provenance; lint catches invalid manifests.

---

## 13. Future Considerations

- **Post–Phase 2:** Cursor hooks (e.g. `.cursor/rules/*.mdc`), Claude Code hooks; global Codex path if verified.
- **Discovery:** Optional machine-readable index (e.g. discovery.toml) for tools that can consume it; not required for agents.
- **Skills:** automatic materialization/sync of Codex skills during Grove install/sync; skill versioning.
- **Packs:** Research pack, testing pack, documentation pack, multi-agent coordination pack.
- **Self-upgrade:** Approval workflow, staged application, rollback.

---

## 14. Risks & Mitigations


| Risk                                         | Mitigation                                                                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Sync overwrites user content                 | Strict marker contract; only replace inside anchor markers; tests with user regions and re-sync.                        |
| INDEX or GROVE.md becomes inconsistent       | Schema for index/contribution entries; renderer produces consistent markdown; lint for missing anchors.                 |
| Tool hook paths and semantics differ across external tools | Keep the pipeline generic but make each integration pack-owned; validate one tool at a time, starting with Codex repo-tree `AGENTS.md`. |
| Pack injection order conflicts               | Explicit `order` and id; conflict detection in composer; document ordering conventions.                                 |
| Skills and Grove drift apart                 | Skills reference Grove in SKILL.md and execute against GROVE; AGENTS.md stays minimal (points to GROVE.md/INDEX); avoid duplicating rules inside skills.                      |


---

## 15. Appendix

### Related documents

- [001-grove-cli PRD](../001-grove-cli/PRD.md) — existing CLI and TUI scope.
- [docs/concept.md](../../docs/concept.md) — GROVE framework (G/R/O/V/E).
- Chat export: `tmp/2026-03-18_16-39-13__ChatGPT-Project-Grove__chat.json`.

### Key decisions from conversation (later messages = clarification)

- Keep **GROVE.md** as canonical branded file; compatibility via generated shims (e.g. AGENTS.md).
- **Multiple** `[[contributes.injections]]`; anchor-first routing with optional target; render **markers** (anchor, user) for safe sync; payload can be file-backed or inline.
- **User-editable regions** first-class; overlay files optional later.
- **Discovery:** render into markdown (INDEX.md); no discovery.toml for agents to use.
- **Tool hooks:** generate files where each tool looks; the pipeline is generic, but Phase 2 only requires Codex to be implemented first.
- **Base pack:** minimal; GROVE acronym + principle + operating model in GROVE.md; **Memory** and **Self-upgrade** as separate packs; self-upgrade proposal-driven.
- **Commands:** structured TOML (e.g. `.grove/commands.toml`) rendered into Grove md.
- **Planning-execution:** separate pack; teach when to use subagents and reconciliation.
- **Skills:** Grove = context/source of truth; Codex skills = procedural; actual skill bodies are installed into Codex’s skill directory (not stored under `.grove/`); AGENTS.md bridges.

### Repository structure (this repo)

- `src/grove/` — Grove package (CLI, core, analyzer, packs, TUI).
- `.ai/SPECS/002-grove-phase2-composition/` — this PRD.
- Base pack and Phase 2 packs live under `src/grove/packs/builtins/` (or equivalent) per existing layout.
