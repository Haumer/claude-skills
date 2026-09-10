---
name: walkthrough
description: Annotated live product walkthrough in the user's browser — impersonate a fresh (or named) account, drive a user journey step by step with an on-screen narration bar, support replaying steps, and collect every bug hit along the way. Use when the user says "show me X as a customer", "walk through Y", "do the steps", or names a persona/journey to demo.
---

# /walkthrough — annotated live product tour

Drive the user's real browser through a product journey at watchable speed,
narrating each step in an on-screen bar. The user is watching live: keep the
tour moving (a page should take seconds, not tens of seconds), never leave a
broken state unexplained, and log every bug — a walkthrough that finds a bug
is a *successful* walkthrough.

Arguments: `/walkthrough <journey> [as <persona>]`. No persona given →
**always impersonate a fresh account** (rule 1).

## 0. Project notes first

Before anything, read `walkthroughs/NOTES.md` at the repo root if it exists —
it holds this project's ground rules: dev server URL, how to log in / create
accounts fast, which dialog framework confirms use, what to strip from pages
(consent banners etc.), standing personas, domain validation rules (checksums,
formats), and how to verify state outside the UI. If it doesn't exist, create
it as you learn these facts during the first run — the next run must not pay
the same tax. Prior runs live in `walkthroughs/*.md`; check for one covering
the same journey (see §7).

## 1. Impersonation — fresh unless specified

Fresh persona = invent a plausible one for the product's market (name,
details, a `.test`-domain email) and go through the REAL signup funnel — the
funnel is part of what's being demoed. If the email exists from a prior run,
suffix it; never reuse an account unless the user asked for "the same one".
Named persona → use the project's fast-login mechanism from NOTES.md.

## 2. Annotation bar

**Preferred: the `focus` skill.** If `~/.claude/skills/focus/focus.py` exists,
load it at the top of every driver script and use `focus_say` for narration and
`focus_click` / `focus_type` / `focus_read` / `focus_look` for the actions —
the viewer then sees a cursor glide to each element, a spotlight on it, a chip
naming the action, and a scan line over anything you read. Bugs use
`focus_say(..., "warn")`. Only fall back to the bar snippet below when `focus`
is not installed.

```python
import os
exec(open(os.path.expanduser("~/.claude/skills/focus/focus.py")).read())
```

**Fallback: the bare bar.**

Inject after every navigation (navigations destroy it). Two gotchas baked
into this snippet: build the JS with `.replace(...)` + `json.dumps` — Python
`%`-formatting explodes on CSS percent signs — and define everything INSIDE
the function, because top-level names in a driver script are often invisible
inside `def` bodies (exec scoping).

```python
def note(text, warn=False):
    bar = ("(d=>{let b=d.getElementById('tour-note');if(!b){b=d.createElement('div');b.id='tour-note';d.body.appendChild(b);"
           "b.style.cssText='position:fixed;bottom:18px;left:50vw;transform:translateX(-50vw);max-width:760px;width:96vw;"
           "z-index:2147483647;background:#0f172a;color:#fff;padding:14px 22px;border-radius:14px;"
           "font:600 15px/1.45 system-ui;box-shadow:0 10px 40px rgba(0,0,0,.45);text-align:center'}"
           "b.style.background=BG;b.textContent=TEXT})(document)")
    import json
    js(bar.replace("TEXT", json.dumps(text)).replace("BG", json.dumps("#7c2d12" if warn else "#0f172a")))
```

Every step gets `note("Step N/M — what is happening and why it matters")`.
Bugs get the amber `warn=True` bar with an honest sentence ("Live find: …
fixing it, one minute"). Remove `#tour-note` when the tour ends.

## 3. Speed — the tour is only as fast as your turn count

The browser is not the bottleneck; a harness script starts in 50 ms. What
makes a tour crawl is one action per script with a full think in between,
plus fixed `sleep`s copied from habit. Rules:

- **No fixed sleeps.** `focus_settled()` returns the moment the DOM goes
  quiet; `focus_wait_for("#selector")` the instant the element is there. The
  animations already pace the viewer; a `sleep(3)` on top is dead air.
- **Map, then plan several steps.** `focus_map()` returns every visible
  clickable/typeable element with a verified-unique selector in one call;
  `print(focus_brief(m))` is what you read instead of a screenshot and five
  probes. From it, write the next 3–6 steps at once.
- **Run them as one plan.** `focus_run([...], label)` rehearses the steps
  in a hidden tab that shares the session, then performs them visibly. Give
  every navigating step an `expect` (`url:`, `text:`, `js:` or a selector):
  if the rehearsal fails at step k, only the k steps before it are performed
  and the result carries `ahead`, the map of what the failing step actually
  produced, so the next script starts from knowledge, not a guess. A tour of
  N pages should need roughly N/3 scripts, not 3N.
- **Never rehearse a mutation.** Signup, checkout, delete, send: those steps
  run with `rehearse=False`, alone or at the end of a plan (the hidden tab
  would perform them for real too). Read-only steps (navigation, search,
  filters, opening a preview) are safe to rehearse.
- **Peek before you decide.** `focus_peek([...links])` reads where links go
  without leaving the page, so "which of these is the pricing page" is a
  fetch, not a navigation plus a turn.
- **Batch the verification too.** Run the backend checks for a whole plan in
  one command after it, not one shell call per step.

Announce first, act second still holds: `focus_run` does that per step. The
only deliberate pauses are on decision pages (previews, confirmations),
where one `focus_read` of the decisive text is enough.

## 4. Step-by-step driving

- **Assert after every navigation** — URL substring AND a selector that proves
  it's the right page. Redirects race scripted navigation; the one time this
  was skipped, a sign-out redirect landed the script on a marketing page and
  it typed the persona's password into a newsletter form.
- **Type with `focus_type`** (real keystrokes, so Stimulus/React/Vue notice).
  Only when a field refuses real input fill via JS with input events
  (`value=…; dispatchEvent(new Event('input',{bubbles:true}))`).
- **Submit via a known field's form** — `querySelector('[name="…"]').form.requestSubmit()`.
  NEVER bare `querySelector('form')`: footer/newsletter/search forms exist on
  most pages and `querySelector` happily grabs them.
- **Confirm dialogs are usually NOT `window.confirm`.** Overriding it often
  does nothing (SweetAlert, custom modals). Pattern: click → `focus_settled()`
  → `focus_read` the modal's text (surfaces it in the annotation) → click the
  modal's own confirm button. Record the framework + selector in NOTES.md.
- **File inputs may auto-submit** on selection. Set the file, then check the
  URL before submitting anything — a second submit can skip a preview page
  the user was supposed to see.
- **Verify state OUTSIDE the UI after every mutating step** (rails runner,
  psql, an API call — whatever NOTES.md says). The UI lies by omission: a
  click can no-op with no error. If the backend says the step didn't happen,
  that's a bug to log — not a retry to hide.
- Domain-valid data only (real checksums, real formats — e.g. EAN-13 check
  digit `(10 - base12.chars.each_with_index.sum { |d,i| d.to_i * (i.even? ? 1 : 3) } % 10) % 10`).
  Apps validate; invented identifiers derail tours.

## 5. Checkpoints & revert

Keep a driver-side list as you go: `steps = [(label, url, verify_cmd)]` where
`verify_cmd` re-checks that step's backend state. "Go back to step N" =
`goto(steps[n].url)` + re-inject the bar + re-annotate. Mutations are
forward-only: track every record the tour creates in a `created` dict and
offer two resets at the end — **replay** (jump to a URL, state as-is) or
**hard reset** (delete the created records, only with the user's say-so).
Say plainly which of the two a "revert" will be before doing it.

## 6. Bug collection

Every friction point goes into the log the moment it's hit:

- In-browser: amber `note(..., warn=True)` so the user sees it live.
- On disk: append to the scratchpad's `tour-bugs.md` — step, expected,
  observed, backend evidence, severity (blocks-journey / wrong-copy / cosmetic).

End-of-tour report (always, even when clean): steps completed, bugs found
(inlined), what was fixed live vs left open, which created records remain.
Bugs worth keeping become tasks or memory entries per the usual rules.

## 7. Persistence — every run leaves a record

Write each run to `walkthroughs/<yyyy-mm-dd>-<journey-slug>.md` at the repo
root (check the project's gitignore conventions — some repos keep these
local-only on purpose). The file is the replayable record:

- **Persona**: account details, fast-login instructions, entitlement state.
- **Steps**: the `steps` list — label, URL, verify command. A later session
  can replay any step from this alone.
- **Created records**: model + ids, so cleanup or reuse works months later.
- **Bugs**: the log inlined, each marked fixed-live / open.
- **Verdict**: one paragraph — what the journey felt like, what to fix first.

At the START of a run, diff against the latest prior run of the same journey
and call out regressions ("worked on 08-27, broken now") — the walkthrough
archive is the cheapest regression suite the project has. Personas worth
keeping become standing fixtures in NOTES.md.
