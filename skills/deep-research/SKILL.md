---
name: deep-research
description: Autonomously research a subject (company, person, product, topic) using browser-harness and web search across multiple parallel sub-agents, then render an opinionated, scannable PDF brief — not prose, not slop. Use when the user says "research X", "find everything about X", "deep dive on X", "what do we know about X", "company research", "background check", or names a subject and asks for a brief, dossier, or one-pager. Triggers on phrases like "deep research", "research brief", "do a brief on", "find out everything", "background on".
---

# deep-research

Produce a research brief that a busy human can act on in two minutes. The format is opinionated; the inputs are not. This skill orchestrates parallel sub-agents, enforces a strict source-everything contract, and renders a Typst PDF that does not look like an LLM made it.

## When to use

Trigger on any request to investigate a named subject — a company, a person, a product, an organization, a topic — where the user wants the result *summarized for action*, not a chat transcript. Examples:

- "research Almdudler"
- "find everything about Bregenzer Festspiele"
- "background on Stefan Pierer"
- "deep dive on the company SeerAI"
- "do a brief on the Vienna mobility startup scene"

Do **not** use this skill for: code questions, single-fact lookups, debugging, or anything where one search would suffice.

## The rules (in priority order)

1. **No claim without a source.** Every fact in the brief must trace to a numbered entry in the Sources section. If an agent cannot cite it, it does not appear. No "industry estimates suggest", no inferred figures, no smoothed-over guesses. If the user asked something you genuinely couldn't verify, list it under a "What we couldn't confirm" insight rather than fabricating.
2. **Structure over prose.** The brief is tables, cards, and dated bullets. The only paragraphs are the one-line subject descriptor and the body of each numbered insight (≤ 2 sentences each). No essays. No "in conclusion". No mission-statement filler.
3. **Specificity beats coverage.** A short brief with five concrete, dated, named facts beats a long brief padded with categories. If you have nothing for a section after honest research, omit the section — do not pad it with platitudes.
4. **Parallelize.** Always fan out research across multiple sub-agents in a single message. Sequential research is the difference between a 90-second result and a 12-minute one.
5. **Render the PDF; do not reply with the brief inline.** The deliverable is the PDF (and optionally an HTML mirror). Reply with: where the file is, what's in it, and what was thin.
6. **Anti-slop language.** No emoji. No "Let's explore…". No "in today's fast-paced world". No bullet lists of synonyms. No marketing copy lifted whole from the subject's own About page — paraphrase tightly, cite, and pick the *non-obvious* thing on the page.

## Workflow

`$SKILL_DIR` below means `~/.claude/skills/deep-research/`.

### 1. Classify the subject (one sentence, no agent)

What is it? `company`, `person`, `product`, `topic`, `org`. The classification picks which research vectors to fan out.

For **company** (the default, and what this skill is tuned for):
  - web → official site, what they actually do, products, locations
  - search → Google/DuckDuckGo top results, news, mentions
  - socials → LinkedIn (company), Instagram, Facebook, X, TikTok where applicable
  - people → leadership, board, plausible local contacts, impressum
  - financials → registry data (Firmenbuch for AT, Companies House for UK, OpenCorporates, Crunchbase)
  - news → last 12 months, dated

For **person**: identity, current role, employer, public talks/papers/posts, prior roles, network, anything written by them in the last 24 months. Stay strictly on professional/public material — no doxxing.

For **product**: what it is, who makes it, pricing, alternatives, reviews (G2/Trustpilot/Reddit), recent changelog or release notes.

For **topic**: landscape map — key players, recent inflection points, primary sources, the 5-7 things a smart generalist needs to grasp it.

### 2. Fan out parallel sub-agents (single message, multiple Agent calls)

For each vector, launch a sub-agent with `subagent_type: general-purpose` (use `Explore` for purely read-only filesystem questions, but research is not that). Each sub-agent must return a single fenced JSON block matching the contract below — nothing else in the response is consumed by the synthesizer.

**Sub-agent prompt template** (adapt the vector + targets):

> You are one of several parallel researchers investigating `<SUBJECT>`. Your vector is `<VECTOR>`. Use `browser-harness` (read the `SKILL.md` in its clone first if you haven't — find it with `dirname "$(readlink -f "$(command -v browser-harness)")"`) for any DOM interaction or screenshot, and `WebSearch` / `WebFetch` for static lookups. Specifically check `domain-skills/` under browser-harness for any matching site (linkedin, facebook, sec-edgar, etc.) before improvising.
>
> Hard constraints:
> - Every fact you return must include a `source_url` it was actually observed at.
> - If you cannot verify something, omit it. Do not infer, smooth, or estimate.
> - Stop after 6–8 minutes of work. Returning fewer high-quality facts beats more low-quality ones.
> - Do not contact the subject (no form fills, no DMs, no emails).
>
> Return exactly one fenced ```json block with this shape:
> ```json
> {
>   "vector": "<VECTOR>",
>   "facts": [
>     {"key": "founded", "value": "1957", "source_url": "https://example.com/about", "source_title": "About — Example", "note": "stated on About page"}
>   ],
>   "people": [
>     {"name": "...", "role": "...", "location": "...", "link": "https://...", "why": "...", "source_url": "..."}
>   ],
>   "socials": [
>     {"platform": "LinkedIn", "handle": "@...", "url": "https://...", "audience": "...", "last": "YYYY-MM-DD", "source_url": "..."}
>   ],
>   "events": [
>     {"date": "YYYY-MM", "text": "...", "source_url": "..."}
>   ],
>   "sources": [
>     {"title": "...", "url": "...", "note": "what was extracted here"}
>   ],
>   "gaps": ["thing you tried to find and could not verify"]
> }
> ```
> Nothing outside the JSON block is consumed.

### 3. Synthesize (you, the orchestrator)

- Merge sub-agent JSON blocks. De-duplicate sources by URL. Renumber sources `[1]`, `[2]`, … in the order they first appear in the brief.
- Pick **3 TL;DR sentences**, **3–7 "Things to know" insights**, and **5–10 timeline events**. Cut ruthlessly. If the same fact came from two agents, pick the better-sourced one.
- For each insight, the *lede* is one bold sentence stating the non-obvious thing. The *body* is one supporting sentence with the specific number, date, or quote. Anything else gets cut.
- Pick at most **5 people** for the people table. Bias toward decision-makers and plausible direct contacts in the user's region if known. Skip people you cannot find both a role and a credible link for.
- Pick at most **6 social/digital channels**. Skip ones with no recent activity unless their absence is itself the story.
- Write the "What we couldn't confirm" insight last, only if the gaps list is non-trivial.

### 4. Allocate an ostack ID and render

```bash
python3 ~/.claude/skills/design-document/helpers/track_document.py allocate
# returns e.g. D0042 — record this
```

Copy templates and fill:

```bash
SUBJECT_SLUG=almdudler  # kebab-case of the subject
mkdir -p briefs && cd briefs
cp ~/.claude/skills/deep-research/templates/brief.typ ./
cp ~/.claude/skills/deep-research/templates/brief-skeleton.typ ./${SUBJECT_SLUG}.typ
# edit ${SUBJECT_SLUG}.typ — replace DXXXX with the allocated ID, replace
# subject/one-liner/prepared, fill all sections from the merged JSON.
```

Render:

```bash
typst compile ${SUBJECT_SLUG}.typ
```

Track:

```bash
python3 ~/.claude/skills/design-document/helpers/track_document.py record \
  --id D0042 \
  --path "briefs/${SUBJECT_SLUG}.pdf" \
  --keywords "<subject>, research-brief, <sector>, <country>" \
  --summary "Research brief on <SUBJECT>: one sentence on what it covers." \
  --source "deep-research skill, multi-agent web research"
```

### 5. Verify

Open the PDF and screenshot the first page via browser-harness (or `open` on macOS). Look for: orphan headings, runaway tables, broken links, untouched `DXXXX` placeholders, unfilled `—` cells in the fact grid (those should be removed, not left as em-dashes). If anything is wrong, fix the `.typ` and recompile.

### 6. Reply

Tell the user:
- the path to the PDF,
- a 2-line "what's in it" (e.g. "8 sourced facts, 4 named people, 6 timeline events, 14 sources"),
- what was thin or unverifiable (the gaps), so they know what to chase next.

That's it. No restatement of the brief, no offer to "expand any section".

## Anti-patterns (do not do these)

- Spawning sub-agents sequentially "to save tokens". Parallelize.
- Letting a sub-agent write prose back. Enforce the JSON contract.
- Including the subject's own marketing taglines verbatim as if they were facts. Paraphrase + cite, or cut.
- Emoji bullets, gradient backgrounds, sans body text, "modern" sans-serif headings, neon accent colors. The template does not allow it; do not patch it to allow it.
- A brief that's >4 pages. If yours is, you padded it. Cut.
- Replying with a copy of the brief inline. The PDF is the deliverable.
