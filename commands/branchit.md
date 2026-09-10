---
description: Create a new branch and git worktree. Always branches from main unless told otherwise. Flags a dirty tree; ignores temp/scratch files but mentions them.
---

# /branchit

You are creating a new branch + worktree for the user. Be terse. Do not invent steps. Always branch from `main` (or the repo's default branch) unless the user specifies a different base.

The user has authorized worktree creation by typing `/branchit`. Do not re-ask. Do stop and ask only if the dirty-tree check turns up real changes, or if the name arg is missing.

---

## Args

Parse from the command args:
- **name** (required) — the worktree slug. If missing, ask the user for one short kebab-case name (and stop until they answer).
- **base** (optional) — defaults to the repo's default branch. Override with `--from <branch>` or `from:<branch>`.

Branch name convention: match what the repo already uses. Check `git branch -a` and `git worktree list` — if existing worktrees follow `worktree-<name>`, use that; otherwise just use `<name>`. If unsure, default to `worktree-<name>`.

---

## Preflight

```bash
git rev-parse --is-inside-work-tree || (echo "Not a git repo." && exit 1)
git rev-parse --path-format=absolute --git-common-dir
git worktree list
git status --porcelain
```

Resolve:
- **Repo root** — the main working tree (NOT the current worktree if you're inside one). Derive it from `git worktree list` (first entry is the main tree). All new worktrees go under `<repo-root>/.claude/worktrees/<name>/` to match the existing convention. If that directory doesn't exist yet, create it.
- **Default branch** — `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` if available, else fall back to `main`, then `master`.
- **Dirty tree** — see below.

---

## Dirty-tree check

Run `git status --porcelain` from the current cwd. Classify each line:

**Temp/scratch (safe to ignore, just mention):**
- Untracked files in `tmp/`, `log/`, `node_modules/`, `.bundle/`, `coverage/`, `storage/`, `public/assets/`, `public/packs/`
- `.DS_Store`, `*.log`, `*.swp`, `*.swo`, `.env.local` (but flag `.env` itself)
- Untracked files matching `*.tmp`, `*.bak`, `scratch*`, `mockup*`
- Untracked files at repo root that look like one-off scratch (`*.html`, `*.txt`, `*.md`) the user clearly hasn't committed and that don't shadow a real path

**Real changes (STOP and report):**
- Any modified (`M`) or staged (`A`/`D`/`R`) files
- Untracked files inside `app/`, `lib/`, `config/`, `db/`, `test/`, `spec/`, `bin/` (or any directory that looks like real source)
- `.env` (without suffix)

If real changes exist: STOP. List them. Ask the user whether to (a) commit/stash first and re-run, or (b) proceed anyway (they confirm explicitly).

If only temp/scratch: mention them in one line ("Ignoring 3 scratch files in tmp/ and 1 .DS_Store"), then continue.

---

## Step 1: Fetch + create

```bash
git -C <repo-root> fetch origin --quiet
git -C <repo-root> worktree add <repo-root>/.claude/worktrees/<name> -b <branch-name> origin/<base>
```

Notes:
- Always base on `origin/<base>` so the worktree starts from the latest pushed main, not whatever the user's local main happens to be.
- If `<branch-name>` already exists, STOP and report — don't clobber. Suggest the user pick a different slug or pass an explicit `--branch <name>`.
- If the worktree path already exists, STOP — same reason.

---

## Step 2: Report

One short summary:
- Worktree path (absolute)
- Branch name
- Based on `<base>` at commit `<short-sha>`
- The single `cd` command the user can paste to enter it

Do not auto-`cd`. Do not start the dev server, install deps, or run anything else. The user drives from here.

---

## Output discipline

- Single line per step ("Step 1: created worktree at …").
- No verbose `git` output unless something failed.
- Final summary is 3–4 lines, no headers.

---

## Failure modes

- **Branch exists** — stop, report, suggest a fresh slug.
- **Worktree path exists** — stop, report, suggest a fresh slug.
- **Fetch fails** (no network, no remote) — fall back to local `<base>` and explicitly warn the user that the worktree is based on possibly-stale local state.
- **Not in a git repo** — stop and say so.
- **Real dirty changes** — stop, list files, ask how to proceed.

---

## What this skill is NOT

- Not a session-opener. Creating the worktree does not move the current Claude Code session into it; the user runs a new session (or `cd`s) themselves.
- Not a setup skill. No `bundle install`, no `yarn install`, no migrations. Just branch + worktree.
- Not a PR skill. Use `/ship` or `gh pr create` separately when ready.
