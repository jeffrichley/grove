---
description: "Prepare PR title/body from commits, plan, and validation evidence"
argument-hint: [optional-plan-path]
---

# PR: Prepare High-Signal Pull Request

## Objective

Create or update a pull request with a clear title/body that explains what changed, why, and how it was validated. Then monitor CI until all checks pass, fix any failures on the branch, and merge—do not hand off with failing checks unless the user explicitly accepts or a fix requires user input.

Reference guidance:
- `.ai/COMMANDS/_shared/story-writing.md`
- `.ai/COMMANDS/_shared/review-checklist.md`

## Process

### 1. Collect PR inputs

- Commit history on branch:
  - `git log --oneline origin/main..HEAD`
- Active plan and execution evidence:
  - `.ai/PLANS/...` including `## Execution Report`
- Validation evidence from `.ai/COMMANDS/validate.md`

### 2. Build PR title

- Keep title specific and outcome-oriented.
- Prefer alignment with dominant commit intent.

### 3. Build PR body

Include:
- Summary (what changed)
- Why (problem/value)
- Validation (commands + outcomes)
- Risks / rollback notes
- References (plans/issues)

### 4. Enforce PR template usage

If available, use repository template:
- `.github/pull_request_template.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/PULL_REQUEST_TEMPLATE/*`

When template exists:
- populate all required sections with concrete content
- do not leave placeholder text

If no template exists:
- use structured fallback format below

### 5. Monitor CI checks to completion, then merge or fix

After creating/updating the PR, do not stop at submission. Keep polling checks until they complete:

- Get PR number:
  - `gh pr view --json number -q .number`
- Watch checks (preferred):
  - `gh pr checks <PR_NUMBER> --watch --interval 10`
- Polling fallback:
  - `while true; do gh pr checks <PR_NUMBER>; sleep 10; done`

Decision rule after checks complete:
- If all required checks pass:
  - merge PR (`gh pr merge <PR_NUMBER> --squash --delete-branch` or repo-standard merge mode)
- If any required check fails:
  - inspect failing job logs
  - fix on the same branch
  - re-run validation (`.ai/COMMANDS/validate.md`)
  - push and continue polling until green

### 6. Completion: do not hand off with failing checks

- **This command is not complete** until either (a) the PR is merged, or (b) the user explicitly tells you to stop or to accept failing checks.
- If CI fails, **you must fix** on the branch, re-validate, push, and poll again. Do not present "options" and stop; implement the fix.
- **Exception:** Only if a fix truly requires user input (e.g. merge conflict with main, or an explicit product/design choice), report the blocker and what you need from the user; then stop.
- When reporting a blocker, state clearly: "PR command incomplete: [reason]. I need [X] from you before I can continue."

## Fallback PR Body Format

```markdown
## Summary
- ...

## Why
- ...

## Validation
- `command` -> result
- `command` -> result

## Risks / Rollback
- ...

## References
- .ai/PLANS/00x-*.md
```

## Quality Bar

- PR body can be understood without opening the full diff first.
- Validation evidence is explicit and reproducible.
- Known risks and follow-ups are transparent.
