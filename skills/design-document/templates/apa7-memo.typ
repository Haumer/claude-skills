// Memo template — APA7 typography with TO/FROM/DATE/RE block.

#import "apa7.typ": *

#show: doc => apa7-base(
  doc-id: "DXXXX",
  title: "Memo subject",
  author: "Author Name",
  doc,
)

#align(center, text(weight: "bold", size: 14pt, "MEMORANDUM"))
#v(0.5em)

#table(
  columns: (auto, 1fr),
  stroke: none,
  align: (right, left),
  inset: 4pt,
  text(weight: "bold", "TO:"), [Recipient(s)],
  text(weight: "bold", "FROM:"), [Author Name],
  text(weight: "bold", "DATE:"), [2026-05-01],
  text(weight: "bold", "RE:"), [Memo subject],
)

#v(0.5em)
#line(length: 100%, stroke: 0.5pt)
#v(0.5em)

= Purpose

One sentence stating why this memo exists.

= Background

= Discussion

= Recommendation
