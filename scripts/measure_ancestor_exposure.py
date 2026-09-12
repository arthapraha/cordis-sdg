#!/usr/bin/env python3
"""t-63ab: what parent/child crosswalk rows actually did to the committed table.

    python scripts/measure_ancestor_exposure.py

WHAT THE DEFECT IS. `pipeline.py` score() walks every EuroSciVoc category on a
project and every crosswalk row for it, adding each row's weight to that target.
A project carrying a category AND one of its descendants, where both map to the
same target, therefore scores that target twice from one classification. Only
`contributing` rows are deduplicated ("a contributing row counts at most once per
target"); a `direct` row paired with anything still sums.

WHAT THIS SCRIPT REPORTS. The (project, target) pairs in the committed mapping
table where an ancestor and its descendant both contributed, and what removing
the ancestor's weight would do to the band. Owner's word at cordis-sdg seq 361
asked for the count and the largest band change; the ruling at seq 369 was to
document rather than re-freeze, and this is the re-runnable half of that record.

IT PROVES ITS PARSER BEFORE IT REPORTS ANYTHING. Every target row's score and
band are rebuilt from that row's own evidence cell and compared with the
committed columns. If a single row disagrees the script refuses, because an
exposure figure computed by a parser that cannot reproduce the artefact is a
number with nothing behind it.

The companion script `measure_ancestor_structure.py` asks the other half: whether
any project in the corpus carries such a pair at all.
"""

import collections
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TABLE = ROOT / "data/corpus/mapping-table-0246412.csv"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
PARAMS = ROOT / "data/pipeline/parameters-v1.json"

EVIDENCE_ITEM = re.compile(r"^([a-z_]+): (.*?) \[(.+?), (-?[0-9.]+)\]$")


def crosswalk_rows():
    """path -> [(target_id, strength)], read with the same delimiter as the pipeline."""
    out = collections.defaultdict(list)
    with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            out[row["eurosciwoc_path"].strip()].append((row["target_id"], row["strength"]))
    return out


def ancestor_pairs(cross):
    """Pairs (target, ancestor, descendant, strengths) reaching the SAME target.

    Ancestry is a proper path prefix at a "/" boundary, so "energy and fuels" is
    an ancestor of "energy and fuels/fuel cells" and NOT of "energy and fuelsX".
    """
    paths = sorted(cross)
    pairs = []
    for a in paths:
        for b in paths:
            if not b.startswith(a + "/"):
                continue
            for target in sorted({t for t, _ in cross[a]} & {t for t, _ in cross[b]}):
                sa = sorted({s for t, s in cross[a] if t == target})[0]
                sb = sorted({s for t, s in cross[b] if t == target})[0]
                pairs.append((target, a, b, sa, sb))
    return pairs


def band(score_value, sources, params):
    """pipeline.py's rule, restated here so this script does not import the frozen code."""
    for name in ("high", "medium", "low"):
        rule = params["confidence_bands"][name]
        if score_value >= rule["min_score"] and sources >= rule["min_independent_sources"]:
            return name
    return None


def evidence(cell):
    """The evidence cell as items, or None for any part that does not parse."""
    out = []
    for part in cell.split(" | "):
        hit = EVIDENCE_ITEM.match(part.strip())
        out.append(None if hit is None else {
            "field": hit.group(1), "what": hit.group(2),
            "kind": hit.group(3), "weight": float(hit.group(4))})
    return out


def main():
    for path in (TABLE, CROSSWALK, PARAMS):
        if not path.is_file():
            sys.exit("missing: %s" % path.relative_to(ROOT))

    params = json.loads(PARAMS.read_text(encoding="utf-8"))
    threshold = params["assignment"]["threshold"]
    cross = crosswalk_rows()
    pairs = ancestor_pairs(cross)

    kinds = collections.Counter((p[3], p[4]) for p in pairs)
    deduped = kinds[("contributing", "contributing")]
    summable = len(pairs) - deduped

    print("crosswalk paths                                  %d" % len(cross))
    print("ancestor pairs reaching the same target          %d, over %d targets"
          % (len(pairs), len({p[0] for p in pairs})))
    print("  already neutralised (contributing+contributing) %d" % deduped)
    print("  WOULD SUM if a project carried both             %d" % summable)
    for key in sorted(kinds):
        print("      %-28s %d" % ("%s + %s" % key, kinds[key]))
    print()

    by_target = collections.defaultdict(set)
    for target, a, b, _, _ in pairs:
        by_target[target].add((a, b))

    rows = score_ok = band_ok = 0
    disagreements = []
    exposed = []
    with open(TABLE, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["assignment_level"] != "target":
                continue
            rows += 1
            items = evidence(row["matched_phrases_and_source_fields"])
            if any(i is None for i in items):
                disagreements.append((row["project_id"], "evidence cell did not parse"))
                continue

            recorded = round(float(row["score"]), 3)
            rebuilt = round(sum(i["weight"] for i in items), 3)
            fields = {i["field"] for i in items}
            if abs(rebuilt - recorded) < 0.0005:
                score_ok += 1
            else:
                disagreements.append((row["project_id"],
                                      "score %s, rebuilt %s" % (recorded, rebuilt)))
            if band(recorded, len(fields), params) == row["confidence_band"]:
                band_ok += 1
            else:
                disagreements.append((row["project_id"], "band %s, rebuilt %s"
                                      % (row["confidence_band"],
                                         band(recorded, len(fields), params))))

            target = row["sdg_target_uri"].rsplit("/", 1)[-1]
            cats = {i["what"]: i for i in items if i["field"] == "eurosciwoc_categories"}
            for a, b in by_target.get(target, ()):
                if a in cats and b in cats:
                    new_score = round(recorded - cats[a]["weight"], 3)
                    exposed.append({
                        "project": row["project_id"], "target": target,
                        "ancestor": a, "descendant": b,
                        "score": recorded, "new_score": new_score,
                        "band": row["confidence_band"],
                        "new_band": (band(new_score, len(fields), params)
                                     if new_score >= threshold
                                     else "(not assigned: below threshold %s)" % threshold),
                    })

    print("target-level rows read                           %d" % rows)
    print("  score rebuilt from the evidence cell           %d of %d" % (score_ok, rows))
    print("  band  rebuilt from the evidence cell           %d of %d" % (band_ok, rows))
    if disagreements:
        for project, why in disagreements[:10]:
            print("      MISMATCH %s %s" % (project, why))
        sys.exit("refused: the parser does not reproduce the committed artefact, so "
                 "any exposure figure computed from it would rest on nothing.")
    print()

    changed = [e for e in exposed if e["new_band"] != e["band"]]
    print("(project, target) pairs with an ancestor AND its descendant contributing  %d"
          % len(exposed))
    print("of those, pairs where dropping the duplicate changes the band            %d"
          % len(changed))
    for e in changed:
        print("   %s target %-5s %s -> %s   score %s -> %s"
              % (e["project"], e["target"], e["band"], e["new_band"],
                 e["score"], e["new_score"]))
    if not exposed:
        print()
        print("No row of the committed table is inflated by this defect. Whether that")
        print("is luck or structure is the companion script's question, and the answer")
        print("decides whether the safety belongs to CORDIS or to score().")


if __name__ == "__main__":
    main()
