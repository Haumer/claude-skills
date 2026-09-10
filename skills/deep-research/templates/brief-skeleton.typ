#import "brief.typ": *

#show: brief.with(
  doc-id: "DXXXX",
  subject: "SUBJECT NAME",
  one-liner: "One short italic line that captures what this entity actually is.",
  prepared: "YYYY-MM-DD",
)

= TL;DR
- One sentence on what they do and for whom. [1]
- One sentence on scale or stage (size, revenue, ownership, recent change). [2]
- One sentence on the most actionable thing to know right now. [3]

= Key facts
#fact-grid(
  ("Founded", "—"),
  ("Headquarters", "—"),
  ("Ownership", "—"),
  ("Sector", "—"),
  ("Headcount", "—"),
  ("Website", "—"),
)

= Things to know
#insight(num: 1, lede: "Bold lede sentence.", body: "One supporting sentence with the specific detail that makes the lede non-obvious.", src: "1")
#insight(num: 2, lede: "Bold lede sentence.", body: "Supporting detail.", src: "2")
#insight(num: 3, lede: "Bold lede sentence.", body: "Supporting detail.", src: "3")

= People
#people-table((
  (name: "Full Name", role: "Title", location: "City", link: "https://linkedin.com/...", why: "What makes them the right contact / decision-maker."),
))

= Digital footprint
#socials-table((
  (platform: "Web", handle: "example.com", url: "https://example.com", audience: "—", last: "—"),
  (platform: "LinkedIn", handle: "@company", url: "https://linkedin.com/company/...", audience: "10k", last: "2026-05-01"),
))

= Recent activity
#timeline((
  (date: "2026-04", text: "Most recent observable thing they did. Concrete, dated, sourced.", src: "4"),
  (date: "2026-02", text: "Earlier event.", src: "5"),
))

= Sources
#sources((
  (title: "Source title", url: "https://example.com/page", note: "What was extracted from here."),
))
