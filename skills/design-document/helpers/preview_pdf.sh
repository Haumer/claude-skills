#!/usr/bin/env bash
# Open a PDF for review. Prefers browser-harness if available, else system 'open'.
# Usage: preview_pdf.sh <output.pdf>
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <output.pdf>" >&2
    exit 2
fi

pdf_abs="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"

if command -v browser-harness >/dev/null 2>&1; then
    browser-harness <<PY
new_tab("file://$pdf_abs")
wait_for_load()
print(page_info())
PY
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open "$pdf_abs"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$pdf_abs"
else
    echo "Open manually: $pdf_abs"
fi
