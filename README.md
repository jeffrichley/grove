# grove

Grove is a modular skill framework for AI coding agents that orchestrates the complete software development lifecycle—from idea and architecture through implementation, testing, and release—enabling autonomous end-to-end software creation.

## Development

- **Setup**: `uv sync --all-groups` (requires [uv](https://docs.astral.sh/uv/)).
- **Pre-commit** (run once per clone): `just pre-commit-install` (or `uv run pre-commit install` and `uv run pre-commit install --hook-type commit-msg`).
- **Quality**: `just quality-check` (CI-safe checks only), `just quality` (format + fix + all checks), `just test-cov` (tests with coverage).
- **Commit**: `just commit` for conventional commits via Commitizen.
