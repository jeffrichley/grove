# Grove

Grove is a modular skill framework for AI coding agents that orchestrates the complete software development lifecycle—from idea and architecture through implementation, testing, and release—enabling autonomous end-to-end software creation.

## Documentation

Full documentation is built with [MkDocs](https://www.mkdocs.org/) and the [Material](https://squidfunk.github.io/mkdocs-material/) theme:

- **Serve locally:** `just docs-serve` (then open http://127.0.0.1:8000)
- **Build:** `just docs-build`
- **Validate:** `just docs-check` (runs as part of `just quality`)

See the [docs](docs/index.md) for the GROVE framework, CLI reference, and pack author guide.

## CLI

- **`grove init`** — First-time setup: interactive TUI or `--pack base --pack python` (creates `.grove/` and manifest). With existing manifest, opens manage TUI.
- **`grove configure`** — Open setup: init TUI when no manifest; manage TUI (installed packs, add pack, re-run analysis, full re-setup) when manifest exists. Requires a TTY.
- **`grove manage`** — Alias for `grove configure`.
- **`grove add <pack>`** — Add a pack to an existing Grove installation (e.g. `grove add python`). Updates manifest and generated files.
- **`grove sync`** — Re-render all managed files from current templates and profile. Use `--dry-run` to preview.

## Development

- **Setup**: `uv sync --all-groups` (requires [uv](https://docs.astral.sh/uv/)).
- **Pre-commit** (run once per clone): `just pre-commit-install` (or `uv run pre-commit install` and `uv run pre-commit install --hook-type commit-msg`).
- **Quality**: `just quality-check` (CI-safe, no writes) or `just quality` (format + fix + all checks); `just test-cov` (tests with coverage). Before commit/PR: `just quality && just test`.
- **Docs**: `just docs-serve` to browse; `just docs-check` to validate (included in `just quality`).
- **Commit**: `just commit` for conventional commits via Commitizen.
