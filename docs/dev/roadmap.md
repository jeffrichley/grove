---
last_updated: 2026-03-17
---

# Roadmap

## User-visible / features

| Priority | Item | Status | Source |
| -------- | ---- | ------ | ------ |
| 1 | Grove CLI core: `grove init`, Base + Python packs | Done | `.ai/PLANS/001-grove-cli-core-engine.md` |
| 2 | Grove CLI Phase 2: TUI + full init flow | Done | `.ai/PLANS/002-grove-cli-tui-init-flow.md` |
| 3 | Grove CLI Phase 3: grove add, sync, configure (manage mode) | Next | `.ai/SPECS/001-grove-cli/PRD.md` (§12 Phase 3) |

## Internal / engineering

- Plan 001 delivered: pack registry, analyzer, composer, renderer, file_ops, manifest, CLI entry, integration tests.
- Plan 002 delivered: TUI (Textual), all 9 screens (configure/init flow), SetupState, analyzer/composer/file_ops integration, Apply with per-path conflict choices, manifest + init provenance.
- Next: Phase 3 per PRD (grove add, grove sync, grove configure when manifest exists = manage mode); see `.ai/SPECS/001-grove-cli/PRD.md`.
