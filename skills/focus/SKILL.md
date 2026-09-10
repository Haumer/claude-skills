---
name: focus
description: Make the agent's browser attention visible while it works through a site with browser-harness — an animated cursor glides to the element about to be used, a spotlight dims everything else, a scan line sweeps text being read, a chip names the action (LOOKING / READING / CLICKING / TYPING) and a narration bar explains why. Use whenever a person is watching the browser session live or a recording of it: demos, walkthroughs, QA tours, "show me how you did that", "let me watch".
---

# focus — show where the agent is looking

When a human watches an agent drive a browser, the frustrating part is not the
speed, it is the opacity: things change and nobody can tell what the agent saw
or intended. This skill adds a thin visual layer on top of browser-harness so
every observation and action is announced, located and animated *before* it
happens, and then happens for real at exactly that spot.

Load it inside any browser-harness driver script:

```python
import os
exec(open(os.path.expanduser("~/.claude/skills/focus/focus.py")).read())
```

`focus.py` re-injects `focus.js` into the page on every call, so navigations
and SPA re-renders do not lose the overlay.

## The wrappers

| Instead of | Use | What the viewer sees |
|---|---|---|
| `new_tab(url)` / `goto(url)` | `focus_new_tab(url, label)` / `focus_goto(url, label)` | narration bar stays alive across the navigation |
| `js("...innerText")` | `focus_read(selector, label)` | spotlight on the region, scan line sweeping it top to bottom, returns the text |
| looking at something | `focus_look(selector, label)` | spotlight + cursor glide + "LOOKING" chip |
| `click(x, y)` | `focus_click(selector, label)` / `focus_click_at(x, y, label)` | cursor glides, presses, ripple, then the real click lands on the same pixel |
| `type_text(text)` | `focus_type(selector, text, label)` | click into the field, then the characters appear one by one with a caret chip |
| `press_key("Enter")` | `focus_press("Enter", label)` | narration beat, then the real key |
| `scroll(...)` | `focus_scroll(dy, label)` | scrolls in visible steps |
| narration | `focus_say(text, mood)` | bottom bar; mood `info`, `warn` (amber, for bugs), `ok` (green, for verified state) |
| `screenshot(path)` | `focus_shot(path)` | same, but the overlay is in the frame, so it doubles as evidence |
| end of session | `focus_clear()` | overlay fades out |

Targets are CSS selectors or `(x, y)` viewport coordinates for canvas UIs.
Every wrapper returns the same thing the raw helper would, plus the target
rect where useful.

## The dock — the viewer talks back

Bottom-right of the page is a small control dock, the only part of the overlay
that accepts clicks. Every wrapper passes through a gate that honours it:

| Control | Effect on the driver |
|---|---|
| **Pause / Resume** | the next action blocks until Resume. While paused the page is the viewer's: they can log in, fix a form, scroll around. |
| **Step** | lets exactly one action through, then pauses again. |
| **Stop** | the next action raises `FocusStopped`; the script ends cleanly. |
| **1× / 2× / 0.5×** | changes pacing live (same as `focus_speed`). |
| **Ask me** | manual mode: every click, keystroke, typing and navigation shows "NEXT: CLICK …" and waits for **Approve** or **Skip**. Skip makes the wrapper return `False` without acting. Also settable with `focus_mode("manual")`. |
| **Message box** | the text is queued; the next action raises `FocusMessage` with `.messages`. |

Looking and reading are never gated for approval, only for pause/stop/messages,
so the agent can keep observing while the viewer decides.

**Protocol for `FocusMessage` and `FocusStopped`.** A driver script is one
`browser-harness` run, so an interrupt ends that run with the exception text
in the output ("FOCUS: viewer says: …"). Read it, answer with `focus_say`, and
continue with a new script. Dock state (mode, speed, paused) lives in the tab
and is restored after navigations, so nothing is lost between scripts. After a
pause or takeover, re-assert the page (URL + a selector) before continuing:
the viewer may have moved.

Set `FOCUS_MODE=manual` in the environment to start every session in
approval mode.

## Rules

1. **Announce, locate, act.** Never act on something the viewer has not seen
   highlighted. `focus_click` and `focus_type` do this for you. If you fall back
   to a raw helper, call `focus_look` first.
2. **Say why, not just what.** `focus_say("Checking the price before adding to
   cart — the listing said €12")` beats `focus_say("Clicking add to cart")`.
   The chip already names the mechanical action.
3. **Read visibly.** When you extract text for a decision, use `focus_read` on
   the region so the viewer sees which part of the page the decision came from.
4. **Never fake.** The overlay only decorates. Clicks are real CDP mouse events
   at the cursor tip; typing is real `Input.insertText`. Do not animate a click
   without performing it, and do not perform one you did not animate.
5. **Bugs go amber.** Anything unexpected gets `focus_say(..., "warn")` before
   you work around it, so the viewer never sees a silent retry.
6. **Respect the dock.** Never bypass the gate with raw helpers when a viewer
   is present. If a message arrives, answer it before doing anything else.
7. **Pace for humans.** Default pacing is about one action per second plus
   reading time. `focus_speed(2)` for a viewer who knows the flow,
   `focus_speed(0.6)` for a demo audience. `FOCUS_SPEED=0` turns pauses off for
   unattended runs while keeping the overlay for the screenshots.
8. **Clear at the end.** `focus_clear()` when the session is over, so the
   user's tab is left clean.

## Walkthrough integration

The `walkthrough` skill (and `/wt`) should load `focus` and use these wrappers
in place of its own narration-bar snippet. `focus_say` is the narration bar;
`focus_click` / `focus_type` / `focus_read` are the step actions. Everything
else in walkthrough (fresh persona, backend verification, bug log, run record)
is unchanged.

## Demo

```bash
browser-harness < ~/.claude/skills/focus/demo.py
```

Opens Wikipedia in a new tab, reads the intro, types a search, opens a result,
reads its first paragraph, takes evidence screenshots into `/tmp/focus-demo-*.png`
and clears the overlay.

## Extending

`focus.js` is plain DOM and CSS. Colour is one constant (`ACCENT`). New
choreography goes in as another `window.__focus.<verb>` returning a Promise;
mirror it with a `focus_<verb>` wrapper in `focus.py`. Keep animations under
700 ms and everything `pointer-events: none`, so the overlay can never eat a
click meant for the page.
