# stitch.withgoogle.com

Google's AI UI design tool. You give it a brief (and optionally a reference), it generates mobile/web screens. Useful as a **direction generator** — output is screenshots of mockups, not production code.

## What's actually there

- **The UI is a canvas.** `document.querySelectorAll(...)` returns nothing for the prompt box, toggles, buttons, generated screens. Don't waste time walking the DOM. Use coordinate clicks for everything except the prompt textarea, which accepts `Input.insertText` once focused, and `Enter` to submit.
- **No shadow DOM either.** Confirmed: walking shadow roots returns 0 nodes.
- **The marketing landing has the prompt box visible**, but submitting it without clicking "Try now" first goes nowhere. You must enter the actual app.

## Login flow

1. `new_tab("https://stitch.withgoogle.com/")`. The user's Chrome must be signed into a Google account; that account becomes the Stitch account automatically.
2. Click **"Try now"** in the top right. URL gains `?pli=1` and you land in the projects dashboard.
3. From the dashboard, the prompt box at the right takes a brief.

## Prompt + submit

- **Click the prompt textarea** (center of the prompt box, roughly viewport `(1043, 462)` at a 1728×941 viewport).
- **`type_text(brief)`** — works fine for long multi-paragraph briefs.
- **App vs Web toggle** — coordinate-click. The toggle row is at the bottom of the prompt box. App is selected by default; click "Web" if you want a web app. (If the toggle click misses, just include "mobile-first web" or "responsive web app" in the brief — the model honors the brief over the toggle.)
- **Submit with `press_key("Enter")`.** No need to find a submit button. URL changes to `/projects/<id>`.

## Generation timing

Multi-step. For a brief asking for 3 directions × 3 screens each:

1. **Design system** — typography, color, components. ~30–45s.
2. **Direction A** — full set of screens. ~60–90s.
3. **Stitch will then ask** in the chat panel: "Should I proceed with Direction B or C?" with two inline buttons.

To skip the per-direction confirmation, include in your brief: *"Generate all three directions back-to-back. Don't wait for me to confirm between them."* Or send a follow-up via the chat input at the bottom (viewport ~ `(864, 870)`): *"Generate the next direction now, then immediately the one after."*

Total time for 3 directions: ~5–8 minutes.

## Output

- The canvas shows mobile/web frame mockups. **Screenshot them.** Each frame is labeled with the direction name and screen name (e.g. "Reveal Moment · Tactile Philately").
- **Export to code:** top-right "Export" button. Output is generic Tailwind HTML — useful as visual reference, not as production code that fits an existing design system.
- **The chat panel on the left** keeps a history of every step Stitch took. Useful for grounding follow-up prompts.

## What works for prompting

- Be opinionated. Stitch produces generic AI slop on weak briefs and surprisingly tasteful work on strong ones.
- Name specific aesthetic references ("Pokémon Go visible rarity", "Duolingo springy feel", "philately / postage stamps").
- Specify rarity/state systems explicitly (gold/silver/bronze, owned vs empty silhouette, etc.) — Stitch handles tier systems well.
- Ask for **multiple distinct directions** in one brief (e.g. "Generate 3 directions: A, B, C with different aesthetics") — you get a much wider exploration than iterating one at a time.
- Specify "no confetti / no cartoon mascot / no arcade" if you want a refined feel — Stitch defaults to playful.

## Attaching a reference image

There **is** a `+` button at the bottom-left of the chat input — its tooltip says *"Attach a screenshot, sketch or visual inspiration"*. Clicking it opens a small floating menu with three options: **Upload Files**, **Website URL**, and **Variations (Nx)**.

- The "+" sits at viewport ~`(595, 896)` next to the chat input. The "variations" icon next to it is at ~`(650, 896)` — clicking that one *just* tags the next prompt with `Nx` variations and is **not** the upload affordance.
- The **Upload Files** menu item, once "+" is clicked, sits at viewport ~`(675, 745)`.
- **`Page.setInterceptFileChooserDialog` does NOT capture Stitch's file picker** in practice — no `Page.fileChooserOpened` event fires when Upload Files is clicked. There is also **no `<input type="file">` in the DOM** (`document.querySelectorAll('input[type=file]')` returns `[]`), so `DOM.setFileInputFiles` has nothing to target. Stitch's picker appears to be JS-built / synthesized and bypasses both standard CDP hooks.
- **Workaround that works today**: skip the upload entirely and put the visual context **into the brief as words**. Describe the existing UI in detail (palette, layout, spacing, typography, key elements, what to keep and what to drop). Stitch's prompt comprehension is strong enough that a precise verbal anchor produces output that matches an existing aesthetic — and you avoid the failure surface around the picker entirely.
- If you must attempt the upload, expect to debug from `Page.captureScreenshot` rather than CDP file-chooser events.

## Traps

- **Top "Try now" button position varies** — it's a small pill. If your click misses, the URL won't change to `?pli=1`. Re-screenshot, re-aim.
- **Generic Tailwind export.** Don't ship Stitch's HTML. Use the visuals to inform your own implementation.
- **Long briefs sometimes truncate visibly** in the prompt box but submit fully. Verify by checking the chat history panel after submit.
- **DPR matters when computing click coords** from screenshots. Screenshots are saved at the device pixel ratio (typically 2x), so a 3456×1882 saved file = 1728×941 viewport. Click coords are viewport-space. The harness `screenshot()` saves the raw file; the chat client may re-display it at any size. Always derive click coords as fractions of the viewport, not pixels of the displayed thumbnail.
