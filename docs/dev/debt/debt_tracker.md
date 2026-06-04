---
last_updated: 2026-03-20
---

# Debt Tracker

## Active Debt

### P1

- [ ] DEBT-001 `docs-check` is not warning-clean.
  - Type: `docs`, `tooling`
  - Area: MkDocs configuration and documentation build hygiene
  - Impact: The repo rule is to treat warnings as defects where feasible, but `just docs-check` still emits recurring warnings. That makes the docs gate noisy and weakens confidence in future docs regressions.
  - Evidence:
    - `just docs-check` emits the upstream Material for MkDocs 2.0 warning banner.
    - `just docs-check` reports `color_scheme.md` exists in `docs/` but is not included in `mkdocs.yml` navigation.
    - Residual warnings were repeatedly called out as non-blocking in Plan 004 and Plan 006 validation/reporting.
  - Remediation:
    - Decide whether `docs/color_scheme.md` should be linked in `mkdocs.yml` or removed.
    - Decide how Grove wants to handle the Material warning in CI: pin/document acceptance with owner and target date, replace the theme, or adjust the docs gate strategy so the accepted warning is explicit instead of ambient noise.

### P2

- [ ] DEBT-002 `grove doctor` lacks a machine-readable output mode.
  - Type: `tooling`, `ops`
  - Area: `src/grove/cli/app.py`, `src/grove/core/doctor.py`, `src/grove/core/doctor_checks.py`
  - Impact: `grove doctor` has a structured internal report model, but the CLI only exposes human-readable output. That limits CI automation, editor integration, and scriptable health checks.
  - Evidence:
    - `docs/cli.md` explicitly says `grove doctor` is “Human-readable output only; --json is not implemented yet.”
    - `docs/dev/status.md` records that `--json` and `--strict` were deferred when Plan 006 Phase 4 shipped.
    - `src/grove/core/models.py` already defines typed `DoctorIssue` and `DoctorReport` models, so the current limitation is at the CLI/reporting surface rather than data modeling.
  - Remediation:
    - Add `grove doctor --json` with a stable schema derived from `DoctorReport`.
    - Decide whether `--strict` should remain a separate mode or simply document exact nonzero-exit behavior for error-only vs warning-inclusive runs.
    - Add integration coverage for machine-readable output and exit semantics.

- [ ] DEBT-003 The PRD still promises `grove analyze`, but the shipped CLI does not expose it.
  - Type: `architecture`, `docs`
  - Area: CLI surface, product spec alignment
  - Impact: The analyzer engine exists internally, but users have no first-class inspect-only command even though the canonical PRD still lists `grove analyze` as a shipped CLI entry point. This creates spec drift and hides useful diagnostics behind other flows.
  - Evidence:
    - `.ai/SPECS/001-grove-cli/PRD.md` lists `grove analyze` in MVP scope and in the command table.
    - `src/grove/analyzer/engine.py` exposes `analyze(repo_root: Path) -> ProjectProfile`.
    - `src/grove/cli/app.py` defines `init`, `configure`, `manage`, `add`, `remove`, `sync`, and `doctor`, but no `analyze` command.
    - `docs/cli.md` has no `grove analyze` section.
  - Remediation:
    - Either implement `grove analyze` as an inspect-only command with stable output, or explicitly update the PRD to remove it from the promised shipped surface.
    - Align CLI docs and roadmap/status wording once the product decision is made.

### P3

- None.

## Recently Closed Debt

- None.

(When adding debt: use `DEBT-XXX` IDs and link to roadmap `SI-XXX` when applicable.)
