#!/usr/bin/env python3
"""The seq 244 control: did the substring skip change any byte of the mapping table?

    python scripts/compare_control_table.py --control PATH/TO/control-table.csv

THE CONDITION. `pipeline.py` skips the regex for a vocabulary phrase that is not
a plain substring of the text, which took the corpus build from about ten hours
to minutes. The owner let that into the frozen pipeline at cordis-sdg seq 244 on
one condition: the output must equal the slow run's. The slow run is the pipeline
at c8a6104, before the skip; the committed table is 0246412, after it. The
control table is not committed, being a 24 MB second copy of the same result, so
this script takes its path.

TWO INSTRUMENTS, BECAUSE EACH COVERS THE OTHER'S BLIND SPOT.

1. A differential on every column but `pipeline_commit`, paired on (project,
   target, level) and SCOPED BY RUN ORDER. The build scores records.jsonl from
   top to bottom, so every project up to the last one the control wrote must be
   present. The first version scoped to the projects the control CONTAINED, and
   a project the control had lost vanished from both sides: dropping a
   single-row project passed. Scoping by run order is what makes a lost project
   a difference.

2. A byte comparison. The two runs are two commits, so `pipeline_commit` differs
   by construction and nothing else should. Both hashes are 40 characters, so
   substituting one for the other preserves every offset. If the control, with
   its commit swapped, equals the committed table over the same scope byte for
   byte, the files are identical in every other byte. The swap cannot hide a
   difference: each commit must occur exactly once per row in its own file and
   never in the other.

   ON A PARTIAL CONTROL the byte comparison is made against the committed
   table's matching PREFIX, not the whole file. The first version compared a
   partial control with the whole table, so every partial run was reported as
   "the skip changed the output" — a false accusation, caught by running this
   script on a 300-project rebuild before it was committed. The prefix is exact
   only because both tables are written in records order with no newline inside
   any field; both properties are asserted, and the script refuses if either
   fails rather than slicing on an assumption.

BOTH REFUSE TO REPORT UNTIL THEY HAVE FAILED ON PURPOSE, AND THE FAILURES ARE
SHOWN TO MEAN SOMETHING. The negative controls re-serialise perturbed rows. That
proves nothing unless re-serialising UNTOUCHED rows passes, because otherwise the
serialiser itself would make every perturbation "detected". So the untouched
re-serialisation must pass first, and then a moved score, a moved band, a dropped
single-row project and a changed byte must each be caught.
"""

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLOW_COMMIT = "c8a610477bc170817c20e0432bd197dec62c52c8"
FAST_COMMIT = "0246412b44f722567feaa2e6c1b6e695de86c923"
EXCLUDED = "pipeline_commit"


def rows_of(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline="")))


def as_bytes(rows, cols):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def prefix(data, data_rows):
    """The header plus the first `data_rows` rows, as the original bytes.

    Exact only when no field contains a newline, which main() asserts.
    """
    end = -1
    for _ in range(data_rows + 1):
        end = data.index(b"\n", end + 1)
    return data[:end + 1]


def differential(control_rows, committed_rows, order):
    """Differences, scoped to every project in run order up to the control's last."""
    pos = {pid: i for i, pid in enumerate(order)}
    written = {r["project_id"] for r in control_rows}
    if written - set(pos):
        return {"unknown_projects": len(written - set(pos))}
    last = max(pos[p] for p in written)
    scope = set(order[:last + 1])
    theirs = [r for r in committed_rows if r["project_id"] in scope]

    key = lambda r: (r["project_id"], r["sdg_target_uri"], r["assignment_level"])
    a = {key(r): r for r in control_rows}
    b = {key(r): r for r in theirs}
    if len(a) != len(control_rows) or len(b) != len(theirs):
        return {"keys_not_unique": 1}

    both = set(a) & set(b)
    cols = [c for c in control_rows[0] if c != EXCLUDED]
    return {
        "scope_projects": len(scope),
        "control_rows": len(control_rows),
        "committed_rows_in_scope": len(theirs),
        "projects_missing": len(scope - written),
        "rows_only_control": len(set(a) - set(b)),
        "rows_only_committed": len(set(b) - set(a)),
        "rows_score_or_band_differs": sum(
            1 for k in both
            if a[k]["score"] != b[k]["score"]
            or a[k]["confidence_band"] != b[k]["confidence_band"]),
        "cells_differing": sum(1 for k in both for c in cols if a[k][c] != b[k][c]),
    }


INFORMATIONAL = ("scope_projects", "control_rows", "committed_rows_in_scope")


def clean(result):
    return "projects_missing" in result and not any(
        v for k, v in result.items() if k not in INFORMATIONAL)


def substitution(control_bytes, committed_scope_bytes):
    """Swap the control's commit for the committed table's; compare byte for byte.

    `committed_scope_bytes` is the committed table over the same scope as the
    control: the whole file for a complete run, its matching prefix otherwise.
    """
    slow, fast = SLOW_COMMIT.encode(), FAST_COMMIT.encode()
    control_rows = control_bytes.count(b"\n") - 1
    committed_rows = committed_scope_bytes.count(b"\n") - 1
    counts_ok = (control_bytes.count(slow) == control_rows and control_bytes.count(fast) == 0
                 and committed_scope_bytes.count(fast) == committed_rows
                 and committed_scope_bytes.count(slow) == 0)
    swapped = control_bytes.replace(slow, fast)
    return counts_ok, hashlib.sha256(swapped).hexdigest(), swapped == committed_scope_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True,
                    help="the slow run's table, built at c8a6104; not committed")
    ap.add_argument("--committed", default="data/corpus/mapping-table-0246412.csv")
    ap.add_argument("--records", default="data/corpus/records.jsonl")
    args = ap.parse_args()

    control_p = pathlib.Path(args.control)
    committed_p = ROOT / args.committed
    records_p = ROOT / args.records
    for p in (control_p, committed_p):
        if not p.is_file():
            sys.exit("missing: %s" % p)
    if not records_p.is_file():
        sys.exit("missing: %s, which .gitignore keeps out of the repository.\n"
                 "Rebuild it first:\n"
                 "    python scripts/build_corpus_records.py --out data/corpus/records.jsonl"
                 % args.records)

    control_bytes = control_p.read_bytes()
    committed_bytes = committed_p.read_bytes()
    if not control_bytes.endswith(b"\n"):
        sys.exit("refused: the control table ends mid-line, so it is still being written")
    order = [json.loads(line)["id"] for line in open(records_p, encoding="utf-8")]
    pos = {pid: i for i, pid in enumerate(order)}
    control = rows_of(control_bytes)
    committed = rows_of(committed_bytes)
    cols = list(control[0])

    stamps = {r[EXCLUDED] for r in control}, {r[EXCLUDED] for r in committed}
    if stamps != ({SLOW_COMMIT}, {FAST_COMMIT}):
        sys.exit("refused: expected the control stamped only %s and the committed table "
                 "only %s, found %s and %s. This is not the seq 244 control."
                 % (SLOW_COMMIT[:12], FAST_COMMIT[:12],
                    sorted(s[:12] for s in stamps[0]), sorted(s[:12] for s in stamps[1])))

    # The two properties the prefix slice rests on, checked rather than assumed.
    for name, data, rows in (("control", control_bytes, control),
                             ("committed", committed_bytes, committed)):
        if data.count(b"\n") != len(rows) + 1:
            sys.exit("refused: the %s table has a newline inside a field, so a row "
                     "prefix cannot be sliced by line" % name)
        seq = [pos.get(r["project_id"], -1) for r in rows]
        if -1 in seq or any(x > y for x, y in zip(seq, seq[1:])):
            sys.exit("refused: the %s table is not in records order, so its prefix "
                     "is not the scope the control covers" % name)

    # ---- positive control: re-serialising untouched rows must pass ------------
    rebuilt = as_bytes(control, cols)
    scope_rows = differential(control, committed, order).get("committed_rows_in_scope", -1)
    committed_scope = committed_bytes if scope_rows == len(committed) else prefix(committed_bytes, scope_rows)
    print("positive control, the untouched control re-serialised:")
    print("   reproduces the control's bytes:  %s" % (rebuilt == control_bytes))
    print("   passes the substitution:         %s" % substitution(rebuilt, committed_scope)[2])
    if rebuilt != control_bytes:
        sys.exit("refused: re-serialising untouched rows changes the bytes, so the "
                 "negative controls below would be caught by the serialiser, not the check")

    # ---- negative controls: each must be detected ----------------------------
    per_project = {}
    for r in control:
        per_project[r["project_id"]] = per_project.get(r["project_id"], 0) + 1
    i_high = next(i for i, r in enumerate(control) if r["confidence_band"] == "high")
    i_single = next(i for i, r in enumerate(control) if per_project[r["project_id"]] == 1)

    moved_score = [dict(r) for r in control]
    moved_score[i_high]["score"] = str(float(moved_score[i_high]["score"]) + 0.5)
    moved_band = [dict(r) for r in control]
    moved_band[i_high]["confidence_band"] = "low"
    dropped = [dict(r) for i, r in enumerate(control) if i != i_single]
    one_byte = bytearray(control_bytes)
    j = control_bytes.index(b"\n", len(control_bytes) // 2) - 3
    one_byte[j] = ord("9") if one_byte[j] != ord("9") else ord("8")

    print("negative controls, each must be detected:")
    for what, perturbed in [("a score moved", moved_score),
                            ("a band moved high to low", moved_band),
                            ("a single-row project dropped", dropped)]:
        caught = not clean(differential(perturbed, committed, order))
        bytes_caught = not substitution(as_bytes(perturbed, cols), committed_scope)[2]
        print("   %-30s differential %-8s substitution %s"
              % (what, "caught" if caught else "MISSED", "caught" if bytes_caught else "MISSED"))
        if not (caught and bytes_caught):
            sys.exit("refused: an instrument missed a planted difference")
    byte_caught = not substitution(bytes(one_byte), committed_scope)[2]
    print("   %-30s substitution %s" % ("one byte changed", "caught" if byte_caught else "MISSED"))
    if not byte_caught:
        sys.exit("refused: the substitution missed a changed byte")
    print()

    # ---- the result -------------------------------------------------------------
    result = differential(control, committed, order)
    counts_ok, swapped_sha, identical = substitution(control_bytes, committed_scope)
    whole = result.get("scope_projects") == len(order)
    print("control table    sha256 %s  %d bytes" % (hashlib.sha256(control_bytes).hexdigest(), len(control_bytes)))
    print("committed table  sha256 %s  %d bytes" % (hashlib.sha256(committed_bytes).hexdigest(), len(committed_bytes)))
    print("compared over    %s" % ("the whole committed table" if whole else
                                   "the committed table's first %d rows, the control's scope" % scope_rows))
    print("projects in records order: %d" % len(order))
    for k, v in result.items():
        print("   %-28s %d" % (k, v))
    print("each commit once per row in its own file, never in the other: %s" % counts_ok)
    print("control with its commit swapped  sha256 %s" % swapped_sha)
    print("byte-identical apart from pipeline_commit: %s" % identical)

    if not (clean(result) and counts_ok and identical):
        sys.exit("DIFFERENT: the substring skip changed the output")
    print()
    print("IDENTICAL over %s. The condition at cordis-sdg seq 244 holds%s."
          % ("the whole corpus" if whole else "the first %d projects in run order"
             % result["scope_projects"],
             "" if whole else " for that range only; the control run is not complete"))


if __name__ == "__main__":
    main()
