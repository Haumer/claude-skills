// focus.js — visual attention overlay + viewer channel for browser-harness sessions.
//
// Injected into the page by focus.py. Exposes window.__focus with:
//   look(target, label)          spotlight + glide cursor to target
//   read(target, label, ms)      spotlight + scan line sweeping the region
//   act(target, label)           look + click ripple
//   typing(target, label)        look + caret pulse
//   survey(items, ms)            visit each candidate in turn ("CANDIDATE 2/4 …"); in
//                                manual mode also offers them as a choice in the chat
//   say(text, mood)              narration bar + agent bubble in the chat ("info"|"warn"|"ok")
//   ack(text)                    reply to the viewer's annotations and clear their boxes
//   clear()                      fade everything out
//   rect(target)                 viewport rect of the resolved target
//   pending(kind, label)         announce the next action (manual mode waits for Approve/Skip)
//   poll()                       driver gate: consumes step/approve/choice, drains messages+annotations
//   peek()                       non-consuming check: {stopped, paused, messages, annotations}
//   peekAt(target, label, ms)    dashed ring on a link being read ahead (no click)
//   fetchText(urls, chars)       fetch pages from the page's origin, return title/text/headings
//   settled(quiet, timeout)      resolves when the page DOM has been quiet for `quiet` ms
//   exit(text) / resume()        Esc hides the overlay and stops; resume() brings it back
//   setState(patch)              restore driver-side settings after a navigation
//   addBox(rect, note)           programmatic annotation (what the P-mode drawing does)
//
// The overlay never freezes: the cursor drifts around its target while idle,
// the ring breathes, and after ~2 s without a call the chip turns into a
// THINKING indicator until the next action arrives.
//
// Viewer channel: a chat bubble bottom-right. Open it for the transcript,
// Pause / Step / Stop / speed / "Ask me" (approve or skip every action), and a
// message box. Press P anywhere outside a text field to pause and enter
// annotation mode: drag boxes over the page, type a note per box, press P
// again to send them to the agent and resume. Esc cancels a box; Esc twice stops the agent.
//
// A target is a CSS selector string, an Element, or {x, y, w, h} in viewport px.
// Animation methods return Promises (browser-harness js() awaits them).
// The overlay lives on <html>, not <body>, so SPA re-renders don't kill it.
// Navigations do — focus.py re-injects on every call.
(() => {
  const V = 6;
  if (window.__focus && window.__focus.__v === V) return;
  const prev = window.__focus;

  const Z = 2147483647;
  const ACCENT = "#6366f1";   // agent
  const HUMAN = "#f59e0b";    // viewer's marks
  const FONT = `-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif`;
  const STYLE = `
#__fx-layer{position:fixed;inset:0;pointer-events:none;z-index:${Z};font:500 13px/1.35 ${FONT};opacity:1;transition:opacity .35s ease}
#__fx-layer *{box-sizing:border-box}
#__fx-layer.__fx-hidden{opacity:0}
#__fx-spot{position:absolute;left:0;top:0;width:0;height:0;border-radius:10px;
  box-shadow:0 0 0 2px #fff,0 0 0 4px ${ACCENT},0 0 0 200vmax rgba(15,23,42,.42);
  transition:left .45s cubic-bezier(.2,.8,.2,1),top .45s cubic-bezier(.2,.8,.2,1),width .45s cubic-bezier(.2,.8,.2,1),height .45s cubic-bezier(.2,.8,.2,1),opacity .3s;opacity:0}
#__fx-spot.__fx-on{opacity:1}
#__fx-spot.__fx-soft{box-shadow:0 0 0 2px #fff,0 0 0 4px ${ACCENT},0 0 0 200vmax rgba(15,23,42,.18)}
#__fx-ring{position:absolute;border-radius:14px;border:2px solid ${ACCENT};opacity:0;
  transition:left .45s cubic-bezier(.2,.8,.2,1),top .45s cubic-bezier(.2,.8,.2,1),width .45s cubic-bezier(.2,.8,.2,1),height .45s cubic-bezier(.2,.8,.2,1)}
#__fx-ring.__fx-on{animation:__fx-ring 2.8s ease-in-out infinite}
#__fx-ring.__fx-peek{border-style:dashed;opacity:.9}
@keyframes __fx-ring{0%,100%{opacity:0;transform:scale(1)}40%{opacity:.55;transform:scale(1.035)}}
#__fx-pulse{position:absolute;border-radius:12px;border:2px solid ${ACCENT};opacity:0}
#__fx-pulse.__fx-go{animation:__fx-pulse .7s ease-out 1}
@keyframes __fx-pulse{0%{opacity:.9;transform:scale(1)}100%{opacity:0;transform:scale(1.12)}}
#__fx-scan{position:absolute;left:0;height:3px;border-radius:2px;opacity:0;
  background:linear-gradient(90deg,transparent,${ACCENT} 20%,${ACCENT} 80%,transparent);box-shadow:0 0 12px 2px rgba(99,102,241,.55)}
#__fx-cursor{position:absolute;left:0;top:0;width:26px;height:30px;transform:translate(-40px,-40px);
  transition:transform .5s cubic-bezier(.3,.9,.3,1.04);filter:drop-shadow(0 3px 6px rgba(0,0,0,.45));opacity:0}
#__fx-cursor.__fx-on{opacity:1}
#__fx-cursor .__fx-drift{will-change:transform}
#__fx-cursor.__fx-idle svg{animation:__fx-breathe 2.4s ease-in-out infinite}
@keyframes __fx-breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
#__fx-cursor.__fx-press svg{animation:__fx-press .28s ease-out 1}
@keyframes __fx-press{0%{transform:scale(1)}40%{transform:scale(.82)}100%{transform:scale(1)}}
#__fx-ripple{position:absolute;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 2px ${ACCENT};opacity:0;transform:scale(.3)}
#__fx-ripple.__fx-go{animation:__fx-ripple .6s ease-out 1}
@keyframes __fx-ripple{0%{opacity:.95;transform:scale(.3)}100%{opacity:0;transform:scale(1.6)}}
#__fx-chip{position:absolute;left:0;top:0;transform:translate(-8px,-140%);white-space:nowrap;max-width:60vw;overflow:hidden;text-overflow:ellipsis;
  background:#0f172a;color:#fff;padding:6px 10px 6px 8px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.35);
  transition:left .45s cubic-bezier(.2,.8,.2,1),top .45s cubic-bezier(.2,.8,.2,1),opacity .25s;opacity:0}
#__fx-chip.__fx-on{opacity:1}
#__fx-chip .__fx-kind{display:inline-block;font-size:10px;letter-spacing:.08em;font-weight:700;color:#c7d2fe;margin-right:8px;vertical-align:1px}
#__fx-chip .__fx-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:${ACCENT};margin:0 7px 1px 2px;box-shadow:0 0 0 3px rgba(99,102,241,.3);animation:__fx-dot 1.6s ease-in-out infinite}
@keyframes __fx-dot{0%,100%{box-shadow:0 0 0 3px rgba(99,102,241,.3)}50%{box-shadow:0 0 0 6px rgba(99,102,241,.12)}}
#__fx-chip.__fx-caret::after{content:"";display:inline-block;width:2px;height:12px;background:#fff;margin-left:6px;vertical-align:-2px;animation:__fx-caret 1s steps(2,start) infinite}
@keyframes __fx-caret{to{visibility:hidden}}
#__fx-chip.__fx-think .__fx-text::after{content:"";animation:__fx-dots 1.2s steps(4,end) infinite}
@keyframes __fx-dots{0%{content:""}25%{content:"."}50%{content:".."}75%{content:"..."}}
#__fx-say{position:fixed;bottom:18px;left:50%;transform:translateX(-50%) translateY(20px);max-width:min(720px,calc(100vw - 140px));width:94vw;
  background:#0f172a;color:#fff;padding:13px 20px;border-radius:14px;font:600 15px/1.45 ${FONT};
  box-shadow:0 10px 40px rgba(0,0,0,.45);text-align:center;opacity:0;transition:opacity .3s,transform .3s,background .3s}
#__fx-say.__fx-on{opacity:1;transform:translateX(-50%) translateY(0)}
#__fx-say.__fx-warn{background:#7c2d12}
#__fx-say.__fx-ok{background:#14532d}
/* ---- chat bubble + panel ---- */
#__fx-bubble{position:fixed;right:18px;bottom:18px;width:44px;height:44px;border-radius:50%;pointer-events:auto;cursor:pointer;
  background:#0f172a;box-shadow:0 8px 28px rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;transition:transform .15s}
#__fx-bubble:hover{transform:scale(1.06)}
#__fx-bubble svg{width:20px;height:20px}
#__fx-led{position:absolute;right:-1px;top:-1px;width:12px;height:12px;border-radius:50%;background:#22c55e;border:2px solid #0f172a}
#__fx-led.__fx-paused{background:${HUMAN}}
#__fx-led.__fx-stopped{background:#ef4444}
#__fx-badge{position:absolute;left:-4px;top:-4px;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#ef4444;color:#fff;font:700 11px/18px ${FONT};text-align:center;display:none}
#__fx-badge.__fx-on{display:block}
#__fx-panel{position:fixed;right:18px;bottom:72px;width:300px;max-height:min(520px,70vh);pointer-events:auto;display:flex;flex-direction:column;
  background:#0f172a;color:#fff;border-radius:14px;box-shadow:0 14px 48px rgba(0,0,0,.5);overflow:hidden;
  transform-origin:100% 100%;transform:scale(.92) translateY(8px);opacity:0;visibility:hidden;transition:transform .2s,opacity .2s,visibility .2s}
#__fx-panel.__fx-open{transform:none;opacity:1;visibility:visible}
#__fx-panel .__fx-head{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid #1e293b;font-size:12px;color:#cbd5e1}
#__fx-panel .__fx-head .__fx-hled{width:8px;height:8px;border-radius:50%;background:#22c55e;flex:none}
#__fx-panel .__fx-head .__fx-hled.__fx-paused{background:${HUMAN}}
#__fx-panel .__fx-head .__fx-hled.__fx-stopped{background:#ef4444}
#__fx-panel .__fx-head .__fx-stext{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#__fx-panel .__fx-head button{font-size:14px;padding:2px 6px}
#__fx-panel .__fx-ctl{display:flex;gap:4px;padding:8px 10px;border-bottom:1px solid #1e293b;flex-wrap:wrap}
#__fx-panel button{all:unset;cursor:pointer;background:#1e293b;border:1px solid #334155;color:#fff;border-radius:7px;padding:4px 8px;font:600 11px/1.2 ${FONT}}
#__fx-panel button:hover{background:#334155}
#__fx-panel button.__fx-primary{background:#4f46e5;border-color:#6366f1}
#__fx-panel button.__fx-primary:hover{background:#6366f1}
#__fx-panel button.__fx-active{background:#312e81;border-color:#6366f1;color:#c7d2fe}
#__fx-panel .__fx-log{flex:1;overflow:auto;padding:10px;display:flex;flex-direction:column;gap:6px;min-height:120px;scrollbar-width:thin}
#__fx-panel .__fx-m{max-width:88%;padding:7px 10px;border-radius:12px;font-size:12.5px;line-height:1.4;white-space:pre-wrap;word-break:break-word}
#__fx-panel .__fx-m.__fx-agent{align-self:flex-start;background:#1e293b;border-bottom-left-radius:4px}
#__fx-panel .__fx-m.__fx-agent.__fx-warn{background:#7c2d12}
#__fx-panel .__fx-m.__fx-agent.__fx-ok{background:#14532d}
#__fx-panel .__fx-m.__fx-user{align-self:flex-end;background:#4f46e5;border-bottom-right-radius:4px}
#__fx-panel .__fx-m.__fx-sys{align-self:center;background:none;color:#64748b;font-size:11px;padding:2px}
#__fx-panel .__fx-card{align-self:stretch;background:#1e1b4b;border:1px solid #4338ca;border-radius:10px;padding:8px 10px;font-size:12px;color:#e0e7ff}
#__fx-panel .__fx-card b{display:block;font-size:10px;letter-spacing:.08em;color:#c7d2fe;margin-bottom:4px}
#__fx-panel .__fx-card .__fx-opts{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
#__fx-panel .__fx-card.__fx-done{opacity:.55}
#__fx-panel .__fx-in{display:flex;gap:6px;padding:8px 10px;border-top:1px solid #1e293b}
#__fx-panel input{all:unset;flex:1;min-width:0;background:#1e293b;border:1px solid #334155;color:#fff;border-radius:8px;padding:6px 9px;font:500 12px/1.2 ${FONT}}
#__fx-panel input::placeholder{color:#64748b}
#__fx-panel .__fx-foot{padding:5px 12px 8px;color:#64748b;font-size:10.5px}
/* ---- annotation mode ---- */
#__fx-draw{position:fixed;inset:0;pointer-events:auto;cursor:crosshair;display:none}
#__fx-draw.__fx-on{display:block}
#__fx-hint{position:fixed;top:14px;left:50%;transform:translateX(-50%);background:${HUMAN};color:#1c1917;padding:8px 14px;border-radius:10px;font:600 13px/1.3 ${FONT};
  box-shadow:0 8px 24px rgba(0,0,0,.35);display:none;white-space:nowrap}
#__fx-hint.__fx-on{display:block}
.__fx-box{position:fixed;border:2px solid ${HUMAN};background:rgba(245,158,11,.12);border-radius:4px;pointer-events:none}
.__fx-box .__fx-num{position:absolute;left:-2px;top:-22px;background:${HUMAN};color:#1c1917;font:700 11px/18px ${FONT};padding:0 6px;border-radius:5px 5px 0 0}
.__fx-box .__fx-note{position:absolute;left:-2px;bottom:-30px;pointer-events:auto;width:240px;background:#1c1917;color:#fff;border:1px solid ${HUMAN};border-radius:7px;padding:5px 8px;font:500 12px/1.2 ${FONT};outline:none}
.__fx-box .__fx-lbl{position:absolute;left:-2px;bottom:-24px;background:#1c1917;color:#fde68a;font:500 11px/1.2 ${FONT};padding:3px 7px;border-radius:6px;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.__fx-box.__fx-sent{border-style:dashed}
`;

  const CURSOR_SVG = `<span class="__fx-drift"><svg viewBox="0 0 26 30" width="26" height="30" xmlns="http://www.w3.org/2000/svg" style="transform-origin:4px 3px;display:block"><path d="M4 2 L4 24 L9.6 18.6 L13.6 27.4 L17.6 25.6 L13.6 17 L21 17 Z" fill="#fff" stroke="#0f172a" stroke-width="1.6" stroke-linejoin="round"/></svg></span>`;
  const CHAT_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.2-4.2A8 8 0 1 1 21 12z"/></svg>`;

  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const state = prev && prev.state ? prev.state : {
    paused: false, step: false, stopped: false, mode: "auto", speed: 1,
    approve: null, choice: null, pending: null,
    messages: [], annotations: [], chat: [], unread: 0, open: false,
    annotating: false, boxes: [], boxSeq: 0,
  };
  const SPEEDS = [1, 2, 0.5];

  // ---------------------------------------------------------------- overlay
  function ensure() {
    let layer = $("__fx-layer");
    if (layer && layer.isConnected) return layer;
    if (state.stopped && state.exited) return null;   // Esc: the overlay stays gone until resume()
    const style = document.createElement("style");
    style.id = "__fx-style"; style.textContent = STYLE;
    document.documentElement.appendChild(style);
    layer = document.createElement("div");
    layer.id = "__fx-layer";
    layer.innerHTML = `<div id="__fx-spot"></div><div id="__fx-ring"></div><div id="__fx-pulse"></div><div id="__fx-scan"></div>
<div id="__fx-chip"><span class="__fx-dot"></span><span class="__fx-kind"></span><span class="__fx-text"></span></div>
<div id="__fx-ripple"></div><div id="__fx-cursor">${CURSOR_SVG}</div><div id="__fx-say"></div>
<div id="__fx-draw"></div><div id="__fx-hint">Point me at things: drag boxes, type a note, Enter. Press P again to send and resume · Esc cancels a box, Esc again leaves the mode</div>
<div id="__fx-panel">
  <div class="__fx-head"><span class="__fx-hled"></span><span class="__fx-stext">agent running</span><button data-a="close" title="close">×</button></div>
  <div class="__fx-ctl"><button data-a="pause">Pause</button><button data-a="step">Step</button><button data-a="stop">Stop</button><button data-a="speed">1×</button><button data-a="ask">Ask me</button></div>
  <div class="__fx-log"></div>
  <div class="__fx-in"><input class="__fx-msg" placeholder="Message the agent…"><button class="__fx-primary" data-a="send">Send</button></div>
  <div class="__fx-foot">P = pause and draw boxes · P again = send and resume · Esc = stop and hide</div>
</div>
<div id="__fx-bubble">${CHAT_SVG}<span id="__fx-led"></span><span id="__fx-badge"></span></div>`;
    document.documentElement.appendChild(layer);
    wire(layer);
    render();
    startLife();
    return layer;
  }

  // ---- continuous motion: idle drift, breathing ring, THINKING after silence
  const life = { anchor: null, kind: "", label: "", last: Date.now(), thinking: false, raf: 0 };
  function touch(kind, label) { life.last = Date.now(); if (kind !== undefined) { life.kind = kind; life.label = label || ""; } if (life.thinking) unthink(); }
  function unthink() {
    life.thinking = false;
    const chip = $("__fx-chip"); if (!chip) return;
    chip.classList.remove("__fx-think");
    chip.querySelector(".__fx-kind").textContent = life.kind;
    chip.querySelector(".__fx-text").textContent = life.label;
  }
  function think() {
    life.thinking = true;
    const chip = $("__fx-chip"); if (!chip || !life.anchor) return;
    chip.classList.add("__fx-think", "__fx-on");
    chip.querySelector(".__fx-kind").textContent = "THINKING";
    chip.querySelector(".__fx-text").textContent = "deciding the next step";
  }
  function startLife() {
    if (life.raf) return;
    const tick = () => {
      life.raf = requestAnimationFrame(tick);
      const cur = $("__fx-cursor"); if (!cur) { life.raf = 0; return; }
      const t = performance.now();
      const idle = cur.classList.contains("__fx-idle");
      const amp = life.thinking ? 16 : idle ? 7 : 0;
      const dx = amp * (Math.sin(t / 1100) * 0.7 + Math.sin(t / 2300) * 0.3);
      const dy = amp * (Math.cos(t / 1400) * 0.6 + Math.sin(t / 3100) * 0.4);
      const drift = cur.querySelector(".__fx-drift");
      if (drift) drift.style.transform = `translate(${dx.toFixed(1)}px,${dy.toFixed(1)}px)`;
      const silent = Date.now() - life.last;
      if (!life.thinking && silent > 2200 && life.anchor && !state.paused && !state.annotating) think();
    };
    life.raf = requestAnimationFrame(tick);
  }

  function resolve(t) {
    if (!t) return null;
    if (typeof t === "string") return document.querySelector(t);
    return t;
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
    if (r.top >= 60 && r.bottom <= innerHeight - 60) return;
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    let last = null;
    for (let i = 0; i < 40; i++) {
      await sleep(40);
      const n = el.getBoundingClientRect().top;
      if (last !== null && Math.abs(n - last) < 0.5) break;
      last = n;
    }
  }
  function place(r, kind, label, soft = false) {
    ensure();
    touch(kind, label);
    $("__fx-layer").classList.remove("__fx-hidden");
    const spot = $("__fx-spot"), ring = $("__fx-ring"), chip = $("__fx-chip"), cur = $("__fx-cursor");
    Object.assign(spot.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
    Object.assign(ring.style, { left: r.x - 5 + "px", top: r.y - 5 + "px", width: r.w + 10 + "px", height: r.h + 10 + "px" });
    spot.classList.add("__fx-on"); spot.classList.toggle("__fx-soft", soft); ring.classList.add("__fx-on");
    const cx = r.x + Math.min(r.w * 0.62, r.w - 8), cy = r.y + Math.min(r.h * 0.6, r.h - 6);
    life.anchor = { x: cx, y: cy };
    cur.style.transform = `translate(${cx}px,${cy}px)`;
    cur.classList.add("__fx-on"); cur.classList.remove("__fx-idle");
    chip.classList.remove("__fx-think");
    chip.querySelector(".__fx-kind").textContent = kind;
    chip.querySelector(".__fx-text").textContent = label || "";
    chip.style.transform = r.y > 48 ? "translate(-8px,-140%)" : `translate(-8px,${r.h + 10}px)`;
    Object.assign(chip.style, { left: r.x + 8 + "px", top: r.y + "px" });
    chip.classList.toggle("__fx-on", !!(label || kind));
    return { cx, cy };
  }

  async function look(target, label, kind = "LOOKING") {
    const t = resolve(target); if (!t) return null;
    await bringIntoView(t);
    const r = rectOf(t), p = place(r, kind, label);
    await sleep(480);
    $("__fx-cursor").classList.add("__fx-idle");
    touch();
    return { ...r, ...p };
  }
  async function read(target, label, ms = 1200) {
    const t = resolve(target); if (!t) return null;
    await bringIntoView(t);
    const r = rectOf(t);
    place(r, "READING", label);
    $("__fx-cursor").style.transform = `translate(${r.x - 14}px,${r.y - 10}px)`;
    life.anchor = { x: r.x - 14, y: r.y - 10 };
    await sleep(300);
    const scan = $("__fx-scan");
    Object.assign(scan.style, { left: r.x + 4 + "px", width: r.w - 8 + "px", top: r.y + "px", opacity: "1", transition: "none" });
    await sleep(20);
    scan.style.transition = `top ${ms}ms linear`; scan.style.top = r.y + r.h - 3 + "px";
    await sleep(ms);
    scan.style.opacity = "0";
    $("__fx-cursor").classList.add("__fx-idle");
    touch();
    return r;
  }
  async function act(target, label) {
    const r = await look(target, label, "CLICKING"); if (!r) return null;
    const cur = $("__fx-cursor"), rip = $("__fx-ripple"), pulse = $("__fx-pulse");
    Object.assign(rip.style, { left: r.cx + 4 + "px", top: r.cy + 2 + "px" });
    Object.assign(pulse.style, { left: r.x - 2 + "px", top: r.y - 2 + "px", width: r.w + "px", height: r.h + "px" });
    cur.classList.remove("__fx-idle"); cur.classList.add("__fx-press"); rip.classList.add("__fx-go"); pulse.classList.add("__fx-go");
    await sleep(240);
    cur.classList.remove("__fx-press"); rip.classList.remove("__fx-go"); pulse.classList.remove("__fx-go");
    cur.classList.add("__fx-idle");
    touch();
    return r;
  }
  async function typing(target, label) {
    const r = await look(target, label, "TYPING");
    if (r) $("__fx-chip").classList.add("__fx-caret");
    return r;
  }
  function doneTyping() { const c = $("__fx-chip"); if (c) c.classList.remove("__fx-caret"); touch(); }

  // Visit each candidate so the viewer sees the options being weighed.
  async function survey(items, ms = 1000) {
    ensure();
    const out = [];
    for (let i = 0; i < items.length; i++) {
      const it = items[i], t = resolve(it.target);
      if (!t) { out.push(null); continue; }
      await bringIntoView(t);
      const r = rectOf(t);
      place(r, `CANDIDATE ${i + 1}/${items.length}`, it.label || "", true);
      out.push(r);
      await sleep(ms);
    }
    $("__fx-spot").classList.remove("__fx-soft");
    $("__fx-cursor").classList.add("__fx-idle");
    if (state.mode === "manual" && items.length) {
      state.choice = null;
      push({ type: "choice", options: items.map((it) => it.label || String(it.target)) });
    }
    touch();
    return out;
  }

  // Peek: show which link is being read ahead (dashed ring, soft spotlight), nothing is clicked.
  async function peekAt(target, label, ms = 300) {
    const t = resolve(target); if (!t) return null;
    await bringIntoView(t);
    const r = rectOf(t);
    place(r, "PEEKING", label || "reading ahead", true);
    $("__fx-ring").classList.add("__fx-peek");
    await sleep(ms);
    $("__fx-ring").classList.remove("__fx-peek"); $("__fx-spot").classList.remove("__fx-soft");
    $("__fx-cursor").classList.add("__fx-idle");
    touch();
    return r;
  }
  // Fetch pages in parallel from the page's own origin (cookies included) and reduce them to text.
  function fetchText(urls, chars = 1500) {
    return Promise.all(urls.map(async (u) => {
      try {
        const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 8000);
        const res = await fetch(u, { credentials: "include", signal: ctl.signal, headers: { Accept: "text/html,*/*" } });
        clearTimeout(to);
        const ct = res.headers.get("content-type") || "", body = await res.text();
        if (!/html/i.test(ct)) return { url: u, status: res.status, type: ct, title: "", text: body.slice(0, chars), headings: [], links: 0, forms: 0 };
        const doc = new DOMParser().parseFromString(body, "text/html");
        doc.querySelectorAll("script,style,noscript,svg,template").forEach((e) => e.remove());
        const txt = (doc.body ? doc.body.textContent : "").replace(/\s+/g, " ").trim();
        return { url: u, status: res.status, type: ct, title: (doc.title || "").trim(), text: txt.slice(0, chars),
                 headings: [...doc.querySelectorAll("h1,h2,h3")].map((h) => h.textContent.replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 20),
                 links: doc.querySelectorAll("a[href]").length, forms: doc.querySelectorAll("form").length };
      } catch (e) { return { url: u, error: String(e) }; }
    }));
  }
  // Resolve when the page's DOM (not the overlay) has been quiet for `quiet` ms, or after `timeout` ms.
  function settled(quiet = 300, timeout = 8000) {
    return new Promise((res) => {
      const start = Date.now(); let last = start;
      const ours = (n) => { const el = n.nodeType === 1 ? n : n.parentElement; return !!(el && el.closest && el.closest("#__fx-layer")); };
      const mo = new MutationObserver((recs) => { if (recs.some((r) => !ours(r.target))) last = Date.now(); });
      mo.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
      const iv = setInterval(() => {
        const now = Date.now();
        if (now - last >= quiet || now - start >= timeout) { clearInterval(iv); mo.disconnect(); res({ ms: now - start, quiet: now - last >= quiet }); }
      }, 50);
    });
  }
  function note(text) { push({ who: "sys", text }); return true; }

  function say(text, mood = "info") {
    ensure(); touch();
    const s = $("__fx-say"); if (!s) return false;
    s.textContent = text || "";
    s.classList.toggle("__fx-warn", mood === "warn"); s.classList.toggle("__fx-ok", mood === "ok");
    s.classList.toggle("__fx-on", !!text);
    if (text) push({ who: "agent", text, mood });
    return true;
  }
  function ack(text) {
    document.querySelectorAll(".__fx-box").forEach((b) => b.remove());
    state.boxes = [];
    if (text) say(text, "ok");
    return true;
  }
  async function clear(ms = 350) {
    const layer = $("__fx-layer"); if (!layer) return true;
    layer.classList.add("__fx-hidden"); await sleep(ms); layer.remove();
    const st = $("__fx-style"); if (st) st.remove();
    if (life.raf) { cancelAnimationFrame(life.raf); life.raf = 0; }
    life.anchor = null;
    return true;
  }
  function rect(target) { const t = resolve(target); return t ? rectOf(t, 0) : null; }

  // ---------------------------------------------------------------- chat
  function push(m) {
    m.t = Date.now();
    state.chat.push(m); if (state.chat.length > 80) state.chat.shift();
    if (!state.open && (m.who === "agent" || m.type)) state.unread++;
    render();
  }
  function statusText() {
    if (state.stopped) return "stopped — exits at the next action";
    if (state.annotating) return "annotation mode — press P to send";
    if (state.mode === "manual" && state.pending) return "waiting for your approval";
    if (state.paused) return "paused — the page is yours";
    return "agent running";
  }
  function render() {
    const panel = $("__fx-panel"); if (!panel) return;
    const cls = state.stopped ? "__fx-stopped" : state.paused ? "__fx-paused" : "";
    $("__fx-led").className = cls; panel.querySelector(".__fx-hled").className = "__fx-hled " + cls;
    panel.querySelector(".__fx-stext").textContent = statusText();
    panel.classList.toggle("__fx-open", state.open);
    const badge = $("__fx-badge"); badge.textContent = state.unread; badge.classList.toggle("__fx-on", state.unread > 0 && !state.open);
    panel.querySelector('[data-a="pause"]').textContent = state.paused ? "Resume" : "Pause";
    panel.querySelector('[data-a="speed"]').textContent = state.speed + "×";
    panel.querySelector('[data-a="ask"]').classList.toggle("__fx-active", state.mode === "manual");
    const log = panel.querySelector(".__fx-log");
    const html = state.chat.map((m, i) => {
      if (m.type === "pending") return `<div class="__fx-card ${m.done ? "__fx-done" : ""}"><b>NEXT · ${esc(m.kind)}</b>${esc(m.label)}${m.done ? "" : `<div class="__fx-opts"><button class="__fx-primary" data-a="approve" data-i="${i}">Approve</button><button data-a="skip" data-i="${i}">Skip</button></div>`}</div>`;
      if (m.type === "choice") return `<div class="__fx-card ${m.done ? "__fx-done" : ""}"><b>WHICH ONE?</b>${m.done ? esc(m.picked) : `<div class="__fx-opts">${m.options.map((o, k) => `<button data-a="choice" data-i="${i}" data-k="${k}">${k + 1}. ${esc(o)}</button>`).join("")}<button data-a="choice" data-i="${i}" data-k="-1">you decide</button></div>`}</div>`;
      if (m.who === "sys") return `<div class="__fx-m __fx-sys">${esc(m.text)}</div>`;
      return `<div class="__fx-m ${m.who === "user" ? "__fx-user" : "__fx-agent"} ${m.mood === "warn" ? "__fx-warn" : m.mood === "ok" ? "__fx-ok" : ""}">${esc(m.text)}</div>`;
    }).join("");
    if (log.dataset.html !== html) { log.innerHTML = html; log.dataset.html = html; log.scrollTop = log.scrollHeight; }
  }

  function wire(layer) {
    const panel = layer.querySelector("#__fx-panel"), bubble = layer.querySelector("#__fx-bubble");
    bubble.addEventListener("click", (e) => { e.stopPropagation(); state.open = !state.open; if (state.open) state.unread = 0; render(); if (state.open) panel.querySelector(".__fx-msg").focus(); });
    const input = panel.querySelector(".__fx-msg");
    const sendMsg = () => { const v = input.value.trim(); if (!v) return; state.messages.push(v); input.value = ""; push({ who: "user", text: v }); push({ who: "sys", text: "delivered at the agent's next action" }); };
    panel.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      e.stopPropagation();
      const a = b.dataset.a, i = +b.dataset.i;
      if (a === "close") state.open = false;
      else if (a === "pause") state.paused = !state.paused;
      else if (a === "step") { state.paused = true; state.step = true; }
      else if (a === "stop") state.stopped = true;
      else if (a === "speed") state.speed = SPEEDS[(SPEEDS.indexOf(state.speed) + 1) % SPEEDS.length];
      else if (a === "ask") state.mode = state.mode === "manual" ? "auto" : "manual";
      else if (a === "approve" || a === "skip") { state.approve = a === "approve" ? "yes" : "skip"; if (state.chat[i]) state.chat[i].done = true; }
      else if (a === "choice") { const k = +b.dataset.k; state.choice = k; if (state.chat[i]) { state.chat[i].done = true; state.chat[i].picked = k < 0 ? "you decide" : state.chat[i].options[k]; } }
      else if (a === "send") sendMsg();
      render();
    });
    ["keydown", "keyup", "keypress"].forEach((ev) => input.addEventListener(ev, (e) => { e.stopPropagation(); if (ev === "keydown" && e.key === "Enter") sendMsg(); }));
    wireDraw(layer);
    if (!window.__focusKeys) {
      window.__focusKeys = true;
      document.addEventListener("keydown", onKey, true);
    }
  }

  // ---------------------------------------------------------------- annotation mode (P)
  function editable(el) {
    if (!el) return false;
    if (el.closest && el.closest("#__fx-layer")) return !!el.closest("input,textarea");
    return el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
  }
  function exit(text) {
    state.stopped = true; state.exited = true; state.paused = false; state.step = false; state.annotating = false;
    document.querySelectorAll(".__fx-box").forEach((b) => b.remove()); state.boxes = [];
    push({ who: "sys", text: text || "Esc — stopped by the viewer" });
    clear(220);
  }
  function resume() { state.stopped = false; state.exited = false; ensure(); render(); return true; }
  function onKey(e) {
    if (e.key === "Escape") {
      if (state.annotating) {                           // in P mode Esc cancels the draft box, then leaves the mode
        const d = state.boxes.find((b) => !b.done);
        if (d) { d.el.remove(); state.boxes = state.boxes.filter((b) => b !== d); } else toggleAnnotate();
        return;
      }
      if (e.target && e.target.closest && e.target.closest("#__fx-panel")) { state.open = false; render(); return; }
      e.preventDefault(); e.stopPropagation();
      exit("Esc — stopped by the viewer; overlay hidden, the page is yours");
      return;
    }
    if ((e.key === "p" || e.key === "P") && !e.metaKey && !e.ctrlKey && !e.altKey && !editable(e.target)) {
      e.preventDefault(); e.stopPropagation();
      toggleAnnotate();
    }
  }
  function toggleAnnotate() {
    ensure();
    state.annotating = !state.annotating;
    $("__fx-draw").classList.toggle("__fx-on", state.annotating);
    $("__fx-hint").classList.toggle("__fx-on", state.annotating);
    if (state.annotating) { state.paused = true; unthink(); push({ who: "sys", text: "paused — draw boxes, P sends them" }); }
    else flushBoxes();
    render();
  }
  let drag = null;
  function wireDraw(layer) {
    const d = layer.querySelector("#__fx-draw");
    d.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      drag = { x0: e.clientX, y0: e.clientY, el: mkBox({ x: e.clientX, y: e.clientY, w: 0, h: 0 }) };
    });
    d.addEventListener("mousemove", (e) => {
      if (!drag) return;
      const r = norm(drag.x0, drag.y0, e.clientX, e.clientY);
      Object.assign(drag.el.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
    });
    d.addEventListener("mouseup", (e) => {
      if (!drag) return;
      const r = norm(drag.x0, drag.y0, e.clientX, e.clientY);
      const el = drag.el; drag = null;
      if (r.w < 6 || r.h < 6) { el.remove(); return; }
      const box = { rect: r, el, note: "", done: false, n: ++state.boxSeq };
      el.querySelector(".__fx-num").textContent = box.n;
      state.boxes.push(box);
      const inp = document.createElement("input");
      inp.className = "__fx-note"; inp.placeholder = "What should I look at here? (Enter)";
      el.appendChild(inp); inp.focus();
      ["keydown", "keyup", "keypress"].forEach((ev) => inp.addEventListener(ev, (x) => {
        x.stopPropagation();
        if (ev !== "keydown") return;
        if (x.key === "Enter") commitBox(box, inp.value);
        if (x.key === "Escape") { el.remove(); state.boxes = state.boxes.filter((b) => b !== box); }
        if ((x.key === "p" || x.key === "P") && !inp.value) { x.preventDefault(); commitBox(box, ""); toggleAnnotate(); }
      }));
    });
  }
  function norm(x0, y0, x1, y1) { return { x: Math.min(x0, x1), y: Math.min(y0, y1), w: Math.abs(x1 - x0), h: Math.abs(y1 - y0) }; }
  function mkBox(r) {
    const el = document.createElement("div");
    el.className = "__fx-box";
    Object.assign(el.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
    el.innerHTML = `<span class="__fx-num"></span>`;
    $("__fx-layer").appendChild(el);
    return el;
  }
  function commitBox(box, note) {
    if (box.done) return;
    box.note = (note || "").trim(); box.done = true;
    const inp = box.el.querySelector(".__fx-note"); if (inp) inp.remove();
    const lbl = document.createElement("span"); lbl.className = "__fx-lbl"; lbl.textContent = box.note || "(no note)";
    box.el.appendChild(lbl);
  }
  function addBox(r, note) {           // programmatic: same path as drawing
    ensure();
    const el = mkBox(r);
    const box = { rect: { ...r }, el, note: "", done: false, n: ++state.boxSeq };
    el.querySelector(".__fx-num").textContent = box.n;
    state.boxes.push(box); commitBox(box, note);
    return box.n;
  }
  function flushBoxes() {
    const fresh = state.boxes.filter((b) => !b.sent);
    fresh.forEach((b) => { if (!b.done) commitBox(b, (b.el.querySelector(".__fx-note") || {}).value || ""); });
    const payload = fresh.map((b) => ({ n: b.n, note: b.note, ...describe(b.rect) }));
    fresh.forEach((b) => { b.sent = true; b.el.classList.add("__fx-sent"); });
    if (payload.length) {
      state.annotations.push(...payload);
      push({ who: "user", text: payload.map((p) => `#${p.n} ${p.note || "(no note)"}`).join("\n") });
      push({ who: "sys", text: `${payload.length} box${payload.length > 1 ? "es" : ""} sent — the agent reads them now` });
    }
    state.paused = false;
    touch();
  }
  function cssPath(el) {
    if (!(el instanceof Element)) return null;
    if (el.id) return "#" + CSS.escape(el.id);
    const parts = [];
    let cur = el;
    for (let i = 0; cur && cur !== document.documentElement && i < 5; i++) {
      let s = cur.tagName.toLowerCase();
      if (cur.id) { parts.unshift("#" + CSS.escape(cur.id)); break; }
      const sib = cur.parentElement ? [...cur.parentElement.children].filter((c) => c.tagName === cur.tagName) : [];
      if (sib.length > 1) s += `:nth-of-type(${sib.indexOf(cur) + 1})`;
      parts.unshift(s); cur = cur.parentElement;
    }
    return parts.join(" > ");
  }
  function textInRect(r) {
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n, total = 0;
    while ((n = walker.nextNode()) && total < 600) {
      const s = n.nodeValue.trim(); if (!s) continue;
      if (n.parentElement && n.parentElement.closest("#__fx-layer,script,style,noscript")) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      const b = range.getBoundingClientRect();
      if (b.width === 0 && b.height === 0) continue;
      if (b.right < r.x || b.left > r.x + r.w || b.bottom < r.y || b.top > r.y + r.h) continue;
      out.push(s); total += s.length;
    }
    return out.join(" ").slice(0, 600);
  }
  function describe(r) {
    const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
    const els = document.elementsFromPoint(cx, cy).filter((e) => !e.closest("#__fx-layer"));
    const el = els[0] || null;
    return {
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) },
      page: { x: Math.round(r.x + scrollX), y: Math.round(r.y + scrollY) },
      element: el ? {
        tag: el.tagName.toLowerCase(), id: el.id || null, classes: [...el.classList].slice(0, 4),
        selector: cssPath(el), text: (el.innerText || el.value || el.alt || "").trim().replace(/\s+/g, " ").slice(0, 160),
      } : null,
      text: textInRect(r),
    };
  }

  // ---------------------------------------------------------------- driver API
  function pending(kind, label) {
    ensure(); touch();
    if (!$("__fx-layer")) return false;
    state.pending = { kind, label: label || "" }; state.approve = null;
    if (state.mode === "manual") push({ type: "pending", kind, label: label || "" });
    render();
    return true;
  }
  function poll() {
    ensure();
    const out = {
      paused: state.paused, step: state.step, stopped: state.stopped, mode: state.mode, speed: state.speed,
      approve: state.approve, choice: state.choice,
      messages: state.messages.splice(0), annotations: state.annotations.splice(0),
    };
    if (state.step) state.step = false;
    if (state.approve) { state.approve = null; state.pending = null; }
    if (state.choice !== null) state.choice = null;
    render();
    return JSON.stringify(out);
  }
  function peek() {
    return JSON.stringify({ stopped: state.stopped, paused: state.paused, messages: state.messages.length, annotations: state.annotations.length, annotating: state.annotating });
  }
  function setState(patch) { Object.assign(state, patch || {}); render(); return true; }

  window.__focus = { __v: V, state, ensure, look, read, act, typing, doneTyping, survey, say, ack, clear, rect, pending, poll, peek, setState, addBox, toggleAnnotate, peekAt, fetchText, settled, note, exit, resume };
})();
