# Grove

**Grove** is a modular skill framework for AI coding agents that orchestrates the complete software development lifecycle—from idea and architecture through implementation, testing, and release—enabling autonomous end-to-end software creation.

Instead of manually curating a large `.ai`-style tree that tends to grow out of control, you run a CLI that analyzes your repo, lets you select capabilities (base + optional packs), and writes a lean `.grove/` structure with rules, plans, handoffs, and **project-specific skills** generated from templates and repo facts.

---

## Quick start

1. **Install** (from repo root):
   ```bash
   uv pip install .
   ```
   Or with [uv](https://docs.astral.sh/uv/): `uv sync --all-groups` then use `uv run grove`.

2. **Initialize** Grove in your project:
   ```bash
   cd /path/to/your/repo
   grove init
   ```
   Follow the interactive TUI, or run non-interactively:
   ```bash
   grove init --pack base --pack python
   ```

3. **Manage** an existing Grove installation:
   ```bash
   grove configure
   ```
   Or add a pack and re-sync managed files:
   ```bash
   grove add python
   grove sync
   ```

---

## What Grove provides

| Area | Description |
|------|-------------|
| **Context system** | A persistent “grove” of knowledge (plans, decisions, handoffs) instead of fragile chat memory. See [GROVE framework](concept.md). |
| **CLI** | `grove init`, `grove configure`, `grove add`, `grove sync` to bootstrap and maintain a `.grove/` installation. See [CLI reference](cli.md). |
| **Packs** | Base pack (required) plus optional capability packs (e.g. Python, CLI). See [Pack author guide](pack-author-guide.md) to create or extend packs. |
| **Manifest** | `.grove/manifest.toml` tracks installed packs and generated files so you can re-sync safely. |

---

## Next steps

- [GROVE framework](concept.md) — Grow, Root, Optimize, Verify, Enrich
- [CLI reference](cli.md) — Commands and options
- [Pack author guide](pack-author-guide.md) — How to add or create packs
- [Development](dev/roadmap.md) — Roadmap and status
