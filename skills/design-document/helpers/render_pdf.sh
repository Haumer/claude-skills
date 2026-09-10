#!/usr/bin/env bash
# Compile a Typst document to PDF.
# Usage: render_pdf.sh [--root <path>] <source.typ> [output.pdf]
#
# Use --root when the source imports from a parent directory (Typst forbids
# parent-traversal imports unless the project root is set explicitly).
set -euo pipefail

ROOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--root) ROOT="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,7p' "$0"
            exit 0 ;;
        --) shift; break ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *) break ;;
    esac
done

if [ $# -lt 1 ]; then
    echo "usage: $0 [--root <path>] <source.typ> [output.pdf]" >&2
    exit 2
fi

src="$1"
out="${2:-${src%.typ}.pdf}"

if ! command -v typst >/dev/null 2>&1; then
    echo "error: typst not found on PATH. Install via 'brew install typst' (macOS) or see https://github.com/typst/typst" >&2
    exit 1
fi

if [ -n "$ROOT" ]; then
    typst compile --root "$ROOT" "$src" "$out"
else
    typst compile "$src" "$out"
fi
echo "$out"
