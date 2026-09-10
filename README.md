# claude-skills

Claude Code skills and slash commands I wrote and use daily. Opinionated, small, and built around one idea: the output should look like a careful human made it, and every claim in it should be traceable.

| Skill / command | What it does | Needs |
|---|---|---|
| [**deep-research**](skills/deep-research/SKILL.md) | "research Almdudler" → fans out parallel sub-agents over the browser and the web, enforces a source-everything JSON contract, renders a ≤ 4-page Typst PDF brief: TL;DR, fact grid, insights, people, digital footprint, timeline, sources. | typst, python3, browser-harness, design-document |
| [**design-document**](skills/design-document/SKILL.md) | Papers, reports, memos and letters as APA7-typeset PDFs via Typst. Charts follow APA7 and cite their data. Every document gets a global ID and lands in a per-project `documents.md`. | typst, python3, matplotlib (charts only) |
| [**focus**](skills/focus/SKILL.md) | Makes the agent's attention visible while it drives browser-harness: a cursor glides to the element about to be used, a spotlight dims the rest, a scan line sweeps text being read, a chip names the action and a narration bar says why. It never freezes: idle drift, breathing ring, a THINKING state between decisions. A chat bubble lets the viewer pause and take over, step, stop, approve or skip each action, and message the agent; pressing P lets them draw annotated boxes that interrupt the agent immediately, Esc hides it and stops. A survey step shows the candidates being weighed before one is chosen; a peek step reads linked pages ahead without navigating, so several actions can run in one go. Every click and keystroke is still real. `walkthrough` uses it. | browser-harness |
| [**walkthrough**](skills/walkthrough/SKILL.md) | Annotated live product tour in your own browser: impersonate a fresh user, drive a journey step by step, verify state outside the UI after every step, log every bug hit. | browser-harness, focus |
| [**gemini**](skills/gemini/SKILL.md) | Gemini from the shell with plain curl: image generation and editing with reference-image composition, text prompts, key lookup, base64 output decoding. | curl, jq, `GEMINI_API_KEY` |
| [**/branchit**](commands/branchit.md) | New branch + git worktree from the latest pushed default branch, with a dirty-tree check that ignores scratch files but stops on real changes. | git, gh (optional) |
| [**/shipit**](commands/shipit.md) | Ship a feature branch: merge main in, run tests, look for lost work, merge, push, deploy (kamal / fly / heroku / CI), smoke-test prod, clean up. | git, gh, your deploy CLI |
| [**/wt**](commands/wt.md) | Short alias for `walkthrough`. | walkthrough |

Also bundled: two [browser-harness domain skills](browser-harness/domain-skills/) (LinkedIn profile reader, Google Stitch) that `deep-research` and design work lean on.

## Install

```bash
git clone https://github.com/Haumer/claude-skills ~/code/claude-skills
cd ~/code/claude-skills
./install.sh
```

`install.sh` symlinks `skills/*` into `~/.claude/skills/` and `commands/*.md` into `~/.claude/commands/`, initialises the document tracker state in `~/.claude/ostack/`, copies the domain skills into your browser-harness clone if it finds one, and reports which dependencies are missing. It never overwrites a skill or command you already have under the same name. Re-run after `git pull`.

Restart Claude Code afterwards. Then, in any project:

```
research Almdudler
write a one-page memo about the Q3 roadmap
/wt checkout as a new customer
/branchit fix-login
/shipit
```

## Dependencies

| Dependency | Used by | Install |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | everything | `npm install -g @anthropic-ai/claude-code` |
| [Typst](https://typst.app) | deep-research, design-document | `brew install typst` or [releases](https://github.com/typst/typst/releases) |
| Python 3 | design-document tracker, deep-research | system / `brew install python` |
| [matplotlib](https://matplotlib.org) | design-document charts only | `pip install matplotlib` |
| [browser-harness](https://github.com/browser-use/browser-harness) | deep-research, walkthrough, PDF verification | clone it and follow its `install.md`; it connects to your real Chrome over CDP |
| curl, jq | gemini | `brew install jq` |
| `GEMINI_API_KEY` | gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey), export in your shell |
| git, [gh](https://cli.github.com) | branchit, shipit | `brew install gh` |
| kamal / fly / heroku CLI | shipit deploy step | whichever your project deploys with |

There are no npm dependencies. The skills are Markdown, Typst templates and two small Python helpers.

## How the pieces fit

- `design-document` owns the document tracker (`helpers/track_document.py`). It allocates global IDs (`D0001`, `D0002`, …) from `~/.claude/ostack/state.json`, appends to the project's `documents.md` and to `~/.claude/ostack/index.md`. `deep-research` reuses it, so install both.
- `deep-research` templates live in `skills/deep-research/templates/`: `brief.typ` is the styling (serif body, one oxblood accent, tables not prose), `brief-skeleton.typ` is what gets copied and filled.
- `design-document` templates are `apa7.typ` (shared base) plus `apa7-paper`, `apa7-report`, `apa7-memo`, `apa7-letter`. A rendered example is in `skills/design-document/examples/`.
- `focus` is two files: `focus.js` (the overlay, injected into the page) and `focus.py` (wrappers that animate first, then perform the real CDP action at the same pixel). `browser-harness < skills/focus/demo.py` shows it on Wikipedia.
- `walkthrough` expects a `walkthroughs/NOTES.md` at your repo root (dev URL, fast login, dialog framework, personas). It creates one on the first run and writes a replayable record per run to `walkthroughs/<date>-<journey>.md`.
- `/wt` is a one-line command that invokes the `walkthrough` skill with its arguments.

## Design rules these skills enforce

- No claim without a source. If a sub-agent cannot cite it, it does not appear.
- Serif body, one accent colour at most, no emoji, no gradients, no marketing copy lifted verbatim.
- Tables and dated bullets over paragraphs. A brief longer than four pages was padded.
- The PDF is the deliverable. The chat reply says where the file is and what was thin.
- Verify before declaring done: open the PDF, screenshot a page, look for orphan headings and runaway tables.

## Tests

```bash
bash tests/smoke.sh                       # compile every Typst template and example
python3 -m pytest tests/ -v               # document tracker
```

## License

MIT. See [LICENSE](LICENSE).
