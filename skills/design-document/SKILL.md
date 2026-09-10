---
name: design-document
description: Create well-designed PDFs (papers, reports, letters, memos) using APA7 conventions via Typst. Use when the user asks to write, draft, generate, or design a document — paper, report, memo, letter, brief, white paper, essay. Charts follow APA7 too and cite their data sources. Every document gets a global ID, lands in documents.md, and can be reviewed in the browser. Triggers on phrases like "write a document", "draft a report", "make a PDF", "write this up", "memo about X", "one-pager on Y".
---

# design-document

Make documents that look like a careful human made them, not a model fishing for novelty. Default to APA7 because it is familiar, neutral, citation-friendly, and avoids the "AI document" tells: branded sans-serif body text, decorative gradients, emoji bullets, neon accent colors on chart axes.

## When to use this skill

Trigger on any request to produce a written document destined for a PDF: papers, reports, memos, letters, briefs, one-pagers, essays, white papers, project writeups, executive summaries. Also trigger when the user asks for "a document about X" without specifying form — assume APA7 paper unless they signal otherwise (a memo or letter has its own template).

Do **not** use this skill for: README files, code documentation, GitHub issues, slide decks (different skill), or anything the user explicitly wants in HTML/Markdown.

## The rules (in priority order)

1. **APA7 typography or nothing.** Times New Roman 12pt body, double-spaced, 1-inch margins, running head, page numbers top-right, hanging indents on references. Do not improvise fonts or colors. If the user asks for "a different look", ask what specifically and adjust the template — never silently style.
2. **Charts follow APA7 too.** Serif font on labels, no gridlines unless they aid reading, grayscale-safe palette, figure caption *below* the figure with a number ("Figure 1. ...") and a data source line. Use `helpers/apa7_chart.py` — it sets the matplotlib defaults.
3. **Cite data, always.** Any chart or stat must reference a dataset. If the user gave you the data inline, reference it as such ("Source: data provided by user, 2026-05-01"). If they didn't, ask before fabricating. The tracker entry records the reference.
4. **Every document gets a global ID — but not in the filename.** Use `helpers/track_document.py` to allocate one before writing the file. The ID lives in the PDF metadata (so the file carries it) and in the tracker entries. The filename is whatever the document actually is — `quarterly-update.pdf`, not `D0007-quarterly-update.pdf`. IDs are bookkeeping for the assistant, not branding for the user.
5. **Track every document in `documents.md`.** Per-project, in cwd. The tracker also updates the global index at `~/.claude/ostack/index.md`.
6. **Offer git-tracking.** If the cwd is a git repo, commit the source `.typ` and the rendered `.pdf` after each document. If it's not a git repo and looks like a sensible place to track work (i.e., not `~/Downloads`), offer to `git init`.
7. **Verify before declaring done.** Open the rendered PDF (browser-harness if available, `open` on macOS otherwise) and screenshot at least one page to check for broken layout: orphan headings, line/page breaks, chart misalignment, runaway widths. Mention what you saw.

## The workflow

`$SKILL_DIR` below means `~/.claude/skills/design-document/` (where the skill is symlinked).

For a new document:

```text
1. Allocate ID            python3 $SKILL_DIR/helpers/track_document.py allocate
                          (returns e.g. D0007 — keep it; you'll embed it as PDF metadata)

2. Copy template files    cp $SKILL_DIR/templates/apa7.typ ./
                          cp $SKILL_DIR/templates/apa7-paper.typ ./quarterly-update.typ
                          (BOTH files must end up in the same directory — apa7.typ is
                          imported as a sibling. Picking apa7-paper / apa7-report /
                          apa7-memo / apa7-letter depends on the doc type.)

3. Edit quarterly-update.typ
                          - replace doc-id "DXXXX" with the allocated ID (e.g. "D0007")
                          - replace title, author, affiliation, etc.
                          - fill the body content
                          - update or remove the references block as needed

4. Render                 bash $SKILL_DIR/helpers/render_pdf.sh quarterly-update.typ
                          → produces quarterly-update.pdf in the same dir
                          (filename is whatever the doc is about — NOT the ID)

5. Verify                 bash $SKILL_DIR/helpers/preview_pdf.sh quarterly-update.pdf
                          (browser-harness if available, else system 'open')
                          Screenshot at least one page; check for orphan headings,
                          chart misalignment, runaway widths, missing page numbers.

6. Track                  python3 $SKILL_DIR/helpers/track_document.py record \
                              --id D0007 --path ./quarterly-update.pdf \
                              --keywords "kw1,kw2,kw3" \
                              --summary "One sentence."

7. Git commit (if repo + tracking enabled)
                          git add quarterly-update.typ quarterly-update.pdf apa7.typ documents.md
                          git commit -m "doc: D0007 quarterly update"
```

**Tracking config:** Read `~/.claude/ostack/config.json` before step 7:
- `track_documents_in_git: true` (default) — commit source + PDF + tracker.
- `track_documents_in_git: false` — skip the commit; the doc is still recorded in `documents.md` and the global index.

If the cwd isn't a git repo and looks like a sensible place to track work (i.e., not `~/Downloads`, `/tmp`, etc.), offer `git init` once. Don't push.

If the config file is missing, assume `true` (matches install default).

For a **revision** of an existing doc (same content, refined):

```text
python3 $SKILL_DIR/helpers/track_document.py revise --id D0007 --note "fixed table, tightened intro"
```

This bumps the version in the tracker entry. The filename can stay the same (overwriting the prior PDF) or you can save as `quarterly-update-v2.pdf` if the user wants both versions kept side by side. Git history covers versioning when the repo is git-tracked.

## Templates

Each template is a Typst file in `templates/`. They all import a shared `apa7.typ` that defines the running head, title-page block, abstract block, body styling, and reference list with hanging indents.

- `apa7-paper.typ` — full APA7 manuscript (title page, abstract, body, references). Default.
- `apa7-report.typ` — APA7 typography but report layout (title block at top of page 1, no separate title page, sections numbered).
- `apa7-memo.typ` — internal memo (TO/FROM/DATE/RE block, no abstract).
- `apa7-letter.typ` — block-format business letter with APA7 typography.

When the user is vague, pick `apa7-paper.typ`. When they say "one-pager" or "brief", use `apa7-report.typ` and keep it terse.

## Charts

Use `helpers/apa7_chart.py`. It exposes a context manager that applies the APA7 matplotlib rcParams and a `save_figure(fig, path, caption, source)` helper that writes both the PNG (300 DPI) and a sidecar `.caption.txt` you embed under the figure in Typst.

```python
from apa7_chart import apa7_style, save_figure
import matplotlib.pyplot as plt

with apa7_style():
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(years, values)
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue (USD millions)")
    save_figure(fig, "fig1.png",
                caption="Annual revenue, 2018–2025.",
                source="Internal finance dashboard, retrieved 2026-05-01.")
```

If the user wants a chart and you don't have data, **ask**. Do not invent numbers.

## Verification (browser-harness)

If `browser-harness` is on PATH, prefer it for verification — you can scroll the rendered PDF, take screenshots of specific pages, and report layout issues with evidence:

```bash
browser-harness <<'PY'
new_tab("file:///abs/path/to/D0007-foo.pdf")
wait_for_load()
screenshot()  # check page 1
PY
```

Report what you saw: "Page 2 has an orphan heading at the bottom; tightened the prior paragraph and re-rendered." If `browser-harness` isn't installed, fall back to `open <pdf>` (macOS) and ask the user to confirm.

Common issues to watch for and how to fix them:

| Symptom | Likely cause | Fix |
|---|---|---|
| Heading alone at bottom of page | No `keep-with-next` on heading | Add `#set heading(numbering: ..., supplement: ...)` with `block(breakable: false)` wrapping heading + first para, or insert `#pagebreak()` strategically |
| Chart wider than text column | Image natural size > text width | `#image("fig1.png", width: 100%)` instead of unbounded |
| References don't have hanging indent | Forgot to use `#bibliography` or wrap in `apa7-references` block | Use the template's reference helper |
| Body text looks too tight | Single-spaced by default in Typst | Template sets `par(leading: 1em)` for double-spacing — confirm template was imported |
| Page numbers missing | No header set | Template includes `set page(header: ...)` — confirm template wasn't bypassed |

## What to ask the user, briefly, before starting

- **Type** if not obvious: paper, report, memo, letter.
- **Audience** if it changes register (e.g., academic vs. internal team).
- **Length target** if you don't have a clear scope ("a one-pager", "5–8 pages").
- **Data** if the doc needs numbers and they haven't supplied them.

Do not ask about fonts, margins, colors, or layout. Those are decided — APA7.

## What not to do

- Don't pick a font other than the template's serif (Times New Roman or its free equivalent New Computer Modern / Liberation Serif).
- Don't add color outside grayscale unless the user explicitly asks for one accent color.
- Don't use emoji in document body, headings, or charts.
- Don't add a logo unless the user provides one.
- Don't fabricate data, citations, or references. If you need a reference and don't have one, leave a `[CITATION NEEDED: …]` placeholder and tell the user.
- Don't skip the tracker. Even drafts get IDs — that is how the user finds them later.
