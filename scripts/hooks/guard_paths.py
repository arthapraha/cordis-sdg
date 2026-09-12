#!/usr/bin/env python3
"""Refuse a write to snapshot payload or to anything credential-shaped.

Authorised by the owner in cordis-sdg at seq 157, on counsel's advice at seq 155.

TWO THINGS MUST NEVER ENTER THIS REPOSITORY AND TODAY BOTH REST ON .gitignore,
which is a file anyone can edit and which nothing enforces at the moment of
writing.

data/raw/ is 180 MB of snapshot payload. It is deliberately uncommitted: the
manifest carries a sha256 for every file so a re-download is verifiable byte for
byte without carrying the bytes in git history. A single accidental write there
is not a mistake anyone notices in a diff.

Registration section 9: "No credentials in the repo or the room. Keys are read by
name from the environment." The explanation pass is parked for want of a key, so
a key is a thing someone will soon be holding, and the moment of most risk is the
moment it arrives.

This fails CLOSED: anything it cannot parse is allowed through rather than
blocked, but any path it does recognise as forbidden is refused. It guards the
write, not the commit, because by commit time the bytes are already on disk.
"""

import json
import pathlib
import sys

FORBIDDEN_DIRS = ["data/raw/"]
FORBIDDEN_NAMES = {".env", ".envrc", "credentials", "credentials.json",
                   "secrets.json", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}


def verdict(path_text):
    if not path_text:
        return None
    p = pathlib.PurePath(path_text).as_posix()
    low = p.lower()
    for d in FORBIDDEN_DIRS:
        if d in low:
            return ("%s is snapshot payload. It is uncommitted on purpose: "
                    "data/manifest.json carries a sha256 for every file so a "
                    "re-download is verifiable without 180 MB in git history. "
                    "Write it by re-running the fetch, not by hand." % d.rstrip("/"))
    name = pathlib.PurePath(p).name.lower()
    if name in FORBIDDEN_NAMES or pathlib.PurePath(name).suffix in FORBIDDEN_SUFFIXES:
        return ("registration section 9: no credentials in the repository or the "
                "room. Keys are read by name from the environment.")
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool_input = payload.get("tool_input") or {}
    # Write and Edit both carry file_path; NotebookEdit uses notebook_path.
    for key in ("file_path", "notebook_path", "path"):
        why = verdict(tool_input.get(key))
        if why:
            print("refused: %s\n  %s" % (tool_input.get(key), why),
                  file=sys.stderr)
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
