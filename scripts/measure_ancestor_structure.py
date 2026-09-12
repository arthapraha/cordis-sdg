#!/usr/bin/env python3
"""t-63ab: is the zero luck, or is it structural? Ask the corpus records.

    python scripts/build_corpus_records.py --out data/corpus/records.jsonl
    python scripts/measure_ancestor_structure.py

`measure_ancestor_exposure.py` finds no inflated row in the committed mapping
table. That on its own does not say whether the defect is harmless or merely
dormant, and the two call for different responses. This script asks the question
that separates them: does ANY project in the snapshot carry a EuroSciVoc category
together with one of its own descendants?

WHY THE INPUT IS NOT IN THE REPOSITORY. `data/corpus/records.jsonl` is 150 MB of
regenerated snapshot text and `.gitignore` keeps it out, so a fresh clone must
rebuild it with the line above. Its sha256 is pinned below rather than read from
a manifest beside it, which is also not committed: pinning it here is what lets
this script say whether it is measuring the input the limitation describes or a
different one.

IT CARRIES A POSITIVE CONTROL AND WILL NOT REPORT WITHOUT IT. The headline is a
zero, and a zero from an instrument nobody has watched find anything is
indistinguishable from an instrument that cannot find anything. Counsel caught
that this was missing at cordis-sdg seq 365. A planted ancestor pair must be
detected by both tests before either is allowed to read a real record.
"""

import collections
import csv
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORDS = ROOT / "data/corpus/records.jsonl"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"

# The records file the documented zero was measured on, 23,451 projects.
RECORDS_SHA256 = "25ab5de2be232dbcc839a53ed7adf60ef684d845190bc0e4c2bca9bef06ad840"
ABSENT = "(absent)"


def main():
    if not CROSSWALK.is_file():
        sys.exit("missing: %s" % CROSSWALK.relative_to(ROOT))
    if not RECORDS.is_file():
        sys.exit("missing: data/corpus/records.jsonl, which .gitignore keeps out of "
                 "the repository.\nRebuild it first:\n"
                 "    python scripts/build_corpus_records.py --out data/corpus/records.jsonl")

    cross = collections.defaultdict(list)
    with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            cross[row["eurosciwoc_path"].strip()].append((row["target_id"], row["strength"]))

    paths = sorted(cross)
    pairset = set()
    for a in paths:
        for b in paths:
            if b.startswith(a + "/") and ({t for t, _ in cross[a]} & {t for t, _ in cross[b]}):
                pairset.add((a, b))
    print("crosswalk ancestor pairs sharing a target: %d" % len(pairset))

    def carries_any_descendant(cats):
        return any(b.startswith(a + "/") for a in cats for b in cats if a != b)

    def carries_crosswalk_pair(cats):
        return any((a, b) in pairset for a in cats for b in cats)

    # ---- the positive control, before a single real record is read -----------
    planted_parent, planted_child = sorted(pairset)[0]
    planted = [planted_parent, planted_child, "natural sciences/mathematics"]
    fired_any = carries_any_descendant(planted)
    fired_pair = carries_crosswalk_pair(planted)
    print()
    print("positive control: a synthetic record carrying")
    print("   %s" % planted_parent)
    print("   %s" % planted_child)
    print("   general descendant test fires: %s" % fired_any)
    print("   crosswalk-pair test fires:     %s" % fired_pair)
    if not (fired_any and fired_pair):
        sys.exit("refused: the tests do not detect a planted ancestor pair, so the "
                 "zero they would report measures nothing.")
    print()

    digest = hashlib.sha256(RECORDS.read_bytes()).hexdigest()
    print("records read:  data/corpus/records.jsonl")
    print("  sha256       %s" % digest)
    if digest == RECORDS_SHA256:
        print("  this is the snapshot docs/limitations.md section 1.6 describes")
    else:
        print("  DIFFERENT INPUT: section 1.6's zero was measured on")
        print("               %s" % RECORDS_SHA256)
        print("  The figures below describe this file, not that one. That is the")
        print("  point of re-running it; say which input a new figure came from.")
    print()

    projects = with_categories = multi = any_descendant = crosswalk_pair = 0
    examples = []
    with open(RECORDS, encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            projects += 1
            cats = record.get("eurosciwoc_categories")
            if cats == ABSENT or not cats:
                continue
            cats = [c.strip() for c in cats]
            with_categories += 1
            if len(cats) > 1:
                multi += 1
            if carries_any_descendant(cats):
                any_descendant += 1
                if len(examples) < 5:
                    examples.append((record["id"], cats))
            if carries_crosswalk_pair(cats):
                crosswalk_pair += 1

    print("projects in the records                                    %d" % projects)
    print("  carrying a category list                                 %d" % with_categories)
    print("  carrying more than one category                          %d" % multi)
    print("  carrying a category AND one of its own descendants       %d" % any_descendant)
    print("  carrying a crosswalk ancestor pair sharing a target      %d" % crosswalk_pair)
    for project, cats in examples:
        print("      %s %s" % (project, cats))

    if any_descendant == 0:
        print()
        print("CORDIS classifies with the most specific term in a branch and does not")
        print("also list its ancestors, so score()'s missing guard cannot fire on this")
        print("snapshot. The safety belongs to the upstream data, not to our rule:")
        print("a snapshot that listed a parent beside its child would double count")
        print("silently, and nothing in the pipeline would say so.")


if __name__ == "__main__":
    main()
