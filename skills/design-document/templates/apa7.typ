// apa7.typ — shared APA7 styling primitives for ostack design-document skill.
//
// Provides:
//   apa7-base       page setup, fonts, paragraph defaults, heading levels
//   apa7-title-page student/professional title page
//   apa7-abstract   abstract block (own page, no first-line indent)
//   apa7-references reference list with hanging indent
//   apa7-figure     figure with caption + source line, APA7-formatted

#let apa7-fonts = ("Times New Roman", "New Computer Modern", "Liberation Serif")

#let apa7-base(
  doc-id: none,
  title: "",
  author: "",
  body,
) = {
  // Embed the ostack ID into PDF metadata via keywords. The filename does
  // *not* include the ID — it's bookkeeping for the assistant only.
  set document(
    title: title,
    author: author,
    keywords: if doc-id != none { ("ostack-id:" + doc-id,) } else { () },
  )

  set page(
    paper: "us-letter",
    margin: (x: 1in, y: 1in),
    numbering: "1",
    number-align: right + top,
  )

  set text(
    font: apa7-fonts,
    size: 12pt,
    lang: "en",
  )

  // APA7: double-spaced, left-aligned (ragged right), 0.5in first-line indent.
  set par(
    leading: 1em,
    justify: false,
    first-line-indent: 0.5in,
  )

  // Heading levels per APA7 (5 levels):
  //   L1: centered, bold, title case
  //   L2: flush left, bold, title case
  //   L3: flush left, bold italic, title case
  //   L4: indented, bold, title case, period, run-in (handled inline)
  //   L5: indented, bold italic, title case, period, run-in
  show heading.where(level: 1): it => block(width: 100%, above: 1.5em, below: 0.5em)[
    #set align(center)
    #set text(weight: "bold", size: 12pt)
    #it.body
  ]
  show heading.where(level: 2): it => block(width: 100%, above: 1.2em, below: 0.4em)[
    #set align(left)
    #set text(weight: "bold", size: 12pt)
    #it.body
  ]
  show heading.where(level: 3): it => block(width: 100%, above: 1em, below: 0.4em)[
    #set align(left)
    #set text(weight: "bold", style: "italic", size: 12pt)
    #it.body
  ]

  body
}

#let apa7-title-page(
  title: "",
  author: "",
  affiliation: "",
  course: "",
  instructor: "",
  date: "",
) = {
  set align(center)
  v(2in)
  text(weight: "bold", size: 12pt, title)
  v(2em)
  text(author)
  if affiliation != "" { linebreak(); text(affiliation) }
  if course != "" { linebreak(); text(course) }
  if instructor != "" { linebreak(); text(instructor) }
  if date != "" { linebreak(); text(date) }
  pagebreak()
}

#let apa7-abstract(body) = {
  align(center, text(weight: "bold", "Abstract"))
  v(0.5em)
  // Abstract is a single paragraph, no first-line indent.
  set par(first-line-indent: 0in)
  body
  pagebreak()
}

#let apa7-references(body) = {
  align(center, text(weight: "bold", "References"))
  v(0.5em)
  // Hanging indent: first line flush, subsequent lines indented 0.5in.
  set par(hanging-indent: 0.5in, first-line-indent: 0in)
  body
}

// APA7 figure: image, then "Figure N. caption" then "Note. Source: ..."
// `source` is required — every chart must cite its data.
#let apa7-figure(
  number: 1,
  image-path: "",
  caption: "",
  source: "",
  width: 100%,
) = {
  block(breakable: false)[
    #align(center, image(image-path, width: width))
    #v(0.4em)
    #set par(first-line-indent: 0in)
    #text(weight: "bold", "Figure " + str(number) + ". ")
    #caption
    #linebreak()
    #emph("Note.") " Source: " + source
  ]
}
