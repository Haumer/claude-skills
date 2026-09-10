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
import re as _re
import time as _time

FOCUS_DIR = _os.path.expanduser(_os.environ.get("FOCUS_SKILL_DIR", "~/.claude/skills/focus"))
_FOCUS_JS = open(_os.path.join(FOCUS_DIR, "focus.js")).read()
import hashlib as _hashlib
_FOCUS_SRC = _hashlib.sha1(_FOCUS_JS.encode()).hexdigest()[:10]
_FOCUS_JS = _FOCUS_JS.replace('"__SRC__"', _json.dumps(_FOCUS_SRC), 1)
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


def focus_front():
    """Bring the controlled tab to the front if it is hidden behind another one.

    A hidden tab throttles timers to 1 Hz (every animation crawls) and drops synthetic
    input, so nothing works and nobody sees it. Returns True if it had to switch."""
    if js("document.visibilityState") != "hidden":
        return False
    url = js("location.href")
    tid = next((t["targetId"] for t in cdp("Target.getTargets").get("targetInfos", [])
                if t.get("type") == "page" and t.get("url") == url and t.get("title", "").startswith("\U0001F7E2")), None)
    if tid:
        cdp("Target.activateTarget", targetId=tid)
        _time.sleep(0.15)
    focus_install()
    if js("!!(window.__focus && window.__focus.note)"):
        js("window.__focus.note('brought this tab to the front — it was hidden, and a hidden tab neither animates nor takes input')")
    return True


def _gate(kind, label, approval=True):
    """Honour the dock: pause/step/stop/messages, and Approve/Skip in manual mode.

    Returns True to proceed, False if the viewer skipped this action."""
    global _SPEED
    focus_install()
    focus_front()
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
    if js(f"!!(window.__focus && window.__focus.__v === 8 && window.__focus.__src === {_q(_FOCUS_SRC)})"):
        return True
    js(_FOCUS_JS)
    _push_state()
    js("window.__focus && window.__focus.ensure()")     # build the scene now, restoring the pre-navigation one if there is a snapshot
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


def focus_peek(targets, label="", chars=1500, mode="auto"):
    """Sneak a look at where links lead WITHOUT navigating, so the next steps can be planned in one go.

    targets: a selector, a URL, or a list of them. Selectors resolve to the
    link under (or around) the element. Each page is fetched from the tab's own
    origin (cookies included) and reduced to {url, status, title, text, headings,
    links, forms, els} — els is the interactive-element map (see focus_map). mode "auto" falls back to a hidden background tab when the
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
        for u, r in zip(live, js(f"window.__focus.fetchText({_q(live)}, {int(chars)}, {_q(_MAP_JS)})") or []):
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


# --- page map: every interactive element with a stable selector, in one call ---
_MAP_JS = r"""(root, limit, withText) => {
  const doc = root.ownerDocument || root, win = doc.defaultView, live = !!win;
  const esc = (x) => (win && win.CSS && win.CSS.escape) ? win.CSS.escape(x) : String(x).replace(/([^\w-])/g, "\\$1");
  const vis = (e) => { if (!live) return true; const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
    const st = win.getComputedStyle(e); return st.visibility !== "hidden" && st.display !== "none" && st.opacity !== "0"; };
  const attr = (e, a) => e.getAttribute(a) || "";
  const txt = (e) => { const t = (live && e.innerText != null ? e.innerText : e.textContent) || "";
    const alt = attr(e, "aria-label") || attr(e, "title") || attr(e, "placeholder") || attr(e, "alt") || ((e.querySelector && e.querySelector("img[alt]")) || {}).alt || "";
    return (t.trim() || alt).replace(/\s+/g, " ").trim().slice(0, 80); };
  const uniq = (sel, scope) => { try { return scope.querySelectorAll(sel).length === 1; } catch (_) { return false; } };
  const selFor = (e, scope) => {
    if (e.id && uniq("#" + esc(e.id), scope)) return "#" + esc(e.id);
    for (const a of ["data-testid", "data-test", "data-qa", "name", "aria-label", "placeholder", "href", "title", "value"]) {
      const v = attr(e, a); if (!v || v.length > 80) continue;
      const sel = e.tagName.toLowerCase() + "[" + a + "=" + JSON.stringify(v) + "]"; if (uniq(sel, scope)) return sel;
    }
    const parts = []; let cur = e;
    while (cur && cur.nodeType === 1 && cur !== scope && parts.length < 7) {
      if (cur.id && uniq("#" + esc(cur.id), scope)) { parts.unshift("#" + esc(cur.id)); break; }
      const tag = cur.tagName.toLowerCase(), sibs = [...cur.parentNode.children].filter((c) => c.tagName === cur.tagName);
      parts.unshift(sibs.length > 1 ? tag + ":nth-of-type(" + (sibs.indexOf(cur) + 1) + ")" : tag);
      cur = cur.parentNode;
    }
    const sel = parts.join(" > "); return uniq(sel, scope) ? sel : null;
  };
  const Q = "a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=option],[role=checkbox],[role=radio],[role=combobox],[contenteditable=true],[onclick]";
  const els = [], seen = new Set();
  const walk = (scope, shadow) => {
    for (const e of scope.querySelectorAll(Q)) {
      if (els.length >= limit) return;
      if (!vis(e) || (e.closest && e.closest("#__fx-layer"))) continue;
      const tag = e.tagName.toLowerCase(), t = txt(e), href = attr(e, "href");
      const key = tag + "|" + t + "|" + href;
      if (seen.has(key) && !/^(input|select|textarea)$/.test(tag)) continue; seen.add(key);
      const o = { i: els.length, tag, text: t };
      const role = attr(e, "role"); if (role) o.role = role;
      if (tag === "input") o.type = e.type || "text";
      if (e.name) o.name = e.name;
      if (href) o.href = live ? (e.href || href) : href;
      if (e.disabled) o.disabled = true;
      if (/^(input|textarea|select)$/.test(tag) && e.value) o.value = String(e.value).slice(0, 60);
      if (tag === "select") o.options = [...e.options].map((x) => x.text.trim()).slice(0, 12);
      if (live) { const r = e.getBoundingClientRect(); o.rect = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }
      if (shadow) o.shadow = true; else { const sel = selFor(e, doc); if (sel) o.sel = sel; }
      els.push(o);
    }
    for (const h of scope.querySelectorAll("*")) { if (els.length >= limit) return; if (h.shadowRoot) walk(h.shadowRoot, true); }
  };
  walk(doc, false);
  const headings = [...doc.querySelectorAll("h1,h2,h3")].filter(vis).map((h) => ((live ? h.innerText : h.textContent) || "").replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 20);
  const out = { url: live ? win.location.href : "", title: (doc.title || "").trim(), headings, els, count: els.length };
  if (withText) out.text = ((doc.body && (live ? doc.body.innerText : doc.body.textContent)) || "").replace(/\s+/g, " ").trim().slice(0, withText === true ? 600 : withText);
  return out;
}"""

# Mutation clock for a tab without the overlay: installed once per document, polled from Python
# (timers in a hidden tab are throttled to 1 Hz, so the polling has to live on this side).
_MUT_JS = ("(()=>{if(!window.__fxmo){window.__fxLast=Date.now();window.__fxmo=new MutationObserver(()=>{window.__fxLast=Date.now()});"
           "window.__fxmo.observe(document.documentElement,{childList:true,subtree:true,characterData:true});return 0}return Date.now()-window.__fxLast})()")


def focus_map(limit=60, chars=600):
    """One call instead of a screenshot and five probes: {url, title, headings, text, els, count}.

    els: visible interactive elements in page order — {i, tag, text, sel, rect, href?, type?,
    name?, value?, options?, role?, disabled?, shadow?}. `sel` is a selector verified unique
    in the document; elements inside shadow roots have no sel (use rect with focus_click_at).
    Print it with focus_brief(m)."""
    focus_install()
    js(f"window.__focus.chip('MAPPING', 'reading every clickable thing on this page')")
    m = _json.loads(js(f"JSON.stringify(({_MAP_JS})(document, {int(limit)}, {int(chars)}))"))
    js(f"window.__focus.note({_q('mapped %d interactive elements' % m['count'])})")
    return m


def focus_brief(m, n=None):
    """Compact text of a map (or a peek/run result carrying one): one line per element."""
    if m is None:
        return "(no map)"
    if "els" not in m and isinstance(m.get("map"), dict):
        m = m["map"]
    lines = [f"{m.get('title') or '?'}  |  {m.get('url') or ''}"]
    if m.get("headings"):
        lines.append("headings: " + " / ".join(m["headings"][:8]))
    if m.get("text"):
        lines.append("text: " + m["text"][:300])
    for e in (m.get("els") or [])[: n or 999]:
        bits = [f"[{e['i']}]", e["tag"] + (f"[{e['type']}]" if e.get("type") else "") + (f"({e['role']})" if e.get("role") else "")]
        if e.get("text"):
            bits.append(_json.dumps(e["text"][:50], ensure_ascii=False))
        if e.get("value"):
            bits.append("value=" + _json.dumps(e["value"][:30], ensure_ascii=False))
        if e.get("options"):
            bits.append("options=" + "|".join(e["options"][:6]))
        if e.get("href"):
            bits.append(e["href"][:70])
        bits.append("sel=" + e["sel"] if e.get("sel") else ("shadow @" + str(e.get("rect")) if e.get("shadow") else "@" + str(e.get("rect"))))
        if e.get("disabled"):
            bits.append("(disabled)")
        lines.append(" ".join(bits))
    return "\n".join(lines)


# --- hidden tab: same cookies as the visible one, driven at DOM level ---
class _Shadow:
    """A background tab the viewer never sees. It shares the browser's session, so a logged-in
    journey rehearses as logged in. The tab never gets focus, so real Input events are dropped;
    clicks, typing and keys are performed at DOM level instead (el.click(), the native value
    setter plus input/change events, KeyboardEvents plus form.requestSubmit for Enter)."""

    def __init__(self, url, timeout=10.0):
        self.tid = cdp("Target.createTarget", url=url, background=True)["targetId"]
        self.sid = cdp("Target.attachToTarget", targetId=self.tid, flatten=True)["sessionId"]
        self.wait_loaded(timeout)

    def ev(self, expr, await_=False):
        r = cdp("Runtime.evaluate", session_id=self.sid, expression=expr, returnByValue=True, awaitPromise=await_)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError((d.get("exception") or {}).get("description") or d.get("text") or "js error")
        return r.get("result", {}).get("value")

    def wait_loaded(self, timeout=10.0):
        end = _time.time() + timeout
        while _time.time() < end:
            try:
                if self.ev("location.href") != "about:blank" and self.ev("document.readyState") == "complete":
                    break
            except Exception:
                pass
            _time.sleep(0.1)
        return self.settled()

    def settled(self, quiet=0.3, timeout=6.0):
        end = _time.time() + timeout
        while _time.time() < end:
            try:
                if self.ev(_MUT_JS) >= quiet * 1000:
                    return True
            except Exception:
                pass
            _time.sleep(0.1)
        return False

    def wait_for(self, expr, timeout=6.0):
        end = _time.time() + timeout
        while True:
            try:
                if self.ev(expr):
                    return True
            except Exception:
                pass
            if _time.time() >= end:
                return False
            _time.sleep(0.1)

    def map(self, limit=60, chars=600):
        return _json.loads(self.ev(f"JSON.stringify(({_MAP_JS})(document, {int(limit)}, {int(chars)}))"))

    def do(self, st):
        k, t = st["kind"], st.get("target")
        if k == "goto":
            cdp("Page.navigate", session_id=self.sid, url=t); self.wait_loaded(); return True
        if k == "click":
            ok = self.ev(f"(e=>{{if(!e)return false;e.scrollIntoView({{block:'center'}});e.click();return true}})(document.querySelector({_q(t)}))")
            if not ok:
                return False
            _time.sleep(0.15); self.wait_loaded(); return True
        if k == "type":
            ok = self.ev(f"""(e=>{{if(!e)return false;e.focus();const p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
                const d=Object.getOwnPropertyDescriptor(p,'value');if(d&&d.set)d.set.call(e,{_q(st['text'])});else e.value={_q(st['text'])};
                e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return true}})(document.querySelector({_q(t)}))""")
            if ok:
                self.settled()
            return bool(ok)
        if k == "press":
            key = st["key"]; code = {"Enter": 13, "Escape": 27, "Tab": 9, "ArrowDown": 40, "ArrowUp": 38, "Backspace": 8}.get(key, 0)
            self.ev(f"""(()=>{{const e=document.activeElement||document.body;const o={{key:{_q(key)},code:{_q(key)},keyCode:{code},which:{code},bubbles:true,cancelable:true}};
                const ok=e.dispatchEvent(new KeyboardEvent('keydown',o));e.dispatchEvent(new KeyboardEvent('keypress',o));e.dispatchEvent(new KeyboardEvent('keyup',o));
                const f=e.form||(e.closest&&e.closest('form'));if(ok&&{_q(key)}==='Enter'&&f){{if(f.requestSubmit)f.requestSubmit();else f.submit()}}}})()""")
            _time.sleep(0.15); self.wait_loaded(); return True
        if k == "wait":
            return self.wait_for(_expect_expr(t), st.get("timeout", 6.0))
        if k == "read":
            st["_text"] = self.ev(f"(e=>e?e.innerText:null)(document.querySelector({_q(t)}))")
            return st["_text"] is not None
        if k == "scroll":
            self.ev(f"scrollBy(0,{int(st.get('dy', 400))})"); self.settled(); return True
        return True                                  # say / unknown: nothing to rehearse

    def close(self):
        try:
            cdp("Target.closeTarget", targetId=self.tid)
        except Exception:
            pass


def _peek_tab(url, chars=1500, timeout=10.0):
    """Read a page in a hidden tab (for JS-rendered pages the fetch cannot see). Closes it afterwards."""
    sh = _Shadow(url, timeout)
    try:
        m = sh.map(60, chars)
    finally:
        sh.close()
    m["links"] = len([e for e in m["els"] if e.get("href")])
    m["via"] = "tab"
    return m


# --- run a plan: rehearse it in the hidden tab, then perform it visibly, in one script ---
def _norm_step(s):
    """('click', sel, label) / ('type', sel, text, label) / ('press', key, label) / ('goto', url, label)
    / ('wait', cond) / ('read', sel, label) / ('scroll', dy) / ('say', text) — or the same as dicts.
    Any form may carry expect= (selector, 'js:', 'text:', 'url:') and timeout=."""
    if isinstance(s, dict):
        d = dict(s)
    else:
        k, rest = s[0], list(s[1:])
        d = {"kind": k}
        if k == "type":
            d["target"], d["text"] = rest[0], rest[1]; d["label"] = rest[2] if len(rest) > 2 else ""
        elif k == "press":
            d["key"] = rest[0]; d["label"] = rest[1] if len(rest) > 1 else ""
        elif k == "say":
            d["text"] = rest[0]; d["mood"] = rest[1] if len(rest) > 1 else "info"
        elif k == "scroll":
            d["dy"] = rest[0] if rest else 400; d["label"] = rest[1] if len(rest) > 1 else ""
        else:
            d["target"] = rest[0]; d["label"] = rest[1] if len(rest) > 1 else ""
    d.setdefault("label", "")
    return d


def _expect_expr(x):
    """selector | 'js:<expr>' | 'text:<substring>' | 'url:<substring>' -> JS expression."""
    if x.startswith("js:"):
        return x[3:]
    if x.startswith("text:"):
        return f"(document.body.innerText||'').includes({_q(x[5:])})"
    if x.startswith("url:"):
        return f"location.href.includes({_q(x[4:])})"
    return f"(e=>!!(e&&(e.offsetParent||e.getClientRects().length)))(document.querySelector({_q(x)}))"


def _step_name(st):
    k = st["kind"]
    return {"type": f"type {st.get('text', '')[:30]!r} into {st.get('target')}", "press": f"press {st.get('key')}",
            "say": "say", "scroll": f"scroll {st.get('dy', 400)}"}.get(k, f"{k} {st.get('target')}")


def _rehearse(steps, limit, chars):
    """Run the steps in a hidden tab starting from the visible tab's URL. Returns (records, skipped_reason)."""
    url = js("location.href")
    live_title = js("document.title")
    sh = _Shadow(url)
    recs = []
    try:
        strip = lambda t: _re.sub(r"^[^\w(\[]+", "", t or "").strip()   # the overlay prefixes the title with a status dot
        if strip(sh.ev("document.title")) != strip(live_title):
            return recs, f"the hidden tab shows a different page for this URL ({sh.ev('document.title')!r} vs {live_title!r}); the state is not in the URL"
        for i, st in enumerate(steps):
            rec = {"i": i, "step": _step_name(st), "ok": True}
            t0 = _time.time()
            try:
                acted = sh.do(st)
            except Exception as e:
                acted = False; rec["why"] = f"error: {str(e)[:160]}"
            if not acted:
                rec["ok"] = False; rec.setdefault("why", "target not found")
            elif st.get("expect") and not sh.wait_for(_expect_expr(st["expect"]), st.get("timeout", 6.0)):
                rec["ok"] = False; rec["why"] = f"expected {st['expect']!r} did not appear"
            if st.get("_text") is not None:
                rec["text"] = st.pop("_text")
            try:
                rec["url"], rec["title"] = sh.ev("location.href"), sh.ev("document.title")
            except Exception:
                pass
            if not rec["ok"] or i == len(steps) - 1:
                try:
                    rec["map"] = sh.map(limit, chars)
                except Exception:
                    pass
            rec["s"] = round(_time.time() - t0, 2)
            recs.append(rec)
            _check()
            if not rec["ok"]:
                break
        return recs, None
    finally:
        sh.close()


def _do_visible(st):
    """Perform one step with the normal choreography; returns a record."""
    k, t, label = st["kind"], st.get("target"), st.get("label", "")
    rec = {"step": _step_name(st), "ok": True}
    t0 = _time.time()
    if k == "click":
        rec["ok"] = bool(focus_click(t, label)); focus_settled()
    elif k == "type":
        rec["ok"] = bool(focus_type(t, st["text"], label))
    elif k == "press":
        rec["ok"] = focus_press(st["key"], label) is not False; focus_settled()
    elif k == "goto":
        rec["ok"] = focus_goto(t, label) is not None
    elif k == "wait":
        rec["ok"] = focus_wait_for(t, st.get("timeout", 6.0), label)
    elif k == "read":
        rec["text"] = focus_read(t, label); rec["ok"] = rec["text"] is not None
    elif k == "scroll":
        focus_scroll(st.get("dy", 400), label)
    elif k == "say":
        focus_say(st["text"], st.get("mood", "info"))
    if rec["ok"] and st.get("expect"):
        if not focus_wait_for("js:" + _expect_expr(st["expect"]), st.get("timeout", 6.0)):
            rec["ok"] = False; rec["why"] = f"expected {st['expect']!r} did not appear"
    elif not rec["ok"]:
        rec["why"] = "target not found or skipped"
    rec["url"] = js("location.href")
    rec["s"] = round(_time.time() - t0, 2)
    return rec


def focus_run(steps, label="", rehearse=True, limit=60, chars=600):
    """Several steps in one script. With rehearse=True (default) the plan is first replayed in a
    hidden tab that shares the session; the viewer sees a REHEARSING chip. If the rehearsal
    fails at step k, only the k steps before it are performed visibly and the result carries
    `ahead`: the map of what the failing step actually produced, so the next script starts
    from knowledge instead of a guess. Never rehearse a step with side effects (an order, a
    message, a delete): pass rehearse=False for those.

    Returns {ok, done, steps:[{step, ok, why?, url, text?}], stopped_at?, why?, ahead?,
    rehearsal:[...], map: map of the visible page at the end}."""
    steps = [_norm_step(s) for s in steps]
    _gate("RUN", label or f"{len(steps)} steps", approval=False)
    if label:
        focus_say(label)
    out = {"ok": True, "done": 0, "steps": [], "rehearsal": None, "map": None}
    to_run, failed = steps, None
    if rehearse and steps:
        js(f"window.__focus.chip('REHEARSING', {_q('%d steps in a hidden tab' % len(steps))})")
        t0 = _time.time()
        recs, skipped = _rehearse(steps, limit, chars)
        out["rehearsal"] = recs
        if skipped:
            out["rehearsal_skipped"] = skipped
            focus_say("Could not rehearse: " + skipped + " — performing the steps directly", "warn")
        else:
            failed = next((r for r in recs if not r["ok"]), None)
            if failed:
                k = failed["i"]; to_run = steps[:k]
                out.update(stopped_at=k, why=failed.get("why"), ahead=failed.get("map"))
                focus_say(f"Rehearsal stopped at step {k + 1} ({failed['step']}): {failed.get('why')} — doing the {k} step{'s' if k != 1 else ''} before it, then re-planning", "warn")
            else:
                js(f"window.__focus.note({_q('rehearsed %d steps in %.1f s: all fine, performing them now' % (len(steps), _time.time() - t0))})")
        js("window.__focus.chip('THINKING', '')")
    for i, st in enumerate(to_run):
        rec = _do_visible(st)
        out["steps"].append(rec)
        if not rec["ok"]:
            out["ok"] = False
            focus_say(f"Step {i + 1} ({rec['step']}) failed: {rec.get('why')}", "warn")
            break
        out["done"] = i + 1
    if failed:
        out["ok"] = False
    out["map"] = focus_map(limit, chars)
    return out


def focus_clear():
    """Fade the overlay out and remove it."""
    if js("!!window.__focus"):
        js("window.__focus.clear()")
    return True


# --- make the wrappers visible to each other under the harness's nested exec() ---
globals().update({k: v for k, v in dict(locals()).items()
                  if not k.startswith("__") and (k.startswith(("focus_", "Focus", "_")) or k == "FOCUS_DIR")})
