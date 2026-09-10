// Block-format business letter with APA7 typography.

#import "apa7.typ": *

#show: doc => apa7-base(
  doc-id: "DXXXX",
  title: "Letter to recipient",
  author: "Author Name",
  doc,
)

// Block format: everything left-aligned, paragraphs separated by blank line, no first-line indent.
#set par(first-line-indent: 0in, leading: 0.7em)

Author Name \
Street Address \
City, State ZIP \
email\@example.com \

#v(1em)
2026-05-01
#v(1em)

Recipient Name \
Title \
Organization \
Street Address \
City, State ZIP

#v(1em)

Dear Recipient Name,

First paragraph: state the purpose of the letter.

Second paragraph: details, context, request.

Third paragraph: closing, next steps, contact info.

#v(1em)

Sincerely,

#v(2em)

Author Name
