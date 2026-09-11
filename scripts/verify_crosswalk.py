#!/usr/bin/env python3
"""Check the committed crosswalk, synonym list and key terms against their sources.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
sections 3.1 to 3.3. This is the check that a reader can run to see that the
three load-bearing artefacts are internally consistent and that every identifier
in them is real:

  * every crosswalk target_id exists in the taxonomy snapshot;
  * every crosswalk eurosciwoc_path exists in the projects snapshot, compared
    after stripping surrounding whitespace from both sides (see WHITESPACE
    below);
  * every crosswalk row carries a justification;
  * every synonym target_id exists in the taxonomy, with no duplicate pairs;
  * every key-term target_id exists in the taxonomy;
  * every target is reachable by at least one key term or synonym.

Exits non-zero if any check fails. It reads no project text beyond the EuroSciVoc
category vocabulary, which is the crosswalk's own left-hand side.

WHITESPACE. Exactly one of the 1,007 category paths in this snapshot carries a
trailing space: "engineering and technology/medical engineering/wearable medical
technology ". It is CORDIS's own spelling, not a parsing artefact of ours. The
crosswalk stores the clean spelling and every comparison against the snapshot
strips surrounding whitespace on both sides, rather than embedding an invisible
character in a committed CSV where no reader could see it and any editor would
silently remove it. The same normalisation must be applied wherever the crosswalk
is joined to project rows, or the join will miss that category. This is recorded
here because a defect in source data that is invisible on screen is exactly the
kind that survives review.
"""

import collections
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "data/terms/sdg-targets.csv"
KEYTERMS = ROOT / "data/terms/target-key-terms.csv"
SYNONYMS = ROOT / "data/terms/synonyms.csv"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
EUROSCIVOC = ROOT / "data/raw/cordis-horizon-projects/euroSciVoc.csv"

STRENGTHS = {"direct", "contributing"}


def read(path):
    if not path.is_file():
        sys.exit("missing: %s" % path.relative_to(ROOT))
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def categories():
    csv.field_size_limit(1 << 30)
    if not EUROSCIVOC.is_file():
        sys.exit("missing EuroSciVoc extract: %s" % EUROSCIVOC.relative_to(ROOT))
    with open(EUROSCIVOC, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        header = next(r)
        i = header.index("euroSciVocPath")
        return {row[i].strip() for row in r if len(row) == len(header) and row[i].strip()}


def main():
    failures = []
    notes = []

    targets = read(TARGETS)
    target_ids = {t["target_id"] for t in targets}
    goals = {t["goal_id"] for t in targets}

    # --- crosswalk -------------------------------------------------------
    cross = read(CROSSWALK)
    paths = categories()
    bad_target = sorted({r["eurosciwoc_path"] + " -> " + r["target_id"]
                         for r in cross if r["target_id"] not in target_ids})
    bad_path = sorted({r["eurosciwoc_path"] for r in cross
                       if r["eurosciwoc_path"].strip() not in paths})
    bad_strength = sorted({r["strength"] for r in cross
                           if r["strength"] not in STRENGTHS})
    no_just = [r for r in cross if len(r["justification"].strip()) < 20]
    dupes = [k for k, v in collections.Counter(
        (r["eurosciwoc_path"], r["target_id"]) for r in cross).items() if v > 1]

    if bad_target:
        failures.append("crosswalk rows naming a target not in the taxonomy: %s" % bad_target)
    if bad_path:
        failures.append("crosswalk rows naming a EuroSciVoc path absent from the snapshot: %s" % bad_path)
    if bad_strength:
        failures.append("crosswalk rows with an unknown strength: %s" % bad_strength)
    if no_just:
        failures.append("crosswalk rows with no real justification: %d" % len(no_just))
    if dupes:
        failures.append("duplicate (category, target) pairs in the crosswalk: %s" % dupes)

    # --- synonyms --------------------------------------------------------
    syn = read(SYNONYMS)
    bad_syn = sorted({r["target_id"] for r in syn if r["target_id"] not in target_ids})
    syn_dupes = [k for k, v in collections.Counter(
        (r["target_id"], r["synonym"].strip().lower()) for r in syn).items() if v > 1]
    syn_blank = [r for r in syn if not r["synonym"].strip() or not r["note"].strip()]
    if bad_syn:
        failures.append("synonyms naming a target not in the taxonomy: %s" % bad_syn)
    if syn_dupes:
        failures.append("duplicate (target, synonym) pairs: %s" % syn_dupes)
    if syn_blank:
        failures.append("synonym rows with no synonym or no note: %d" % len(syn_blank))

    # --- key terms -------------------------------------------------------
    kt = read(KEYTERMS)
    bad_kt = sorted({r["target_id"] for r in kt if r["target_id"] not in target_ids})
    if bad_kt:
        failures.append("key terms naming a target not in the taxonomy: %s" % bad_kt)

    # A TERM THAT MATCHES EVERYTHING IS WORSE THAN NO TERM, and until now this
    # file checked only that identifiers were real. Two passes reproduced the
    # vocabulary byte for byte and neither saw that target 12.3's terms were
    # "2030" and "d", or that target 3.b's was "and" (cordis-sdg seq 103, 106).
    # A reproducibility check is not a content check. These are the content
    # checks, mechanical so they do not depend on someone reading 859 terms.
    import extract_key_terms  # the committed step-5 list, not a second copy
    junk = collections.defaultdict(list)
    for r in kt:
        term = r["term"]
        words = term.split()
        if all(w.isdigit() for w in words):
            junk["a bare number"].append((r["target_id"], term))
        elif len(words) == 1 and words[0] in extract_key_terms.EDGE_WORDS:
            junk["a single function word"].append((r["target_id"], term))
        elif len(term) < 3:
            junk["shorter than three characters"].append((r["target_id"], term))
    for why, items in sorted(junk.items()):
        failures.append("key terms that are %s: %s" % (why, sorted(set(items))))

    # --- reachability ----------------------------------------------------
    reachable = {r["target_id"] for r in kt} | {r["target_id"] for r in syn}
    unreachable = sorted(target_ids - reachable)
    if unreachable:
        failures.append("targets reachable by neither a key term nor a synonym: %s" % unreachable)

    kt_only = sorted(target_ids - {r["target_id"] for r in syn})
    syn_only = sorted(target_ids - {r["target_id"] for r in kt})
    if syn_only:
        notes.append("targets with NO key term, reachable only through synonyms: %s" % syn_only)
    if kt_only:
        notes.append("targets with no synonym, reachable only through key terms: %s" % kt_only)

    # --- report ----------------------------------------------------------
    cross_targets = {r["target_id"] for r in cross}
    cross_goals = {r["target_id"].split(".")[0] for r in cross}
    print("targets in the taxonomy        %d over %d goals" % (len(target_ids), len(goals)))
    print("key terms                      %d rows, %d distinct terms, %d targets"
          % (len(kt), len({r["term"] for r in kt}), len({r["target_id"] for r in kt})))
    print("synonyms                       %d rows, %d distinct, %d targets"
          % (len(syn), len({r["synonym"].lower() for r in syn}), len({r["target_id"] for r in syn})))
    print("crosswalk                      %d rows, %d categories, %d targets, %d goals"
          % (len(cross), len({r["eurosciwoc_path"] for r in cross}),
             len(cross_targets), len(cross_goals)))
    print("  of which direct              %d" % sum(1 for r in cross if r["strength"] == "direct"))
    print("  of which contributing        %d" % sum(1 for r in cross if r["strength"] == "contributing"))
    print("EuroSciVoc categories in snapshot %d; mapped by the crosswalk %d (%.1f%%)"
          % (len(paths), len({r["eurosciwoc_path"] for r in cross}),
             100.0 * len({r["eurosciwoc_path"] for r in cross}) / len(paths)))
    print("goals with no crosswalk row:", sorted(goals - cross_goals, key=int) or "none")
    for n in notes:
        print("note:", n)

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("All checks passed.")


if __name__ == "__main__":
    main()
