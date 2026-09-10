// APA7 manuscript template — full paper with title page, abstract, body, references.
// Replace the placeholder values; remove apa7-abstract block if not needed.

#import "apa7.typ": *

#show: doc => apa7-base(
  doc-id: "DXXXX",                  // replace with allocated ID from track_document.py
  title: "Your Title Here",
  author: "Author Name",
  doc,
)

#apa7-title-page(
  title: "Your Title Here",
  author: "Author Name",
  affiliation: "Institution / Department",
  course: "Course code and name",
  instructor: "Instructor",
  date: "2026-05-01",
)

#apa7-abstract[
  This is the abstract. It is a single paragraph with no first-line indent,
  approximately 150-250 words, summarizing the paper's purpose, method, key
  findings, and implications.
]

= Introduction

Body paragraphs here. APA7 indents the first line of each paragraph by 0.5in,
double-spaces text, and uses a serif font at 12pt.

= Method

Subsections use level-2 headings.

== Participants

Level-3 headings use bold italic.

= Results

= Discussion

#apa7-references[
  Author, A. A. (Year). #emph[Title of work]. Publisher.

  Author, B. B., & Author, C. C. (Year). Title of article. #emph[Journal Name], #emph[Volume]\(Issue\), pages. https://doi.org/xxxx
]
