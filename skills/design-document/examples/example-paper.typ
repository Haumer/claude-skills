// Worked example — render with:
//   bash ../helpers/render_pdf.sh example-paper.typ
//
// Demonstrates: title page, abstract, body sections, a figure with caption +
// source line, and a reference list with hanging indent.

#import "../templates/apa7.typ": *

#show: doc => apa7-base(
  doc-id: "D0001",
  title: "On the Familiarity of Things: A Note on AI-Authored Documents",
  author: "Alex Haumer",
  doc,
)

#apa7-title-page(
  title: "On the Familiarity of Things: A Note on AI-Authored Documents",
  author: "Alex Haumer",
  affiliation: "ostack",
  course: "Example",
  instructor: "—",
  date: "2026-05-01",
)

#apa7-abstract[
  Documents authored by general-purpose language models tend to drift toward
  visual novelty: branded sans-serif body text, decorative gradients, emoji
  bullets, neon accent colors. This brief note argues that the appropriate
  default for ordinary documents is APA7, not because APA7 is exciting but
  because it is familiar — and familiarity, here, is a feature.
]

= Introduction

The first time someone reads a document produced by a model, the typography
itself is a signal. A reader who has spent decades reading APA7-formatted
papers, business memos in Times New Roman, and reports with grayscale charts
will register the unusual font, the colored heading, and the emoji bullet
not as personality but as #emph[wrongness]. The signal is louder than the
content.

= A simple default

Default to APA7. When the user explicitly asks for something else, pick that
something else with care and ask what specifically they want different.

#apa7-references[
  American Psychological Association. (2020). #emph[Publication manual of the American Psychological Association] (7th ed.). https://doi.org/10.1037/0000165-000
]
