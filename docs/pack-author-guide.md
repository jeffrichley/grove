# Pack author guide

This guide explains how to create and add **packs** to Grove. A pack is a bundle of templates, rules, and optional setup questions that extend a Grove installation.

---

## Overview

- **Base pack** — Required; provides the core `.grove/` anchor infrastructure (`GROVE.md`, `INDEX.md`). Always installed.
- **Capability packs** — Optional (e.g. Python, memory, commands). Each pack has a manifest (`pack.toml`) and contributes templates, rules, and optionally setup questions.

Packs are **data-driven**: the CLI discovers them from manifests (e.g. `pack.toml`); there is no hard-coded pack list in the TUI.

---

## Pack layout

A pack lives in a directory containing:

- **`pack.toml`** (or `pack.yaml` / `pack.yml`) — Pack manifest. **Only TOML is supported today;** YAML is not yet implemented.
- **Templates** — Jinja2 (`.j2`) files listed in the manifest; paths are relative to the pack root.
- **Optional:** `rules/`, `skills/`, or other layout as defined by the pack.

**Builtin packs** in this repo live under `src/grove/packs/builtins/`, e.g.:

- `src/grove/packs/builtins/base/` — Base pack
- `src/grove/packs/builtins/python/` — Python pack

---

## pack.toml schema

Required top-level fields:

| Field | Description |
|-------|-------------|
| `id` | Unique pack identifier (e.g. `base`, `python`). |
| `name` | Human-readable name. |
| `version` | Version string (e.g. `0.1.0`). |

Optional top-level fields:

| Field | Description |
|-------|-------------|
| `depends_on` | List of pack IDs this pack depends on (e.g. `["base"]`). |
| `compatible_with` | Tags for filtering (e.g. `["python"]`). |
| `activates_when` | Conditions that can auto-activate (e.g. `["pyproject.toml"]`). |

### `[contributes]` section

- **`templates`** — List of template paths (relative to pack root), e.g. `["GROVE.md.j2", "INDEX.md.j2"]`. Rendered with Jinja2; variables come from the project profile and setup answers.
- **`setup_questions`** — Optional list of questions the TUI shows when the pack is selected (structure defined by the TUI).
- **`rules`** — Optional path-triggered rules (e.g. for scoped context). Example:
  ```toml
  [[contributes.rules]]
  paths = ["**/*.py", "tests/**", "src/**"]
  ```
- **`injections`** — Optional anchored content contributions. Phase 2 uses anchor-first composition, so a pack can target an anchor and optionally narrow it to one file. Example:
  ```toml
  [[contributes.injections]]
  id = "python-guidance"
  anchor = "guidance"
  source = "snippets/guidance.md.j2"
  order = 10
  ```
- **`index_entries`** — Optional structured INDEX contributions rendered into `.grove/INDEX.md` sections such as `rules`, `commands`, `tools`, and `docs`.
- **`tool_hooks`** — Optional tool-native shim outputs such as repo-root `AGENTS.md`. These are rendered by the generic tool hook pipeline and owned by the integration pack.
- **`codex_skills`** — Optional Codex skill materialization entries for repo-local `.agents/skills/`. Use these in a Codex integration pack rather than storing skill bodies under `.grove/`.
- **`doctor_checks`** — Optional pack-owned diagnostics. These let a pack declare correctness requirements that `grove doctor` should validate without hard-coding package-specific rules into core.

---

## Example: base pack

```toml
# src/grove/packs/builtins/base/pack.toml
id = "base"
name = "Base Pack"
version = "0.1.0"
depends_on = []
compatible_with = []
activates_when = []

[contributes]
templates = [
    "GROVE.md.j2",
    "INDEX.md.j2",
]
setup_questions = []
```

---

## Example: Python pack

```toml
# src/grove/packs/builtins/python/pack.toml
id = "python"
name = "Python Pack"
version = "0.1.0"
depends_on = ["base"]
compatible_with = ["python"]
activates_when = ["pyproject.toml"]

[contributes]
templates = [
    "rules/python.md.j2",
    "skills/python-testing.md.j2",
]
setup_questions = []

[[contributes.injections]]
id = "python-guidance"
anchor = "guidance"
source = "snippets/guidance.md.j2"
order = 10

[[contributes.rules]]
paths = ["**/*.py", "tests/**", "src/**"]
```

---

## Template conventions

- **Engine:** Jinja2. Variables are merged from:
  - **Project profile** — From the repo analyzer (e.g. `project_name`, `language`, `package_manager`, `test_framework`, `tools`, `raw`).
  - **Setup answers** — User answers to pack `setup_questions` (keyed by question id).
- **Paths:** Template paths in `contributes.templates` are relative to the pack root. Destinations are under the install root (e.g. `.grove/`).
- **Anchor-owned files:** Rendered files are recorded in the manifest; `grove sync` rebuilds `grove:anchor:*` regions from current profile and contributions while preserving `grove:user:*` regions.
- **Tool integrations:** Tool-native files are owned by integration packs. For example, the built-in Codex integration pack contributes an `AGENTS.md` shim and materializes skills into `.agents/skills/`.

---

## Pack-owned doctor checks

Packs can contribute `doctor_checks` so `grove doctor` validates package-specific invariants in addition to the generic manifest/drift/anchor checks.

Current built-in check support:

- **`skill_front_matter`** — Verify that a tool-consumed skill file exists, has parseable front matter, and includes required keys.

Example:

```toml
[[contributes.doctor_checks]]
id = "codex-planning-execution-front-matter"
check_type = "skill_front_matter"
path = ".agents/skills/planning-execution/SKILL.md"
required_keys = ["name", "description"]
description = "Codex planning skill must include valid front matter."
```

Guidance:

- Keep checks tool- or pack-specific rather than encoding those invariants into Grove core.
- Use stable `id` values so findings are easy to trace.
- Point `path` at the concrete tool-facing output that `doctor` should validate.
- Only declare checks that can run locally and read-only.

---

## Codex skill front matter contract

The built-in Codex integration now expects each materialized `SKILL.md` to start with YAML-like front matter.

Required keys today:

- `name`
- `description`

Example:

```markdown
---
name: planning-execution
description: Plan work in phases and execute against the plan.
---
```

`grove doctor` reports a failure when a declared skill:

- is missing `SKILL.md`
- has no front matter
- has malformed front matter
- omits a required key

If your pack contributes Codex skills, make the template satisfy this contract so AI agents can consume the skill reliably.

---

## Adding a new builtin pack

1. Create a directory under `src/grove/packs/builtins/<pack_id>/`.
2. Add `pack.toml` with `id`, `name`, `version`, and `[contributes]` (at least `templates`).
3. Add template files (`.j2`) and reference them in `contributes.templates`.
4. The registry discovers packs from the builtins directory; no code changes needed to register the pack. Ensure dependency order: if your pack `depends_on` another, that pack must be present in builtins.
5. If your pack integrates with a tool, keep tool-native shims and skills in that tool's integration pack rather than the base pack.

---

## References

- **Pack manifest model:** `src/grove/core/models.py` — `PackManifest`.
- **Loader:** `src/grove/packs/loader.py` — `load_pack_manifest()`, discovery order.
- **Composer:** `src/grove/core/composer.py` — How `contributes.templates` are used and dependency order.
- **Renderer:** `src/grove/core/renderer.py` — Jinja2 rendering and variable context.
- **Tool hook pipeline:** `src/grove/core/tool_hooks.py` — Generic hook and Codex skill materialization flow.
