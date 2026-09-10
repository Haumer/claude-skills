#!/usr/bin/env python3
"""
Track documents created by the design-document skill.

Two stores:
  - Global: ~/.claude/ostack/state.json   (next_id counter)
            ~/.claude/ostack/index.md     (every doc ever made, across projects)
  - Local:  ./documents.md                (docs made in the current project)

Subcommands:
  allocate                              -> prints the next ID (e.g. D0007), bumps counter
  record  --id D0007 --path foo.pdf
          --keywords "k1,k2,k3"
          --summary "..."
          [--source "..."]              -> appends entries to local + global indexes
  revise  --id D0007 --note "..."       -> appends a revision note
  list                                  -> prints local documents.md
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

OSTACK_DIR = Path.home() / ".claude" / "ostack"
STATE_FILE = OSTACK_DIR / "state.json"
GLOBAL_INDEX = OSTACK_DIR / "index.md"
LOCAL_INDEX_NAME = "documents.md"


def ensure_global() -> None:
    OSTACK_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({"next_id": 1}))
    if not GLOBAL_INDEX.exists():
        GLOBAL_INDEX.write_text(
            "# ostack — global document index\n\n"
            "Every document the design-document skill has created, across all projects.\n\n"
        )


def ensure_local() -> Path:
    p = Path.cwd() / LOCAL_INDEX_NAME
    if not p.exists():
        p.write_text(
            "# Documents\n\n"
            "Documents created by the design-document skill in this project. "
            "Entries are append-only; prune by editing this file directly.\n\n"
        )
    return p


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def cmd_allocate(_args) -> None:
    ensure_global()
    state = json.loads(STATE_FILE.read_text())
    n = state["next_id"]
    state["next_id"] = n + 1
    STATE_FILE.write_text(json.dumps(state))
    print(f"D{n:04d}")


def cmd_record(args) -> None:
    ensure_global()
    local = ensure_local()
    abs_path = str(Path(args.path).resolve())
    cwd = str(Path.cwd())
    keywords = ", ".join(k.strip() for k in args.keywords.split(",") if k.strip())

    local_entry = (
        f"## {args.id} — {Path(args.path).name}\n"
        f"- **Created**: {now()}\n"
        f"- **Path**: `{abs_path}`\n"
        f"- **Keywords**: {keywords}\n"
        f"- **Summary**: {args.summary}\n"
    )
    if args.source:
        local_entry += f"- **Source**: {args.source}\n"
    local_entry += "\n"

    with local.open("a") as f:
        f.write(local_entry)

    global_entry = (
        f"## {args.id} — {Path(args.path).name}\n"
        f"- **Created**: {now()}\n"
        f"- **Project**: `{cwd}`\n"
        f"- **Path**: `{abs_path}`\n"
        f"- **Keywords**: {keywords}\n"
        f"- **Summary**: {args.summary}\n"
    )
    if args.source:
        global_entry += f"- **Source**: {args.source}\n"
    global_entry += "\n"

    with GLOBAL_INDEX.open("a") as f:
        f.write(global_entry)

    print(f"recorded {args.id} in {local} and {GLOBAL_INDEX}")


def cmd_revise(args) -> None:
    ensure_global()
    local = ensure_local()
    cwd = str(Path.cwd())
    note = (
        f"## {args.id} — revised\n"
        f"- **Revised**: {now()}\n"
        f"- **Note**: {args.note}\n\n"
    )
    with local.open("a") as f:
        f.write(note)
    with GLOBAL_INDEX.open("a") as f:
        f.write(
            f"## {args.id} — revised\n"
            f"- **Revised**: {now()}\n"
            f"- **Project**: `{cwd}`\n"
            f"- **Note**: {args.note}\n\n"
        )
    print(f"revision recorded for {args.id}")


def cmd_list(_args) -> None:
    p = Path.cwd() / LOCAL_INDEX_NAME
    if not p.exists():
        print("No documents.md in this project yet.")
        return
    sys.stdout.write(p.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("allocate", help="print next ID and bump counter")

    rec = sub.add_parser("record", help="record a new document")
    rec.add_argument("--id", required=True)
    rec.add_argument("--path", required=True)
    rec.add_argument("--keywords", required=True, help="comma-separated, 3-8 keywords")
    rec.add_argument("--summary", required=True, help="one sentence")
    rec.add_argument("--source", help="optional data/reference source")

    rev = sub.add_parser("revise", help="record a revision to an existing doc")
    rev.add_argument("--id", required=True)
    rev.add_argument("--note", required=True)

    sub.add_parser("list", help="print this project's documents.md")

    args = parser.parse_args()
    {
        "allocate": cmd_allocate,
        "record": cmd_record,
        "revise": cmd_revise,
        "list": cmd_list,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
