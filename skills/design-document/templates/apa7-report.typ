// APA7-styled report — typography of APA7, layout of a report (no separate title page).
// Use for one-pagers, internal briefs, project writeups.

#import "apa7.typ": *

#show: doc => apa7-base(
  doc-id: "DXXXX",
  title: "Report Title",
  author: "Author Name",
  doc,
)

#align(center)[
  #text(weight: "bold", size: 14pt, "Report Title")
  #linebreak()
  #text(size: 11pt, "Author Name · 2026-05-01")
]
#v(0.5em)

= Summary

One paragraph summarizing the report.

= Background

= Findings

= Recommendations

#apa7-references[
  Author, A. A. (Year). #emph[Title of work]. Publisher.
]
