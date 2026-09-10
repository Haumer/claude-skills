// focus.js — visual attention overlay for browser-harness sessions.
//
// Injected into the page by focus.py. Exposes window.__focus with:
//   look(target, label)        spotlight + glide cursor to target
//   read(target, label, ms)    spotlight + scan line sweeping the region
//   act(target, label)         look + click ripple
//   typing(target, label)      look + caret pulse
//   say(text, mood)            narration bar at the bottom ("info" | "warn" | "ok")
//   clear()                    fade everything out
//   rect(target)               viewport rect of the resolved target
//
// A target is a CSS selector string, an Element, or {x, y, w, h} in viewport px.
// Every method returns a Promise that resolves when the animation has settled,
// so the driver can `await` it (browser-harness js() awaits promises).
//
// The overlay lives on <html>, not <body>, so SPA re-renders don't kill it.
// Navigations do — focus.py re-injects on every call.
(() => {
  if (window.__focus && window.__focus.__v === 3) return;

  const Z = 2147483647;
  const ACCENT = "#6366f1";
  const CSS = `
#__fx-layer{position:fixed;inset:0;pointer-events:none;z-index:${Z};font:500 13px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif;opacity:1;transition:opacity .35s ease}
#__fx-layer.__fx-hidden{opacity:0}
#__fx-spot{position:absolute;left:0;top:0;width:0;height:0;border-radius:10px;
  box-shadow:0 0 0 2px #fff,0 0 0 4px ${ACCENT},0 0 0 200vmax rgba(15,23,42,.42);
  transition:left .55s cubic-bezier(.2,.8,.2,1),top .55s cubic-bezier(.2,.8,.2,1),width .55s cubic-bezier(.2,.8,.2,1),height .55s cubic-bezier(.2,.8,.2,1),opacity .3s;opacity:0}
#__fx-spot.__fx-on{opacity:1}
#__fx-pulse{position:absolute;border-radius:12px;border:2px solid ${ACCENT};opacity:0;pointer-events:none}
#__fx-pulse.__fx-go{animation:__fx-pulse .7s ease-out 1}
@keyframes __fx-pulse{0%{opacity:.9;transform:scale(1)}100%{opacity:0;transform:scale(1.12)}}
#__fx-scan{position:absolute;left:0;height:3px;border-radius:2px;opacity:0;
  background:linear-gradient(90deg,transparent,${ACCENT} 20%,${ACCENT} 80%,transparent);
  box-shadow:0 0 12px 2px rgba(99,102,241,.55)}
#__fx-cursor{position:absolute;left:0;top:0;width:26px;height:30px;transform:translate(-40px,-40px);
  transition:transform .6s cubic-bezier(.3,.9,.3,1.05);filter:drop-shadow(0 3px 6px rgba(0,0,0,.45));opacity:0}
#__fx-cursor.__fx-on{opacity:1}
#__fx-cursor.__fx-idle svg{animation:__fx-breathe 2.4s ease-in-out infinite}
@keyframes __fx-breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
#__fx-cursor.__fx-press svg{animation:__fx-press .28s ease-out 1}
@keyframes __fx-press{0%{transform:scale(1)}40%{transform:scale(.82)}100%{transform:scale(1)}}
#__fx-ripple{position:absolute;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:2px solid #fff;
  box-shadow:0 0 0 2px ${ACCENT};opacity:0;transform:scale(.3)}
#__fx-ripple.__fx-go{animation:__fx-ripple .6s ease-out 1}
@keyframes __fx-ripple{0%{opacity:.95;transform:scale(.3)}100%{opacity:0;transform:scale(1.6)}}
#__fx-chip{position:absolute;left:0;top:0;transform:translate(-8px,-140%);white-space:nowrap;max-width:60vw;overflow:hidden;text-overflow:ellipsis;
  background:#0f172a;color:#fff;padding:6px 10px 6px 8px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.35);
  transition:left .55s cubic-bezier(.2,.8,.2,1),top .55s cubic-bezier(.2,.8,.2,1),opacity .25s;opacity:0}
#__fx-chip.__fx-on{opacity:1}
#__fx-chip .__fx-kind{display:inline-block;font-size:10px;letter-spacing:.08em;font-weight:700;color:#c7d2fe;margin-right:8px;vertical-align:1px}
#__fx-chip .__fx-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:${ACCENT};margin:0 7px 1px 2px;box-shadow:0 0 0 3px rgba(99,102,241,.3)}
#__fx-chip.__fx-caret::after{content:"";display:inline-block;width:2px;height:12px;background:#fff;margin-left:6px;vertical-align:-2px;animation:__fx-caret 1s steps(2,start) infinite}
@keyframes __fx-caret{to{visibility:hidden}}
#__fx-say{position:fixed;bottom:18px;left:50%;transform:translateX(-50%) translateY(20px);max-width:760px;width:94vw;
  background:#0f172a;color:#fff;padding:13px 20px;border-radius:14px;font:600 15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif;
  box-shadow:0 10px 40px rgba(0,0,0,.45);text-align:center;opacity:0;transition:opacity .3s,transform .3s,background .3s}
#__fx-say.__fx-on{opacity:1;transform:translateX(-50%) translateY(0)}
#__fx-say.__fx-warn{background:#7c2d12}
#__fx-say.__fx-ok{background:#14532d}
`;

  const CURSOR_SVG = `<svg viewBox="0 0 26 30" width="26" height="30" xmlns="http://www.w3.org/2000/svg" style="transform-origin:4px 3px">
<path d="M4 2 L4 24 L9.6 18.6 L13.6 27.4 L17.6 25.6 L13.6 17 L21 17 Z" fill="#fff" stroke="#0f172a" stroke-width="1.6" stroke-linejoin="round"/></svg>`;

  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function ensure() {
    let layer = $("__fx-layer");
    if (layer && layer.isConnected) return layer;
    const style = document.createElement("style");
    style.id = "__fx-style";
    style.textContent = CSS;
    document.documentElement.appendChild(style);
    layer = document.createElement("div");
    layer.id = "__fx-layer";
    layer.innerHTML = `<div id="__fx-spot"></div><div id="__fx-pulse"></div><div id="__fx-scan"></div>
<div id="__fx-chip"><span class="__fx-dot"></span><span class="__fx-kind"></span><span class="__fx-text"></span></div>
<div id="__fx-ripple"></div><div id="__fx-cursor">${CURSOR_SVG}</div><div id="__fx-say"></div>`;
    document.documentElement.appendChild(layer);
    return layer;
  }

  function resolve(target) {
    if (!target) return null;
    if (typeof target === "string") return document.querySelector(target);
    if (target instanceof Element) return target;
    return target; // {x,y,w,h}
  }

  function rectOf(t, pad = 6) {
    if (!t) return null;
    if (t instanceof Element) {
      const r = t.getBoundingClientRect();
      return { x: r.left - pad, y: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 };
    }
    const w = t.w || 24, h = t.h || 24;
    return { x: t.x - (t.w ? 0 : w / 2) - pad, y: t.y - (t.h ? 0 : h / 2) - pad, w: w + pad * 2, h: h + pad * 2 };
  }

  async function bringIntoView(el) {
    if (!(el instanceof Element)) return;
    const r = el.getBoundingClientRect();
    const inView = r.top >= 60 && r.bottom <= innerHeight - 60;
    if (inView) return;
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    // wait for the smooth scroll to settle (rect stops moving)
    let last = null;
    for (let i = 0; i < 40; i++) {
      await sleep(40);
      const n = el.getBoundingClientRect().top;
      if (last !== null && Math.abs(n - last) < 0.5) break;
      last = n;
    }
  }

  function place(r, kind, label) {
    const layer = ensure();
    layer.classList.remove("__fx-hidden");
    const spot = $("__fx-spot"), chip = $("__fx-chip"), cur = $("__fx-cursor");
    Object.assign(spot.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
    spot.classList.add("__fx-on");
    // cursor lands on the lower-right third of the target, like a hand would
    const cx = r.x + Math.min(r.w * 0.62, r.w - 8), cy = r.y + Math.min(r.h * 0.6, r.h - 6);
    cur.style.transform = `translate(${cx}px,${cy}px)`;
    cur.classList.add("__fx-on");
    cur.classList.remove("__fx-idle");
    chip.querySelector(".__fx-kind").textContent = kind;
    chip.querySelector(".__fx-text").textContent = label || "";
    const above = r.y > 48;
    chip.style.transform = above ? "translate(-8px,-140%)" : `translate(-8px,${r.h + 10}px)`;
    Object.assign(chip.style, { left: r.x + 8 + "px", top: r.y + "px" });
    chip.classList.toggle("__fx-on", !!(label || kind));
    return { cx, cy };
  }

  async function look(target, label, kind = "LOOKING") {
    const t = resolve(target);
    if (!t) return null;
    await bringIntoView(t);
    const r = rectOf(t);
    const p = place(r, kind, label);
    await sleep(620);
    $("__fx-cursor").classList.add("__fx-idle");
    return { ...r, ...p };
  }

  async function read(target, label, ms = 1600) {
    const t = resolve(target);
    if (!t) return null;
    await bringIntoView(t);
    const r = rectOf(t);
    place(r, "READING", label);
    // park the cursor at the top-left corner, out of the way of the text
    $("__fx-cursor").style.transform = `translate(${r.x - 14}px,${r.y - 10}px)`;
    await sleep(500);
    const scan = $("__fx-scan");
    Object.assign(scan.style, { left: r.x + 4 + "px", width: r.w - 8 + "px", top: r.y + "px", opacity: "1", transition: "none" });
    await sleep(20);
    scan.style.transition = `top ${ms}ms linear`;
    scan.style.top = r.y + r.h - 3 + "px";
    await sleep(ms);
    scan.style.opacity = "0";
    return r;
  }

  async function act(target, label) {
    const r = await look(target, label, "CLICKING");
    if (!r) return null;
    const cur = $("__fx-cursor"), rip = $("__fx-ripple"), pulse = $("__fx-pulse");
    Object.assign(rip.style, { left: r.cx + 4 + "px", top: r.cy + 2 + "px" });
    Object.assign(pulse.style, { left: r.x - 2 + "px", top: r.y - 2 + "px", width: r.w + "px", height: r.h + "px" });
    cur.classList.remove("__fx-idle");
    cur.classList.add("__fx-press"); rip.classList.add("__fx-go"); pulse.classList.add("__fx-go");
    await sleep(320);
    cur.classList.remove("__fx-press"); rip.classList.remove("__fx-go"); pulse.classList.remove("__fx-go");
    return r;
  }

  async function typing(target, label) {
    const r = await look(target, label, "TYPING");
    if (r) $("__fx-chip").classList.add("__fx-caret");
    return r;
  }

  function doneTyping() { const c = $("__fx-chip"); if (c) c.classList.remove("__fx-caret"); }

  function say(text, mood = "info") {
    ensure();
    const s = $("__fx-say");
    s.textContent = text || "";
    s.classList.toggle("__fx-warn", mood === "warn");
    s.classList.toggle("__fx-ok", mood === "ok");
    s.classList.toggle("__fx-on", !!text);
    return true;
  }

  async function clear(ms = 350) {
    const layer = $("__fx-layer");
    if (!layer) return true;
    layer.classList.add("__fx-hidden");
    await sleep(ms);
    layer.remove();
    const st = $("__fx-style"); if (st) st.remove();
    return true;
  }

  function rect(target) {
    const t = resolve(target);
    return t ? rectOf(t, 0) : null;
  }

  window.__focus = { __v: 3, ensure, look, read, act, typing, doneTyping, say, clear, rect };
})();
