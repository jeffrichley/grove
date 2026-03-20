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

---

## Adding a new builtin pack

1. Create a directory under `src/grove/packs/builtins/<pack_id>/`.
2. Add `pack.toml` with `id`, `name`, `version`, and `[contributes]` (at least `templates`).
3. Add template files (`.j2`) and reference them in `contributes.templates`.
4. The registry discovers packs from the builtins directory; no code changes needed to register the pack. Ensure dependency order: if your pack `depends_on` another, that pack must be present in builtins.

---

## References

- **Pack manifest model:** `src/grove/core/models.py` — `PackManifest`.
- **Loader:** `src/grove/packs/loader.py` — `load_pack_manifest()`, discovery order.
- **Composer:** `src/grove/core/composer.py` — How `contributes.templates` are used and dependency order.
- **Renderer:** `src/grove/core/renderer.py` — Jinja2 rendering and variable context.
