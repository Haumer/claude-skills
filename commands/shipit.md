---
description: Ship the current branch to main and deploy. Pulls main in first, runs tests, looks for lost work, merges, pushes, deploys, smoke-tests prod.
---

# /shipit

You are running the user's preferred branch-shipping workflow. Be terse, surface evidence, stop on real problems. Do not invent steps. Do not skip steps. Each step's success is a precondition for the next.

The user has authorized this entire flow by typing `/shipit` — including push to main and deploy. Do not re-ask for permission at every step. Do stop and report if a step finds genuine trouble.

---

## Preflight

```bash
git rev-parse --is-inside-work-tree || (echo "Not a git repo." && exit 1)
git branch --show-current
git status --porcelain
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

Resolve:
- **Current branch** — must NOT be `main` / `master`. If on the base branch, stop: "You're on the base branch. /shipit is for shipping a feature branch, not for deploying main directly."
- **Base branch** — try `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, fall back to `main` then `master`.
- **Working tree** — must be clean. If dirty, stop and report. Do NOT auto-stash.
- **Worktree** — note if running inside a `.git/worktrees/...` checkout (some projects keep main and feature branches in separate working dirs); use absolute paths so behavior is deterministic.
- **Deploy auth** — detect the deploy mechanism now (same detection as Step 6: `config/deploy.yml` → kamal, `fly.toml` → fly, a `heroku` git remote → heroku, `.github/workflows/*deploy*` → CI). Then verify the credentials that mechanism needs are present, BEFORE doing merge/push work that would leave main ahead of prod if the deploy blocks:
  - **heroku** — `heroku auth:whoami` must succeed. If it says "not logged in", STOP: "Heroku not authenticated. Run `!heroku login` in a new prompt, then re-invoke `/shipit`." (The `!` prefix routes the interactive browser flow to the user's real terminal.) Also probe `git ls-remote heroku HEAD >/dev/null 2>&1`; if that fails but `heroku auth:whoami` succeeded, tell the user their `~/.netrc` is missing the `git.heroku.com` login/password entry — fix with `heroku auth:token` piped into a fresh netrc block, or reset via `heroku login`.
  - **kamal** — `kamal registry login --skip-push 2>/dev/null` or the equivalent auth probe from `config/deploy.yml`; if the registry / SSH keys aren't available, STOP with the fix command.
  - **fly** — `fly auth whoami` must succeed; otherwise STOP: "Run `!fly auth login` and re-invoke."
  - **CI-driven** — nothing to preflight; note that the push will trigger CI and continue.
  This check is cheap and prevents the "main pushed, prod still on old SHA" half-shipped state that happens when Step 6 discovers the auth problem after Step 5 already ran.

---

## Step 1: Bring main into the branch

```bash
git fetch origin --quiet
git log --oneline -1 origin/<base>
```

Sanity-check main is healthy:
- `origin/<base>` should match locally if the user has a local copy. Mismatches are usually fine but flag them.
- If commits exist on `origin/<base>` not yet on this branch, merge them in:
  ```bash
  git merge origin/<base> --no-edit
  ```
- If main has no new commits since the branch's base, say "No-op — main hasn't moved" and continue.

If the merge has conflicts: STOP. Do not auto-resolve. Report the conflicting files and let the user drive the resolution — then they re-run `/shipit`.

---

## Step 2: Health check + lost-work scan

**Tests** — detect framework and run only the test suites likely affected by the diff. Default to running everything if detection is unclear:
- Rails (Minitest): `bin/rails test` (or scope to `test/integration/<area>_test.rb` if the diff is narrow)
- Rails (RSpec): `bin/rspec`
- Bun/JS: `bun test` or `npm test` per project
- Pytest: `pytest`
- Go: `go test ./...`

If tests fail: STOP. Report failures verbatim. Do not guess fixes — show the user.

**Lost-work scan** — look for signals that important work didn't make it into the branch:
1. `git stash list` — any stashes on this branch?
2. `git status --porcelain` should be empty (already verified in preflight); re-check after the merge in case the merge surfaced anything.
3. `git log origin/<base>..HEAD --oneline` — sanity-check the branch's commits match what the user expects to ship.
4. `git diff origin/<base>..HEAD --stat` — eyeball the diff scope: any files changed that look unrelated to the branch's stated purpose?
5. Untracked files (`git ls-files --others --exclude-standard`) — anything important that should have been committed?

Report the lost-work findings as a short table, not prose. If anything looks risky, surface it BEFORE proceeding to step 3.

---

## Step 3: Gate

If step 2 turned up real issues (failing tests, suspicious untracked files, scope mismatches): STOP.
- Issue → either fix it directly (if obvious and bounded), or list the issues and ask the user how to handle each.
- Do not proceed to merge until clean.

If step 2 is clean: continue.

---

## Step 4: Merge into main + short check

Identify whether main lives in this same checkout or in a separate working directory (some projects use `git worktree` and keep main checked out elsewhere). Use the right working directory.

```bash
git checkout <base>
git pull --ff-only origin <base>
git merge --no-ff <branch> -m "Merge branch '<branch>'

<one-paragraph summary of what shipped — derive from the branch's commit log>"
```

The `--no-ff` is intentional — it preserves branch history as a unit, matching the project convention (check `git log --merges --oneline -3` on main if unsure).

**Short check on main:**
- Re-run the test suite — same tests as step 2, now against the merged tree. Catches merge-induced surprises.
- If migrations exist in the diff: flag for the user. Standard pattern is `kamal app exec ... db:migrate` against prod, then run locally and commit the regenerated `schema.rb`. Surface this so the user can decide order.

If anything fails on main: STOP. Offer to revert the merge (`git reset --hard ORIG_HEAD`) or fix forward.

---

## Step 5: Push to origin

```bash
git push origin <base>
```

Show the resulting commit range pushed.

---

## Step 6: Deploy

Detect the deploy mechanism:
- `config/deploy.yml` exists → **kamal** (`kamal deploy`)
- `fly.toml` exists → **fly** (`fly deploy`)
- `render.yaml` exists → flag and ask how the user wants to trigger Render
- `.github/workflows/*deploy*` exists → CI-driven, mention this; the push may already have triggered it
- None found → ask the user

For **kamal** specifically:
```bash
kamal app version              # show what's currently deployed
kamal deploy                   # full build + push + rolling update
```

Use Bash with `timeout: 600000` (10 min). Kamal deploys on this kind of project usually finish in 2–4 min; allow headroom.

Report the deploy duration and the commit SHA now serving traffic. If deploy fails, report stderr verbatim and stop.

---

## Step 7: Live smoke test

Identify production URL(s) from deploy config:
- kamal: parse `config/deploy.yml` for `host:` lines under `proxy:` (or top-level), or `kamal-proxy deploy --host=...` flags in deploy logs
- fly: `fly info -j | jq .Hostname`

Smoke test:
1. Hit the prod home URL, expect 200.
2. Identify routes touched by the diff (look at `git diff origin/<base>..MERGE_BASE -- config/routes.rb` and any new partials/views) and curl each one. Expect 200 unless the route is intentionally a redirect/404.
3. If the diff added a redirect, follow it and verify the destination resolves.
4. Confirm the deployed commit matches what we just pushed (kamal: `kamal app version`).

Report a small table: route → status code. Anything non-2xx-or-intended is an immediate flag — page the user, do not move on silently.

---

## Step 8: Clean up

Only after the branch has actually shipped (merged + pushed; deployed if a deploy step ran). Tear down the throwaway scaffolding this session created so it doesn't linger or get committed by a later run. Be conservative — remove ONLY what this session spun up, never the user's own files or anything tracked by git.

- **Dev servers** — stop any `rails server` / `bin/dev` / `vite`/`puma` you started for verification (e.g. a server on a scratch port). Kill by the port you launched, not a blanket `pkill puma` — the user may have other servers running. Confirm the port is free afterward.
- **Scratch / working files** — delete the session's artifacts: screenshots, `.playwright-mcp/` output dirs, scratch logs (e.g. `/tmp/<branch>-server.log`), throwaway diagnostic scripts. Leave safety backups, anything under version control, and intentionally-untracked project docs alone.
- **Background tasks** — stop any long-running background processes spawned for this ship.
- **Do NOT** touch shared dev/test DB seed data beyond what you created, and do NOT remove the worktree or branch — the user may still want them until the PR/merge is confirmed live.

Report a one-line summary of what was torn down. If nothing was created this session, say "nothing to clean up" and skip.

---

## Output discipline

- One-line summary at the start of each step ("Step 3: gate — clean, proceeding.")
- No verbose `git` output unless a step fails. Show only what matters.
- Final summary: branch shipped, commits pushed, deploy duration, prod commit, smoke results, cleanup.

---

## Failure modes — what to do

- **Conflicts merging main → branch** — stop, list files, let user resolve.
- **Tests fail on branch** — stop, show failures, do not auto-fix.
- **Tests fail on main after merge** — offer revert (`git reset --hard ORIG_HEAD` BEFORE pushing) or fix-forward.
- **Push rejected** — almost always means main moved while we were working. `git pull --rebase` on main, re-run from step 4's check, then push.
- **Deploy fails** — show stderr, stop. Do not retry without user input.
- **Smoke test 5xx** — immediate flag, do not silently complete. The user has 60–90 seconds to decide whether to roll back via `kamal rollback`.

---

## What this skill is NOT

- Not a PR-creation skill. If you want a PR, use `/ship` (gstack) or run `gh pr create` separately. `/shipit` is direct merge → push → deploy.
- Not a release-notes skill. If you want a CHANGELOG entry or release tag, that's separate.
- Not a hotfix skill. The "merge main into branch first" step assumes a normal-cadence ship. For an emergency hotfix on main, do it manually.
