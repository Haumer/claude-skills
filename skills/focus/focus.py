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
# The harness runs driver scripts through a nested exec(), where names defined
# at the top level land in a locals dict that function bodies cannot see. The
# last line of this file therefore copies everything it defines into globals().

import json as _json
import os as _os
import time as _time

FOCUS_DIR = _os.path.expanduser(_os.environ.get("FOCUS_SKILL_DIR", "~/.claude/skills/focus"))
_FOCUS_JS = open(_os.path.join(FOCUS_DIR, "focus.js")).read()
_SPEED = float(_os.environ.get("FOCUS_SPEED", "1.0"))


def focus_speed(x):
    """1.0 = default pacing, 2.0 = twice as fast, 0 = no pauses."""
    global _SPEED
    _SPEED = float(x)


def _pause(seconds):
    if _SPEED > 0:
        _time.sleep(seconds / _SPEED)


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
    if js("!!(window.__focus && window.__focus.__v === 3)"):
        return True
    js(_FOCUS_JS)
    return bool(js("!!window.__focus"))


def _call(method, target, label, extra=""):
    focus_install()
    return js(f"window.__focus.{method}({_target(target)}, {_q(label)}{extra})")


def focus_say(text, mood="info"):
    """Narration bar at the bottom. mood: info | warn | ok. Empty text hides it."""
    focus_install()
    js(f"window.__focus.say({_q(text)}, {_q(mood)})")
    return text


def focus_look(target, label="", hold=0.8):
    """Spotlight a region and glide the cursor to it. Returns its viewport rect or None."""
    r = _call("look", target, label)
    _pause(hold)
    return r


def focus_read(target, label="", seconds=None):
    """Spotlight a region, sweep a scan line over it, return its innerText.

    Duration scales with text length (about 250 words per 4 s) unless given."""
    focus_install()
    text = js(f"(e=>e?e.innerText:null)(document.querySelector({_q(target)}))") if isinstance(target, str) else None
    if isinstance(target, str) and text is None:
        focus_say(f"Could not find: {label or target}", "warn")
        return None
    if seconds is None:
        words = len((text or "").split())
        seconds = min(6.0, max(1.2, words / 60.0))
    ms = int(seconds * 1000 / _SPEED) if _SPEED > 0 else 200
    _call("read", target, label, f", {ms}")
    return text


def focus_click(target, label="", settle=0.5):
    """Announce, glide, ripple, then really click the element's centre. Returns True if clicked."""
    r = _call("act", target, label)
    if not r:
        focus_say(f"Could not find: {label or target}", "warn")
        return False
    click(r["cx"] + 4, r["cy"] + 2)  # same spot the cursor tip is pointing at
    _pause(settle)
    return True


def focus_click_at(x, y, label="", settle=0.5):
    """Coordinate click with the same choreography (for canvas UIs)."""
    return focus_click((x, y), label, settle)


def focus_type(target, text, label="", per_char=0.035, max_seconds=2.5):
    """Click into the field, then type for real, visibly, one character at a time."""
    if not focus_click(target, label or f"type: {text[:40]}", settle=0.15):
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
    _pause(0.3)
    return True


def focus_press(key, label=""):
    """Press a key (Enter, Tab, Escape…) with a short narration beat."""
    if label:
        focus_say(label)
    press_key(key)
    _pause(0.3)


def focus_goto(url, label=None, timeout=15.0):
    """Navigate in the current tab, re-inject the overlay, keep the narration bar alive."""
    focus_say(label or f"Opening {url}")
    _pause(0.5)
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
    _pause(0.5)
    return page_info()


def focus_scroll(dy=400, label="", steps=4):
    """Scroll in visible steps instead of one jump."""
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


def focus_clear():
    """Fade the overlay out and remove it."""
    if js("!!window.__focus"):
        js("window.__focus.clear()")
    return True


# --- make the wrappers visible to each other under the harness's nested exec() ---
globals().update({k: v for k, v in dict(locals()).items()
                  if not k.startswith("__") and (k.startswith(("focus_", "_")) or k == "FOCUS_DIR")})
