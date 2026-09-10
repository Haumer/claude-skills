#!/usr/bin/env bash
# smoke.sh — compile every Typst template and example. Fail on any error.
# Run from anywhere; resolves paths relative to this script.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if ! command -v typst >/dev/null 2>&1; then
    echo "skip: typst not installed" >&2
    exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail=0
TYP_FILES=$(find skills -name '*.typ' -not -name 'apa7.typ' | sort)

for t in $TYP_FILES; do
    out="$TMP/$(basename "${t%.typ}").pdf"
    log="$TMP/$(basename "${t%.typ}").log"
    if typst compile --root . "$t" "$out" >"$log" 2>&1; then
        size=$(wc -c < "$out" | tr -d ' ')
        echo "ok    $t  ($size bytes)"
    else
        echo "FAIL  $t"
        sed 's/^/      /' "$log" | head -30
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo
    echo "smoke test FAILED"
    exit 1
fi
echo
echo "smoke test passed"
