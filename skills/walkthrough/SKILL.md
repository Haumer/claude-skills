---
name: walkthrough
description: Annotated live product walkthrough in the user's browser — impersonate a fresh (or named) account, drive a user journey step by step with an on-screen narration bar, support replaying steps, and collect every bug hit along the way. Use when the user says "show me X as a customer", "walk through Y", "do the steps", or names a persona/journey to demo.
---

# /walkthrough — annotated live product tour

Drive the user's real browser through a product journey at watchable speed,
narrating each step in an on-screen bar. The user is watching live: pace ~10s
per page, never leave a broken state unexplained, and log every bug — a
walkthrough that finds a bug is a *successful* walkthrough.

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
the same journey (see §6).

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

## 3. Step-by-step driving

- **Dwell ~10s per page**, a beat longer on decision pages (previews,
  confirmations). Announce first, act second: note → sleep 3 → act.
- **Assert after every navigation** — URL substring AND a selector that proves
  it's the right page. Redirects race scripted navigation; the one time this
  was skipped, a sign-out redirect landed the script on a marketing page and
  it typed the persona's password into a newsletter form.
- **Fill via JS with input events** (`value=…; dispatchEvent(new Event('input',{bubbles:true}))`)
  so reactive frontends (Stimulus/React/Vue) notice.
- **Submit via a known field's form** — `querySelector('[name="…"]').form.requestSubmit()`.
  NEVER bare `querySelector('form')`: footer/newsletter/search forms exist on
  most pages and `querySelector` happily grabs them.
- **Confirm dialogs are usually NOT `window.confirm`.** Overriding it often
  does nothing (SweetAlert, custom modals). Pattern: click → sleep 1.5 → read
  the modal's text (surface it in the annotation) → sleep 2–3 → click the
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

## 4. Checkpoints & revert

Keep a driver-side list as you go: `steps = [(label, url, verify_cmd)]` where
`verify_cmd` re-checks that step's backend state. "Go back to step N" =
`goto(steps[n].url)` + re-inject the bar + re-annotate. Mutations are
forward-only: track every record the tour creates in a `created` dict and
offer two resets at the end — **replay** (jump to a URL, state as-is) or
**hard reset** (delete the created records, only with the user's say-so).
Say plainly which of the two a "revert" will be before doing it.

## 5. Bug collection

Every friction point goes into the log the moment it's hit:

- In-browser: amber `note(..., warn=True)` so the user sees it live.
- On disk: append to the scratchpad's `tour-bugs.md` — step, expected,
  observed, backend evidence, severity (blocks-journey / wrong-copy / cosmetic).

End-of-tour report (always, even when clean): steps completed, bugs found
(inlined), what was fixed live vs left open, which created records remain.
Bugs worth keeping become tasks or memory entries per the usual rules.

## 6. Persistence — every run leaves a record

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
