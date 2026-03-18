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

### `grove sync`

Re-render all managed files from the current templates and profile. Only writes paths listed in `.grove/manifest.toml`; does not add or remove files from the manifest.

- **Options:** `--root` / `-r`, `--dry-run` (report what would be written, no writes).

---

## Error messages

Errors are printed to stderr. Common cases:

- **No manifest** — “No Grove manifest; run 'grove init' first.” (for `add` / `sync`).
- **Not a TTY** — Configure and manage require an interactive terminal; otherwise you’ll see a message directing you to use `grove init --pack` for non-interactive init.
- **Unknown pack** — Pack id not found in the registry; check available builtin packs or paths.

---

## Help

- `grove --help` — List commands
- `grove <command> --help` — Options for a specific command
