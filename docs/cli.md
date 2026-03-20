# CLI reference

Grove’s CLI bootstraps and maintains a Grove installation in your repo. All commands accept an optional `--root` / `-r` to set the project root (default: current directory).

---

## Commands

### `grove init`

First-time setup: creates `.grove/` and a manifest.

- **Interactive (TTY):** Runs the full init TUI (welcome → analyze → pack selection → preview → apply → finish). If `.grove/manifest.toml` already exists, opens the **manage** TUI instead.
- **Non-interactive:** Use `--pack` to install without a TTY:
  ```bash
  grove init --pack base --pack python
  ```
- **Options:** `--root`, `--dry-run` (preview only, no writes).

---

### `grove configure`

Single entry for setup and management. Requires a TTY.

- **No manifest:** Runs the full init TUI (same as `grove init` when no manifest).
- **Manifest exists:** Opens the **manage** TUI: view installed packs, analysis summary, sync status; actions: Add pack, Re-run analysis, Full re-setup, Quit.

Options: `--root` / `-r`.

---

### `grove manage`

Alias for `grove configure`. Same behavior and options.

---

### `grove add <pack>`

Add a pack to an existing Grove installation (e.g. `grove add python`). Resolves dependencies, renders new files, and updates the manifest. Requires `.grove/manifest.toml`.

- **Example:** `grove add python`
- **Options:** `--root` / `-r`

---

### `grove remove <pack>`

Remove one non-base pack from an existing Grove installation. Grove recomputes the remaining desired state, then classifies managed outputs into delete, rewrite, or preserve actions using pack ownership and provenance.

- **Example:** `grove remove python`
- **Dry-run:** `grove remove codex --dry-run`
- **Behavior:** shared managed files are recomposed from the remaining packs; orphaned pack-owned outputs are deleted; managed tool-hook blocks are removed without deleting unrelated user content.
- **Options:** `--root` / `-r`, `--dry-run`

Current v1 limits:

- Removes one pack at a time.
- `base` cannot be removed.
- Removal is blocked when another installed pack depends on the target pack.

---

### `grove sync`

Re-render all managed files from the current templates and profile. Only writes paths listed in `.grove/manifest.toml`; does not add or remove files from the manifest.

- **Options:** `--root` / `-r`, `--dry-run` (report what would be written, no writes).

---

### `grove doctor`

Run read-only Grove installation diagnostics.

- **Checks:** manifest loadability, installed-pack availability, dependency coherence, managed-file drift, anchor safety, tool-hook target health, pack-local skill presence, and pack-owned checks contributed by packs.
- **Example:** `grove doctor`
- **Options:** `--root` / `-r`

Current v1 limits:

- Human-readable output only; `--json` is not implemented yet.
- Read-only only; no `--fix` mode.

---

## Error messages

Errors are printed to stderr. Common cases:

- **No manifest** — “No Grove manifest; run 'grove init' first.” (for `add` / `sync`).
- **Remove blocked** — Removing `base` or a pack with installed dependents fails with an actionable lifecycle error.
- **Not a TTY** — Configure and manage require an interactive terminal; otherwise you’ll see a message directing you to use `grove init --pack` for non-interactive init.
- **Unknown pack** — Pack id not found in the registry; check available builtin packs or paths.
- **Doctor unhealthy** — `grove doctor` exits nonzero when findings are reported.

---

## Help

- `grove --help` — List commands
- `grove <command> --help` — Options for a specific command
