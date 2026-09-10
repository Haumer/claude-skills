# focus.py — human-watchable wrappers around browser-harness helpers.
#
# Load inside a browser-harness driver script:
#
#     exec(open(os.path.expanduser("~/.claude/skills/focus/focus.py")).read())
#
# Then use focus_* instead of raw click()/type_text()/js() whenever a person is
# watching the browser. Every wrapper first shows WHERE the agent's attention is
# (spotlight, cursor glide, label), then performs the real CDP action at exactly
# that spot. Nothing is faked: the click is a real Input.dispatchMouseEvent at
# the element's centre, the typing is real Input.insertText.
#
# Speed: set FOCUS_SPEED (float, default 1.0; 2.0 = twice as fast, 0.5 = slower)
# or call focus_speed(x). Set FOCUS_SPEED=0 to skip all pauses (overlay still shows).
#
# Interactive: the overlay's chat bubble lets the viewer pause/resume, step,
# stop, change speed, switch to "ask me" mode (Approve/Skip per action) and
# send messages. Pressing P on the page pauses and lets them draw annotated
# boxes; P again sends them. Every wrapper passes through _gate() first and
# every pause polls for interrupts, so those arrive within ~0.3 s.
# Stop raises FocusStopped; a message raises FocusMessage; boxes raise
# FocusAnnotations (read it, answer with focus_ack, continue with a new
# script — the chat state lives in the tab).
#
# The harness runs driver scripts through a nested exec(), where names defined
# at the top level land in a locals dict that function bodies cannot see. The
# last line of this file therefore copies everything it defines into globals().

import json as _json
import os as _os
import time as _time

FOCUS_DIR = _os.path.expanduser(_os.environ.get("FOCUS_SKILL_DIR", "~/.claude/skills/focus"))
_FOCUS_JS = open(_os.path.join(FOCUS_DIR, "focus.js")).read()
_SPEED = float(_os.environ.get("FOCUS_SPEED", "1.0"))
_STATE = {"mode": _os.environ.get("FOCUS_MODE", "auto"), "speed": _SPEED}


class FocusStopped(Exception):
    """The viewer pressed Stop in the dock."""
    def __str__(self):
        return ("FOCUS: the viewer pressed Esc/Stop — this run ended at the next action. "
                "Report where things stand; only if they ask you to carry on, call focus_resume() in the next script.")


class FocusMessage(Exception):
    """The viewer sent a message from the chat. .messages is the list of strings."""
    def __init__(self, messages):
        super().__init__(messages)
        self.messages = list(messages)
    def __str__(self):
        return "FOCUS: viewer says: " + " | ".join(self.messages) + "  (answer with focus_say, then continue with a new script)"


class FocusAnnotations(Exception):
    """The viewer drew boxes on the page (P mode). .boxes is a list of dicts:
    n, note, rect{x,y,w,h} (viewport), page{x,y}, element{tag,id,classes,selector,text}, text (what is inside the box).
    .screenshot is a PNG with the boxes drawn, taken the moment they arrived."""
    def __init__(self, boxes, screenshot=None):
        super().__init__(boxes)
        self.boxes = list(boxes)
        self.screenshot = screenshot
    def __str__(self):
        lines = ["FOCUS: viewer drew %d box%s on %s — look at the screenshot %s, answer with focus_ack(text), then continue with a new script"
                 % (len(self.boxes), "" if len(self.boxes) == 1 else "es", js("location.href") or "the page", self.screenshot or "(none)")]
        for b in self.boxes:
            el = b.get("element") or {}
            lines.append("  #%s note=%r rect=%s element=<%s%s%s> selector=%r text=%r region_text=%r" % (
                b.get("n"), b.get("note", ""), b.get("rect"),
                el.get("tag", "?"), ("#" + el["id"]) if el.get("id") else "",
                ("." + ".".join(el["classes"])) if el.get("classes") else "",
                el.get("selector"), (el.get("text") or "")[:120], (b.get("text") or "")[:200]))
        return "\n".join(lines)


def _raise_for(st):
    """Turn a polled state into the matching interrupt, if any."""
    if st.get("stopped"):
        raise FocusStopped()
    if st.get("annotations"):
        shot = screenshot("/tmp/focus-annotations.png")
        raise FocusAnnotations(st["annotations"], shot)
    if st.get("messages"):
        raise FocusMessage(st["messages"])


def _check():
    """Cheap interrupt check used inside every pause; consumes only interrupts."""
    raw = js("window.__focus && window.__focus.peek()")
    if not raw:
        return
    pk = _json.loads(raw)
    if pk.get("stopped") or pk.get("messages") or pk.get("annotations"):
        _raise_for(_json.loads(js("window.__focus.poll()")))


def _push_state():
    if js("!!(window.__focus && window.__focus.setState)"):
        js(f"window.__focus.setState({_q(_STATE)})")


def focus_speed(x):
    """1.0 = default pacing, 2.0 = twice as fast, 0 = no pauses. The viewer can change it in the dock too."""
    global _SPEED
    _SPEED = float(x)
    _STATE["speed"] = _SPEED
    _push_state()


def focus_mode(mode):
    """'auto' (default) or 'manual' — in manual mode every click/type/key/navigation waits for Approve or Skip in the dock."""
    _STATE["mode"] = mode
    _push_state()


def _gate(kind, label, approval=True):
    """Honour the dock: pause/step/stop/messages, and Approve/Skip in manual mode.

    Returns True to proceed, False if the viewer skipped this action."""
    global _SPEED
    focus_install()
    if approval:
        js(f"window.__focus.pending({_q(kind)}, {_q(label)})")
    while True:
        raw = js("window.__focus && window.__focus.poll()")
        if not raw:                      # page navigated under us — re-inject and retry
            _time.sleep(0.3)
            focus_install()
            continue
        st = _json.loads(raw)
        if st.get("speed") not in (None, _SPEED):
            _SPEED = float(st["speed"]); _STATE["speed"] = _SPEED
        _STATE["mode"] = st.get("mode", _STATE["mode"])
        _raise_for(st)
        if approval and _STATE["mode"] == "manual":
            if st.get("approve") == "yes":
                return True
            if st.get("approve") == "skip":
                return False
            _time.sleep(0.25)
            continue
        if st.get("paused") and not st.get("step"):
            _time.sleep(0.25)
            continue
        return True


def _pause(seconds):
    """Sleep in slices, polling the chat so Stop / messages / boxes interrupt within ~0.3 s."""
    if _SPEED <= 0:
        _check()
        return
    end = _time.time() + seconds / _SPEED
    while True:
        _check()
        left = end - _time.time()
        if left <= 0:
            return
        _time.sleep(min(0.3, left))


def _q(x):
    return _json.dumps(x)


def _target(t):
    """CSS selector string, or (x, y) / {x,y,w,h} in viewport px."""
    if isinstance(t, str):
        return _q(t)
    if isinstance(t, (tuple, list)):
        return _q({"x": t[0], "y": t[1]})
    return _q(t)


def focus_install():
    """Inject the overlay engine if this document doesn't have it yet. Safe to call often."""
    if js("!!(window.__focus && window.__focus.__v === 6)"):
        return True
    js(_FOCUS_JS)
    _push_state()
    return bool(js("!!window.__focus"))


def _call(method, target, label, extra=""):
    focus_install()
    return js(f"window.__focus.{method}({_target(target)}, {_q(label)}{extra})")


def focus_say(text, mood="info"):
    """Narration bar at the bottom. mood: info | warn | ok. Empty text hides it."""
    focus_install()
    js(f"window.__focus.say({_q(text)}, {_q(mood)})")
    return text


def focus_look(target, label="", hold=0.5):
    """Spotlight a region and glide the cursor to it. Returns its viewport rect or None."""
    _gate("LOOK", label or str(target), approval=False)
    r = _call("look", target, label)
    _pause(hold)
    return r


def focus_read(target, label="", seconds=None):
    """Spotlight a region, sweep a scan line over it, return its innerText.

    Duration scales with text length (about 250 words per 4 s) unless given."""
    _gate("READ", label or str(target), approval=False)
    text = js(f"(e=>e?e.innerText:null)(document.querySelector({_q(target)}))") if isinstance(target, str) else None
    if isinstance(target, str) and text is None:
        focus_say(f"Could not find: {label or target}", "warn")
        return None
    if seconds is None:
        words = len((text or "").split())
        seconds = min(3.0, max(0.9, words / 70.0))
    ms = int(seconds * 1000 / _SPEED) if _SPEED > 0 else 200
    _call("read", target, label, f", {ms}")
    return text


def focus_survey(candidates, question="", dwell=0.7):
    """Show the options being weighed before committing to one.

    candidates: list of (selector, label) tuples or {"target","label"} dicts.
    The cursor visits each one with a "CANDIDATE i/N" chip. In manual mode the
    chat offers them as buttons and this returns the viewer's index (or None
    for "you decide"); in auto mode it returns None and the agent decides."""
    _gate("SURVEY", question or f"{len(candidates)} candidates", approval=False)
    items = [c if isinstance(c, dict) else {"target": c[0], "label": c[1] if len(c) > 1 else str(c[0])} for c in candidates]
    if question:
        focus_say(question)
    ms = int(dwell * 1000 / _SPEED) if _SPEED > 0 else 150
    js(f"window.__focus.survey({_q(items)}, {ms})")
    if _STATE["mode"] != "manual":
        return None
    while True:                      # wait for the viewer's pick
        raw = js("window.__focus && window.__focus.poll()")
        if not raw:
            _time.sleep(0.3); focus_install(); continue
        st = _json.loads(raw)
        _raise_for(st)
        ch = st.get("choice")
        if ch is not None:
            return None if ch < 0 else ch
        _time.sleep(0.25)


def focus_ack(text):
    """Reply to the viewer's boxes (green bar + chat) and clear them from the page."""
    focus_install()
    js(f"window.__focus.ack({_q(text)})")
    return text


def focus_click(target, label="", settle=0.3, _gated=False):
    """Announce, glide, ripple, then really click the element's centre. Returns True if clicked."""
    if not _gated and not _gate("CLICK", label or str(target)):
        return False
    r = _call("act", target, label)
    if not r:
        focus_say(f"Could not find: {label or target}", "warn")
        return False
    click(r["cx"] + 4, r["cy"] + 2)  # same spot the cursor tip is pointing at
    _pause(settle)
    return True


def focus_click_at(x, y, label="", settle=0.3):
    """Coordinate click with the same choreography (for canvas UIs)."""
    return focus_click((x, y), label, settle)


def focus_type(target, text, label="", per_char=0.035, max_seconds=2.5):
    """Click into the field, then type for real, visibly, one character at a time."""
    if not _gate("TYPE", f"{label or target}: “{text[:50]}”"):
        return False
    if not focus_click(target, label or f"type: {text[:40]}", settle=0.15, _gated=True):
        return False
    focus_install()
    js(f"window.__focus.typing({_target(target)}, {_q(label or text[:60])})")
    delay = per_char / _SPEED if _SPEED > 0 else 0
    if delay * len(text) > max_seconds:
        delay = max_seconds / max(1, len(text))
    for ch in text:
        type_text(ch)
        if delay:
            _time.sleep(delay)
    js("window.__focus.doneTyping()")
    _pause(0.2)
    return True


def focus_press(key, label=""):
    """Press a key (Enter, Tab, Escape…) with a short narration beat."""
    if not _gate("KEY", f"{key} — {label}" if label else key):
        return False
    if label:
        focus_say(label)
    press_key(key)
    _pause(0.2)


def focus_goto(url, label=None, timeout=15.0):
    """Navigate in the current tab, re-inject the overlay, keep the narration bar alive."""
    if not _gate("NAVIGATE", label or url):
        return None
    focus_say(label or f"Opening {url}")
    _pause(0.3)
    goto(url)
    wait_for_load(timeout)
    focus_install()
    if label:
        focus_say(label)
    return page_info()


def focus_new_tab(url, label=None, timeout=15.0):
    """First navigation of a session: new tab, then overlay."""
    new_tab(url)
    wait_for_load(timeout)
    focus_install()
    focus_say(label or f"Opened {url}")
    _pause(0.3)
    return page_info()


def focus_scroll(dy=400, label="", steps=4):
    """Scroll in visible steps instead of one jump."""
    _gate("SCROLL", label or f"{dy}px", approval=False)
    if label:
        focus_say(label)
    info = page_info()
    for _ in range(steps):
        scroll(info["w"] // 2, info["h"] // 2, dy=dy // steps)
        _pause(0.12)


def focus_shot(path="/tmp/focus-shot.png", settle=0.45):
    """Screenshot with the overlay visible — this is the evidence frame.

    Waits for the overlay transitions (≤ 0.6 s) to finish first."""
    _pause(settle)
    return screenshot(path)


def focus_wait_for(cond, timeout=10.0, label=""):
    """Block until `cond` holds, polling every 0.15 s (interrupts still land).

    cond: a CSS selector (waits until it matches a visible element) or a
    JS expression prefixed with "js:" that must evaluate truthy. Returns True
    when it held, False on timeout — so scripts never need a fixed wait(4)."""
    expr = cond[3:] if cond.startswith("js:") else f"(e=>!!(e&&(e.offsetParent||e.getClientRects().length)))(document.querySelector({_q(cond)}))"
    end = _time.time() + timeout
    while True:
        _check()
        try:
            if js(expr):
                return True
        except Exception:
            pass
        if _time.time() >= end:
            if label:
                focus_say(f"Still waiting for: {label}", "warn")
            return False
        _time.sleep(0.15)


def focus_settled(quiet=0.3, timeout=8.0):
    """Return once the page's DOM has been quiet for `quiet` s (the overlay's own
    motion is ignored) or after `timeout` s. Use after a click that re-renders
    instead of guessing a wait()."""
    focus_install()
    r = js(f"window.__focus.settled({int(quiet * 1000)}, {int(timeout * 1000)})")
    _check()
    return r


def focus_resume():
    """Bring the overlay back after the viewer pressed Esc (or Stop). Only when they asked to continue."""
    focus_install()
    js("window.__focus && window.__focus.resume()")
    _push_state()
    return True


def _peek_tab(url, chars=1500, timeout=10.0):
    """Read a page in a background tab (for JS-rendered pages the fetch cannot see). Closes it afterwards."""
    tid = cdp("Target.createTarget", url=url, background=True)["targetId"]
    sid = cdp("Target.attachToTarget", targetId=tid, flatten=True)["sessionId"]
    ev = lambda expr: cdp("Runtime.evaluate", session_id=sid, expression=expr, returnByValue=True).get("result", {}).get("value")
    end = _time.time() + timeout
    while _time.time() < end and ev("document.readyState") != "complete":
        _time.sleep(0.2)
    _time.sleep(0.7)                                   # let a SPA paint
    val = ev("JSON.stringify({url:location.href,title:document.title,text:(document.body?document.body.innerText:'').replace(/\\s+/g,' ').trim().slice(0,%d),"
             "headings:[...document.querySelectorAll('h1,h2,h3')].map(h=>h.innerText.trim()).filter(Boolean).slice(0,20),"
             "links:document.querySelectorAll('a[href]').length,forms:document.querySelectorAll('form').length})" % chars)
    try:
        cdp("Target.closeTarget", targetId=tid)
    except Exception:
        pass
    d = _json.loads(val) if val else {"url": url, "error": "no result"}
    d["via"] = "tab"
    return d


def focus_peek(targets, label="", chars=1500, mode="auto"):
    """Sneak a look at where links lead WITHOUT navigating, so the next steps can be planned in one go.

    targets: a selector, a URL, or a list of them. Selectors resolve to the
    link under (or around) the element. Each page is fetched from the tab's own
    origin (cookies included) and reduced to {url, status, title, text, headings,
    links, forms}. mode "auto" falls back to a hidden background tab when the
    fetched HTML is thin (JS-rendered), "fetch" never does, "tab" always does.
    The viewer sees a dashed PEEKING ring on each link; nothing is clicked.
    Returns one dict for a single target, else a list (None where a target had no link)."""
    single = isinstance(targets, str)
    items = [targets] if single else list(targets)
    _gate("PEEK", label or f"{len(items)} page{'s' if len(items) != 1 else ''} ahead", approval=False)
    urls = []
    for t in items:
        if t.startswith(("http://", "https://")):
            urls.append(t); continue
        href = js(f"(e=>{{if(!e)return null;const a=e.closest?e.closest('a[href]'):null;return (a&&a.href)||e.href||null}})(document.querySelector({_q(t)}))")
        if not href:
            focus_say(f"Could not peek: no link at {label or t}", "warn")
            urls.append(None); continue
        js(f"window.__focus.peekAt({_q(t)}, {_q(label or 'reading ahead')}, {int(300 / _SPEED) if _SPEED > 0 else 80})")
        urls.append(href)
    live = [u for u in urls if u]
    fetched = {}
    if live and mode in ("auto", "fetch"):
        for u, r in zip(live, js(f"window.__focus.fetchText({_q(live)}, {int(chars)})") or []):
            fetched[u] = dict(r, via="fetch")
    out = []
    for u in urls:
        if not u:
            out.append(None); continue
        r = fetched.get(u)
        thin = (not r) or r.get("error") or len(r.get("text") or "") < 200
        if mode == "tab" or (mode == "auto" and thin):
            try:
                r = _peek_tab(u, chars)
            except Exception as e:                       # keep whatever the fetch gave us
                r = r or {"url": u, "error": str(e), "via": "tab"}
        out.append(r)
        _check()
    if js("!!(window.__focus && window.__focus.note)"):
        got = [f"{(r.get('title') or r.get('url') or '?')[:50]} ({len(r.get('text') or '')} chars)" for r in out if r]
        js(f"window.__focus.note({_q('peeked ahead: ' + '; '.join(got))})")
    return out[0] if single else out


def focus_clear():
    """Fade the overlay out and remove it."""
    if js("!!window.__focus"):
        js("window.__focus.clear()")
    return True


# --- make the wrappers visible to each other under the harness's nested exec() ---
globals().update({k: v for k, v in dict(locals()).items()
                  if not k.startswith("__") and (k.startswith(("focus_", "Focus", "_")) or k == "FOCUS_DIR")})
