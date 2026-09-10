# LinkedIn — reading a member profile

Auth wall. Must connect to a Chrome already logged into LinkedIn. Read-only — never send connection requests, messages, or fill forms.

## URLs

- Profile: `https://www.linkedin.com/in/<vanity>/`
- Detail sub-pages render a flat list (no auth re-prompt, no lazy modal):
  - `…/in/<vanity>/details/experience/`
  - `…/in/<vanity>/details/education/`
  - `…/in/<vanity>/details/skills/`
  - `…/in/<vanity>/details/certifications/`
  - `…/in/<vanity>/recent-activity/all/`

Prefer the `details/<section>/` pages over scrolling the main profile — they expand
every item without needing "Show all" clicks or lazy-load scrolling.

## Extraction

Coordinate clicks aren't needed for reading. Just dump text:

```python
js("(() => { const m=document.querySelector('main')||document.body; return m.innerText.slice(0,5000); })()")
```

The main profile `innerText` already contains, in order: name, headline, location,
connections count, About, Activity (follower count), full Experience (titles,
companies, dates, descriptions), Education, Licenses & certifications, Volunteering,
Recommendations, Languages, Interests. Slice in 4–5k chunks to read it all.

## Traps / quirks

- The browser tab `document.title` is `"<Name> | LinkedIn"` (may be prefixed with a
  status emoji like 🟢). Use `<main>` innerText, not structured selectors — LinkedIn's
  CSS-module class names (`.text-body-medium.break-words` etc.) are unstable/obfuscated
  and frequently return null.
- Follower count appears in the **Activity** section ("N followers"); the connections
  count ("500+ connections") is in the top card — they are different numbers.
- Experience entries grouped under one employer (e.g. multiple roles at one company)
  render as a nested list with the company name once and roles indented.
- "Open to work" green banner and "Private to you" analytics blocks are only visible to
  the profile owner / when logged in as them — ignore for third-party facts.
- Skills per role show as inline "+N skills" summaries on the main page; use
  `details/skills/` for the full named list.
