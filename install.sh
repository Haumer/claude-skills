#!/usr/bin/env bash
# claude-skills installer
#
# Symlinks every skills/<name>/ into ~/.claude/skills/<name>/ and every
# commands/<name>.md into ~/.claude/commands/<name>.md so Claude Code picks
# them up, initialises the document tracker state, checks dependencies, and
# (optionally) drops the bundled browser-harness domain skills into your
# browser-harness clone.
#
# Idempotent: re-running re-points the symlinks and re-checks deps. Existing
# non-symlink skills/commands with the same name are left alone and reported.
#
# Usage: ./install.sh [--no-deps]

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SKILLS_DST="$CLAUDE_DIR/skills"
COMMANDS_DST="$CLAUDE_DIR/commands"
STATE_DIR="$CLAUDE_DIR/ostack"
CHECK_DEPS=1
[[ "${1:-}" == "--no-deps" ]] && CHECK_DEPS=0

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }
warn() { printf '    \033[33mwarn\033[0m  %s\n' "$*"; }

link() {
  local src="$1" dst="$2"
  if [[ -L "$dst" ]]; then
    rm "$dst"
  elif [[ -e "$dst" ]]; then
    warn "$dst exists and is not a symlink — skipping (move it aside and re-run to replace)"
    return
  fi
  ln -s "$src" "$dst"
  note "$(basename "$dst") -> $src"
}

say "Installing claude-skills from $REPO_DIR"
mkdir -p "$SKILLS_DST" "$COMMANDS_DST" "$STATE_DIR"

say "Skills -> $SKILLS_DST"
for d in "$REPO_DIR"/skills/*/; do
  [[ -f "$d/SKILL.md" ]] || continue
  link "${d%/}" "$SKILLS_DST/$(basename "$d")"
done

say "Commands -> $COMMANDS_DST"
for f in "$REPO_DIR"/commands/*.md; do
  link "$f" "$COMMANDS_DST/$(basename "$f")"
done

chmod +x "$REPO_DIR"/skills/*/helpers/*.sh "$REPO_DIR"/skills/*/helpers/*.py 2>/dev/null || true

say "Document tracker state -> $STATE_DIR"
[[ -f "$STATE_DIR/state.json" ]] || { echo '{"next_id": 1}' > "$STATE_DIR/state.json"; note "created state.json"; }
[[ -f "$STATE_DIR/config.json" ]] || { echo '{"track_documents_in_git": false}' > "$STATE_DIR/config.json"; note "created config.json (track_documents_in_git: false)"; }
if [[ ! -f "$STATE_DIR/index.md" ]]; then
  printf '# Global document index\n\nEvery document the design-document / deep-research skills have created, across all projects.\n\n' > "$STATE_DIR/index.md"
  note "created index.md"
fi

# Bundled browser-harness domain skills (LinkedIn profile reader, Google Stitch)
HARNESS_DIR=""
if command -v browser-harness >/dev/null 2>&1; then
  HARNESS_DIR="$(cd "$(dirname "$(readlink -f "$(command -v browser-harness)")")" && pwd)"
fi
[[ -n "$HARNESS_DIR" && -d "$HARNESS_DIR/domain-skills" ]] || HARNESS_DIR="${BROWSER_HARNESS_DIR:-}"
if [[ -n "$HARNESS_DIR" && -d "$HARNESS_DIR/domain-skills" ]]; then
  say "browser-harness domain skills -> $HARNESS_DIR/domain-skills"
  for d in "$REPO_DIR"/browser-harness/domain-skills/*/; do
    name="$(basename "$d")"
    mkdir -p "$HARNESS_DIR/domain-skills/$name"
    cp "$d"/*.md "$HARNESS_DIR/domain-skills/$name/"
    note "$name"
  done
else
  say "browser-harness domain skills"
  note "browser-harness clone not found — skipped. Set BROWSER_HARNESS_DIR=/path/to/clone and re-run,"
  note "or copy browser-harness/domain-skills/* into the clone's domain-skills/ yourself."
fi

if (( CHECK_DEPS )); then
  say "Dependencies"
  missing=()
  for bin in typst python3 git curl jq; do
    command -v "$bin" >/dev/null 2>&1 && note "ok      $bin" || { missing+=("$bin"); warn "missing $bin"; }
  done
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import matplotlib" 2>/dev/null && note "ok      matplotlib" || warn "matplotlib not importable (only needed for charts in design-document: pip install matplotlib)"
  fi
  command -v browser-harness >/dev/null 2>&1 && note "ok      browser-harness" \
    || warn "browser-harness not on PATH — deep-research and walkthrough need it; design-document falls back to 'open'. See https://github.com/browser-use/browser-harness"
  command -v gh >/dev/null 2>&1 && note "ok      gh" || warn "gh not found — /shipit and /branchit use it to detect the default branch (optional)"
  [[ -n "${GEMINI_API_KEY:-}" ]] && note "ok      GEMINI_API_KEY set" || warn "GEMINI_API_KEY not set — only needed for /gemini (https://aistudio.google.com/apikey)"
  if (( ${#missing[@]} )); then
    echo
    warn "required tools missing: ${missing[*]}"
    [[ "$OSTYPE" == darwin* ]] && note "macOS: brew install ${missing[*]}"
    note "typst: https://github.com/typst/typst/releases"
  fi
fi

say "Done."
note "Skills: $(ls "$REPO_DIR"/skills | tr '\n' ' ')"
note "Commands: $(ls "$REPO_DIR"/commands | sed 's/\.md$//' | sed 's/^/\//' | tr '\n' ' ')"
note "Restart Claude Code (or start a new session) to pick them up."
