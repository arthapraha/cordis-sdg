#!/usr/bin/env python3
"""Registration section 6 item 2: the mapping table, over the whole snapshot.

    python scripts/build_mapping_table.py --freeze-seq 207 \
        --records data/corpus/records.jsonl \
        --out data/corpus/mapping-table.csv

Section 6 item 2 names the columns and this file carries every one of them:

  "project id, acronym, title, assigned SDG concept URIs and labels, confidence
  band, explanation, source fields and matched phrases, WHICH OF THE FIVE §3.4
  SOURCES WERE PRESENT FOR THE PROJECT, AS ITS OWN COLUMN, so a reader can tell a
  field that matched nothing from a field that was absent, overflow count,
  snapshot hash, pipeline commit, prompt hash."

IT CALLS THE FROZEN PIPELINE, IT DOES NOT REIMPLEMENT IT. `pipeline.run()` does
the scoring, with `pipeline.load_vocabulary()`, `load_crosswalk()` and
`load_negation()` supplying the rules. A second scorer written beside the first
would be a second set of rules that agree until they do not, and the whole point
of section 3 is that one set of rules decides. pipeline.py is not modified by
this file and its output `0938fe34…` still reproduces from `c8a6104`.

AND IT PASSES THE SAME GUARD. Registration section 4.3's four conditions are
checked here through `pipeline.freeze_conditions()` — the same function, not a
copy — because this run scores the evaluation 100 among the rest of the corpus.
A submission table built outside the freeze would be a way round the guard that
happens not to be called pipeline.py.

ONE ROW PER (PROJECT, ASSIGNED TARGET), which is section 4.7's unit, so a row
carries its own confidence band and its own evidence. A project with no
assignment still gets a row: the table covers the corpus, and a project missing
from it would be indistinguishable from a project the pipeline never saw.

NO EMPTY CELL, EVER. Owner's word at cordis-sdg seq 240. Where a value does not
exist, the cell says which rule leaves it empty rather than being blank. Two
columns are in that position for every row — see EXPLANATION_PARKED below — and
they are the only two.
"""

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pipeline
from repo_path import shown

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "data/terms/sdg-targets.csv"
MANIFEST = ROOT / "data/manifest.json"

# Section 3.7 writes the explanation and records its prompt's hash. It is PARKED:
# no model credential is set in this environment and section 9 forbids one in the
# repository or the room. The pass does not invent a key, substitute a provider,
# or write anything that pretends to be a model's work — so these two columns
# have no value to carry, on any row, and say so rather than being blank.
EXPLANATION_PARKED = (
    "(not generated: section 3.7's explanation pass is parked, no model "
    "credential in this environment, section 9 forbids one here)")
PROMPT_PARKED = "(no prompt: section 3.7 parked)"

NONE_ASSIGNED = "(no target assigned)"
GOAL_ONLY = "(goal level only, no target above threshold)"
NO_MATCH = "(no phrase matched)"

COLUMNS = [
    "project_id", "acronym", "title",
    "sdg_target_uri", "sdg_target_label", "sdg_goal_uri", "sdg_goal_label",
    "assignment_level", "confidence_band", "score",
    "explanation",
    "matched_phrases_and_source_fields",
    "sources_present", "sources_absent",
    "overflow_beyond_cap",
    "snapshot_sha256", "pipeline_commit", "prompt_sha256",
]


def taxonomy():
    with open(TARGETS, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    return {r["target_id"]: r for r in rows}


def snapshot_sha256():
    """One hash standing for the snapshot, and it is the manifest's.

    Section 6 item 2 says "snapshot hash", singular, and the snapshot is four
    CORDIS distributions plus the taxonomy — five hashes, not one. data/
    manifest.json is the committed record that carries all of them with their
    retrieval times, so its digest resolves to every one of them and to nothing
    else. Picking one distribution's hash instead would name a quarter of the
    data the rows came from.
    """
    return hashlib.sha256(MANIFEST.read_bytes()).hexdigest()


def pipeline_commit():
    """The commit of the frozen pipeline, read from git rather than written here.

    It is the commit that last touched scripts/pipeline.py, not HEAD: a row's
    provenance is the code that scored it, and HEAD moves every time a README
    changes. Refuses rather than guessing if git cannot answer.
    """
    r = subprocess.run(["git", "log", "-1", "--format=%H", "--",
                        "scripts/pipeline.py"],
                       cwd=str(ROOT), capture_output=True, text=True)
    commit = r.stdout.strip()
    if r.returncode != 0 or len(commit) != 40:
        sys.exit("refused: cannot read the pipeline's commit from git (%s). "
                 "Every row carries it under section 6 item 2 and a guessed "
                 "value is worse than none." % (r.stderr.strip()[:120] or "?"))
    dirty = subprocess.run(["git", "status", "--porcelain", "--",
                            "scripts/pipeline.py"],
                           cwd=str(ROOT), capture_output=True, text=True)
    if dirty.stdout.strip():
        sys.exit("refused: scripts/pipeline.py has uncommitted changes, so no "
                 "commit hash describes the code that would score these rows.")
    return commit


def evidence_cell(assignment):
    """Section 3.4's record: the exact phrase found, with its source field."""
    parts = []
    for e in assignment["evidence"]:
        if e["source"] == "lexical":
            parts.append("%s: \"%s\" [%s, %s]"
                         % (e["field"], e["phrase"], e["kind"], e["weight"]))
        else:
            parts.append("eurosciwoc_categories: %s [crosswalk %s, %s]"
                         % (e["category"], e["strength"], e["weight"]))
    return " | ".join(parts) if parts else NO_MATCH


def check_row(row):
    """Refuse a row with an empty cell, or a column the header does not have.

    THE FIRST VERSION OF rows_for() LEFT OUT `title` AND THE TABLE WROTE IT
    BLANK ON EVERY ROW. csv.DictWriter fills a missing key with the empty string
    and says nothing, so the defect was visible only by reading the output —
    which is how it was caught, on a 40-project test, and not by anything that
    could fail. The owner's word at cordis-sdg seq 240 is "no empty required
    cell"; this is that word as a check rather than as an intention.
    """
    missing = [k for k in COLUMNS if k not in row]
    if missing:
        raise AssertionError("row for %s has no value for %s"
                             % (row.get("project_id"), ", ".join(missing)))
    blank = [k for k in COLUMNS if str(row[k]).strip() == ""]
    if blank:
        raise AssertionError("row for %s has an empty cell in %s"
                             % (row.get("project_id"), ", ".join(blank)))
    extra = [k for k in row if k not in COLUMNS]
    if extra:
        raise AssertionError("row for %s carries %s, which is not a column"
                             % (row.get("project_id"), ", ".join(extra)))
    return row


def rows_for(result, record, tax, snap, commit):
    """`record` is the project as the pipeline read it; `result` is what it
    scored. The title is the project's and never the scorer's: pipeline.run()
    carries the acronym onto its rows and not the title, and reading
    result["title"] is how the first version of this wrote an empty column.
    """
    if record["id"] != result["id"]:
        raise AssertionError("record %s paired with result %s"
                             % (record["id"], result["id"]))
    base = {
        "project_id": result["id"],
        "acronym": result["acronym"],
        "title": record["title"],
        "sources_present": ", ".join(result["sources_present"]) or "(none of the five)",
        "sources_absent": ", ".join(result["sources_absent"]) or "(none absent)",
        "overflow_beyond_cap": result["overflow_beyond_cap"],
        "snapshot_sha256": snap,
        "pipeline_commit": commit,
        "explanation": EXPLANATION_PARKED,
        "prompt_sha256": PROMPT_PARKED,
    }
    out = []
    if result["assignments"]:
        for a in result["assignments"]:
            t = tax[a["target_id"]]
            out.append(dict(base,
                            sdg_target_uri=a["target_uri"],
                            sdg_target_label=t["target_label"],
                            sdg_goal_uri=a["goal_uri"],
                            sdg_goal_label=t["goal_label"],
                            assignment_level="target",
                            confidence_band=a["confidence"] or "(none: score "
                                            "below every band's minimum)",
                            score=a["score"],
                            matched_phrases_and_source_fields=evidence_cell(a)))
    elif result["goal_level_only"]:
        for g in result["goal_level_only"]:
            any_t = next(v for v in tax.values() if v["goal_id"] == g["goal_id"])
            out.append(dict(base,
                            sdg_target_uri=GOAL_ONLY,
                            sdg_target_label=GOAL_ONLY,
                            sdg_goal_uri=g["goal_uri"],
                            sdg_goal_label=any_t["goal_label"],
                            assignment_level="goal_only",
                            confidence_band="(not banded: section 3.6 bands "
                                            "target assignments)",
                            score=g["score"],
                            matched_phrases_and_source_fields=(
                                "(evidence summed by goal, below the target "
                                "threshold)")))
    else:
        out.append(dict(base,
                        sdg_target_uri=NONE_ASSIGNED,
                        sdg_target_label=NONE_ASSIGNED,
                        sdg_goal_uri=NONE_ASSIGNED,
                        sdg_goal_label=NONE_ASSIGNED,
                        assignment_level="none",
                        confidence_band=NONE_ASSIGNED,
                        score=0,
                        matched_phrases_and_source_fields=NO_MATCH))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="data/corpus/records.jsonl")
    ap.add_argument("--out", default="data/corpus/mapping-table.csv")
    ap.add_argument("--freeze-seq", type=int, required=True)
    ap.add_argument("--chunk", type=int, default=250)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    params = json.loads(pipeline.PARAMS.read_text(encoding="utf-8"))
    records_path = ROOT / args.records

    # THE SAME FOUR CONDITIONS, THROUGH THE SAME FUNCTION. This run scores the
    # evaluation 100 among the corpus, so it is subject to section 4.3 exactly as
    # pipeline.py's own main() is. Loading happens first so condition 4 can see
    # what was opened, as it does there.
    vocab, stop = pipeline.load_vocabulary()
    crosswalk = pipeline.load_crosswalk()
    patterns = pipeline.load_negation()
    loaded = frozenset(pipeline.OPENED)
    failures = pipeline.freeze_conditions(params, args.freeze_seq,
                                          str(records_path), loaded)
    if failures:
        sys.exit("refused: %d of registration section 4.3's four conditions did "
                 "not hold.\n\n  %s" % (len(failures), "\n\n  ".join(failures)))

    tax = taxonomy()
    snap = snapshot_sha256()
    commit = pipeline_commit()

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.is_file():
        # Resume. A nine-hour pass that cannot be resumed is a pass that gets
        # restarted from zero the first time anything interrupts it.
        with open(out, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                done.add(row["project_id"])
        print("resuming: %d projects already written" % len(done))

    # utf-8-sig: Excel reads a UTF-8 CSV as the system codepage unless the file
    # carries a BOM, and these titles are full of accented characters. The word
    # at seq 240 is that it opens in a spreadsheet.
    mode = "a" if done else "w"
    fh = open(out, mode, encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
    if not done:
        writer.writeheader()

    batch, scored, written, t0 = [], 0, 0, time.time()

    def flush():
        nonlocal batch, scored, written
        if not batch:
            return
        results = pipeline.run(batch, vocab, stop, crosswalk, patterns, params)
        if len(results) != len(batch):
            raise AssertionError("scored %d of %d records" % (len(results), len(batch)))
        for rec, r in zip(batch, results):
            for row in rows_for(r, rec, tax, snap, commit):
                writer.writerow(check_row(row))
                written += 1
        scored += len(batch)
        fh.flush()
        rate = scored / max(time.time() - t0, 0.001)
        print("  scored %6d  rows %7d  %.1f/s  eta %.0f min"
              % (scored, written, rate, (total - scored) / max(rate, 0.001) / 60),
              flush=True)
        batch = []

    total = 0
    with open(records_path, encoding="utf-8") as rf:
        for line in rf:
            rec = json.loads(line)
            if rec["id"] in done:
                continue
            total += 1
    print("to score: %d projects" % total)

    with open(records_path, encoding="utf-8") as rf:
        for i, line in enumerate(rf):
            if args.limit and i >= args.limit:
                break
            rec = json.loads(line)
            if rec["id"] in done:
                continue
            batch.append(rec)
            if len(batch) >= args.chunk:
                flush()
    flush()
    fh.close()

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print()
    print("wrote %s  %.1f MB" % (shown(out, ROOT), out.stat().st_size / 1048576))
    print("  sha256          ", digest)
    print("  projects scored ", scored)
    print("  rows            ", written)
    print("  pipeline commit ", commit)
    print("  snapshot sha256 ", snap)


if __name__ == "__main__":
    main()
