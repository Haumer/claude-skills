// brief.typ — opinionated research brief template.
//
// Design rules (do not improvise away from these):
//   - Serif body (Times/CMU). Sans only for the tag/chip/section-label row.
//   - One accent color: deep oxblood (#6b1f2a). Use for the cover bar, section
//     rules, and the report ID. Never for body text or chart fills.
//   - Information-dense, not prose. Tables and cards, not paragraphs.
//   - No emoji, no gradients, no full-width photos, no neon, no rounded badges.
//   - Every claim is footnoted with a source number that ties to the Sources
//     section. If a fact has no source, it does not appear in the brief.

#let accent = rgb("#6b1f2a")
#let muted = rgb("#5a5a5a")
#let rule-color = rgb("#cfcfcf")

#let serif = ("Times New Roman", "New Computer Modern", "Liberation Serif")
#let sans = ("Helvetica Neue", "Helvetica", "Arial", "Liberation Sans")

#let brief(
  doc-id: none,
  subject: "",
  one-liner: "",
  prepared: "",
  body,
) = {
  set document(
    title: subject + " — research brief",
    keywords: if doc-id != none { ("ostack-id:" + doc-id,) } else { () },
  )
  set page(
    paper: "a4",
    margin: (x: 1.6cm, top: 2cm, bottom: 1.8cm),
    footer: context [
      #set text(font: sans, size: 8pt, fill: muted)
      #grid(
        columns: (1fr, auto, 1fr),
        align: (left, center, right),
        subject + " — research brief",
        if doc-id != none { doc-id } else { "" },
        [#counter(page).display() / #context counter(page).final().first()],
      )
    ],
  )
  set text(font: serif, size: 10pt, lang: "en")
  set par(leading: 0.55em, justify: false, first-line-indent: 0pt)

  // Section heading: small-caps sans, accent rule below.
  show heading.where(level: 1): it => block(width: 100%, above: 1.4em, below: 0.5em)[
    #set text(font: sans, size: 9pt, weight: "bold", tracking: 0.12em)
    #upper(it.body)
    #v(2pt)
    #line(length: 100%, stroke: 0.6pt + accent)
  ]
  show heading.where(level: 2): it => block(width: 100%, above: 0.9em, below: 0.3em)[
    #set text(font: serif, size: 11pt, weight: "bold")
    #it.body
  ]

  // Cover
  block[
    #set text(font: sans, size: 8pt, weight: "bold", tracking: 0.18em, fill: accent)
    #upper("Research Brief")
    #h(1fr)
    #if doc-id != none [#text(font: sans, size: 8pt, fill: muted, doc-id)]
  ]
  v(2pt)
  line(length: 100%, stroke: 1.2pt + accent)
  v(0.6em)
  text(font: serif, size: 22pt, weight: "bold", subject)
  v(0.2em)
  text(font: serif, size: 11pt, style: "italic", fill: muted, one-liner)
  v(0.4em)
  block[
    #set text(font: sans, size: 8pt, fill: muted)
    Prepared #prepared
  ]
  v(0.8em)

  body
}

// ---------- structural helpers ----------

// chip: small uppercase sans label, used for tags
#let chip(s) = box(inset: (x: 5pt, y: 2pt), stroke: 0.5pt + muted, radius: 1pt)[
  #text(font: sans, size: 7pt, weight: "bold", tracking: 0.1em, upper(s))
]

// fact-grid: 2-column key/value table for "Key facts"
#let fact-grid(..pairs) = {
  let items = pairs.pos()
  block(stroke: (top: 0.4pt + rule-color, bottom: 0.4pt + rule-color), inset: (y: 6pt), width: 100%)[
    #table(
      columns: (auto, 1fr, auto, 1fr),
      column-gutter: 18pt,
      row-gutter: 4pt,
      stroke: none,
      align: (left, left, left, left),
      ..items.map(p => (
        text(font: sans, size: 8pt, fill: muted, weight: "bold", tracking: 0.06em, upper(p.at(0))),
        text(font: serif, size: 9.5pt, p.at(1)),
      )).flatten()
    )
  ]
}

// insight: numbered "thing to know" — bold lede, supporting sentence, source ref.
#let insight(num: 1, lede: "", body: "", src: "") = block(below: 10pt, width: 100%)[
  #grid(columns: (22pt, 1fr), gutter: 6pt,
    align(top + right)[#text(font: serif, size: 14pt, weight: "bold", fill: accent, str(num))],
    [
      #text(font: serif, size: 10.5pt, weight: "bold", lede)
      #h(4pt)
      #text(font: serif, size: 10pt, body)
      #if src != "" [
        #text(font: sans, size: 7pt, fill: muted, " [" + src + "]")
      ]
    ]
  )
]

// header cell helper
#let _hcell(s) = text(font: sans, size: 7.5pt, weight: "bold", tracking: 0.08em, fill: muted, s)

// people-row: name, role, location, contact, why
#let people-table(rows) = {
  let cells = (
    _hcell("NAME"), _hcell("ROLE"), _hcell("LOCATION"), _hcell("LINK"), _hcell("WHY THEY MATTER"),
  )
  for r in rows {
    cells = cells + (
      text(font: serif, size: 9.5pt, weight: "bold", r.name),
      text(font: serif, size: 9.5pt, r.role),
      text(font: serif, size: 9pt, fill: muted, r.location),
      if r.link != "" { text(font: sans, size: 8pt, link(r.link, "↗")) } else { text("—") },
      text(font: serif, size: 9pt, r.why),
    )
  }
  table(
    columns: (auto, 1fr, auto, auto, 1.4fr),
    column-gutter: 8pt,
    row-gutter: 4pt,
    inset: (y: 5pt),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt + accent) } else { (bottom: 0.3pt + rule-color) },
    align: (left, left, left, left, left),
    ..cells,
  )
}

// socials-table: platform, handle, followers, last activity
#let socials-table(rows) = {
  let cells = (
    _hcell("PLATFORM"), _hcell("HANDLE / URL"), _hcell("AUDIENCE"), _hcell("LAST OBSERVED"),
  )
  for r in rows {
    cells = cells + (
      text(font: serif, size: 9.5pt, weight: "bold", r.platform),
      text(font: sans, size: 8.5pt, link(r.url, r.handle)),
      text(font: serif, size: 9.5pt, r.audience),
      text(font: serif, size: 9pt, fill: muted, r.last),
    )
  }
  table(
    columns: (auto, 1fr, auto, 1.2fr),
    column-gutter: 10pt,
    row-gutter: 4pt,
    inset: (y: 5pt),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt + accent) } else { (bottom: 0.3pt + rule-color) },
    align: (left, left, right, left),
    ..cells,
  )
}

// route-table: a generic 4-column "where to address what" routing table.
// Columns: scope, entity / address, key contact, note. Useful for multi-entity
// company briefs where the "who do I email" answer depends on country / topic.
#let route-table(rows) = {
  let cells = (
    _hcell("SCOPE"), _hcell("ENTITY / ADDRESS"), _hcell("KEY CONTACT"), _hcell("NOTE"),
  )
  for r in rows {
    cells = cells + (
      text(font: serif, size: 9.5pt, weight: "bold", r.scope),
      text(font: serif, size: 9pt, r.entity),
      text(font: serif, size: 9pt, r.contact),
      text(font: serif, size: 9pt, fill: muted, r.note),
    )
  }
  table(
    columns: (auto, 1.6fr, 1fr, 1.4fr),
    column-gutter: 8pt,
    row-gutter: 4pt,
    inset: (y: 5pt),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt + accent) } else { (bottom: 0.3pt + rule-color) },
    align: (left, left, left, left),
    ..cells,
  )
}

// timeline-row: date, headline, source
#let timeline(items) = {
  for it in items {
    block(below: 6pt)[
      #grid(columns: (62pt, 1fr), gutter: 8pt,
        text(font: sans, size: 8pt, weight: "bold", fill: accent, it.date),
        [
          #text(font: serif, size: 10pt, it.text)
          #if it.src != "" [#text(font: sans, size: 7pt, fill: muted, " [" + it.src + "]")]
        ]
      )
      #v(2pt)
      #line(length: 100%, stroke: 0.3pt + rule-color)
    ]
  }
}

// sources-list: numbered references with hanging indent feel
#let sources(items) = {
  set par(first-line-indent: 0pt, leading: 0.5em)
  for (i, s) in items.enumerate() {
    block(below: 4pt)[
      #grid(columns: (22pt, 1fr), gutter: 4pt,
        text(font: sans, size: 8pt, weight: "bold", fill: muted, "[" + str(i + 1) + "]"),
        [
          #text(font: serif, size: 9pt, weight: "bold", s.title) #h(4pt)
          #text(font: sans, size: 8pt, link(s.url, s.url))
          #if s.at("note", default: "") != "" [
            #linebreak()
            #text(font: serif, size: 8.5pt, fill: muted, style: "italic", s.note)
          ]
        ]
      )
    ]
  }
}
