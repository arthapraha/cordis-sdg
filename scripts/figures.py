#!/usr/bin/env python3
"""The numbers behind section 6 item 4's visualisations, as data and not pictures.

    python scripts/figures.py --table data/corpus/mapping-table.csv \
        --records data/corpus/records.jsonl \
        --metrics data/pipeline/evaluation-100-metrics.json \
        --out data/corpus/figures.json

Section 6 item 4 names the analyses the competition page asks for:

  "which SDGs are most frequently linked and which least, how SDG relevance
  varies by programme, topic, country, organisation type, project duration and
  scientific field, and where the mapping is uncertain."

WHY THIS EMITS DATA AND NOT CHARTS. Whether the figures are drawn by matplotlib
in a notebook or as committed SVG depends on a decision about this repository's
dependencies that is the owner's and not mine (cordis-sdg seq 243). The counting
is the same either way and the renderer is not, so the counting lives here, in
the standard library, and whatever draws them reads this file.

It also means every number in a chart is inspectable without running the chart.
A figure whose underlying counts cannot be read is a figure nobody can check.

WHAT IT REFUSES. A mapping table that does not cover every project in the
records, or that names a pipeline commit other than the one the whole table
agrees on, or that is still being written. A partial table is a legitimate thing
to look at during a long run and an illegitimate thing to draw a corpus-wide
conclusion from, so --allow-partial says so in the output rather than being
silent about it.
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
URI = "http://data.europa.eu/sdg/"

# Cells build_mapping_table.py writes where a value does not exist. They are
# read back here rather than re-spelled: a count that treats "(no target
# assigned)" as a target id would report a very popular SDG that does not exist.
NOT_A_TARGET = ("(no target assigned)",
                "(goal level only, no target above threshold)")


def load_table(path, allow_partial):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    if not rows:
        sys.exit("refused: %s has no rows" % path)
    commits = {r["pipeline_commit"] for r in rows}
    if len(commits) != 1:
        sys.exit("refused: the table names %d pipeline commits (%s). Rows scored "
                 "by different code cannot be counted together."
                 % (len(commits), ", ".join(sorted(c[:12] for c in commits))))
    snaps = {r["snapshot_sha256"] for r in rows}
    if len(snaps) != 1:
        sys.exit("refused: the table names %d snapshot hashes." % len(snaps))
    return rows, commits.pop(), snaps.pop()


def load_records(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            out[r["id"]] = r
    return out


def counted(pairs, top=None):
    """A count, always with its denominator and the name of what was counted."""
    c = collections.Counter(pairs)
    items = sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if top:
        items = items[:top]
    return [{"key": k, "count": v} for k, v in items]


def duration_band(rec):
    """Project duration in whole years, from the dates the snapshot carries."""
    s, e = rec.get("start_date"), rec.get("end_date")
    if not s or not e or s == "(absent)" or e == "(absent)":
        return "(dates absent)"
    try:
        sy, sm, sd = (int(x) for x in s[:10].split("-"))
        ey, em, ed = (int(x) for x in e[:10].split("-"))
    except (ValueError, AttributeError):
        return "(dates unparseable)"
    months = (ey - sy) * 12 + (em - sm)
    if months < 0:
        return "(end before start)"
    if months <= 12:
        return "up to 1 year"
    if months <= 24:
        return "1 to 2 years"
    if months <= 36:
        return "2 to 3 years"
    if months <= 48:
        return "3 to 4 years"
    if months <= 60:
        return "4 to 5 years"
    return "over 5 years"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="data/corpus/mapping-table.csv")
    ap.add_argument("--records", default="data/corpus/records.jsonl")
    ap.add_argument("--metrics", default="data/pipeline/evaluation-100-metrics.json")
    ap.add_argument("--out", default="data/corpus/figures.json")
    ap.add_argument("--allow-partial", action="store_true",
                    help="permit a table that does not cover every record, and "
                         "say so in the output")
    args = ap.parse_args()

    rows, commit, snap = load_table(ROOT / args.table, args.allow_partial)
    records = load_records(ROOT / args.records)
    metrics = json.loads((ROOT / args.metrics).read_text(encoding="utf-8"))

    in_table = {r["project_id"] for r in rows}
    missing = len(records) - len(in_table & set(records))
    if missing and not args.allow_partial:
        sys.exit("refused: the table covers %d of %d projects in the records. "
                 "A corpus-wide figure drawn from a partial table is a figure "
                 "about whichever projects happened to finish. Pass "
                 "--allow-partial to look at it anyway."
                 % (len(in_table & set(records)), len(records)))

    assigned = [r for r in rows if r["assignment_level"] == "target"]
    goal_only = [r for r in rows if r["assignment_level"] == "goal_only"]
    none_rows = [r for r in rows if r["assignment_level"] == "none"]

    # --- which SDGs are most and least frequently linked ---------------------
    target_ids = [r["sdg_target_uri"][len(URI):] for r in assigned
                  if r["sdg_target_uri"] not in NOT_A_TARGET]
    goal_ids = [r["sdg_goal_uri"][len(URI):] for r in assigned
                if r["sdg_goal_uri"] not in NOT_A_TARGET]

    # Targets and goals reached by NOTHING are the other half of this figure and
    # a count of what was assigned cannot show them. Read from the taxonomy.
    with open(ROOT / "data/terms/sdg-targets.csv", encoding="utf-8", newline="") as fh:
        tax = list(csv.DictReader(fh, delimiter=";"))
    all_targets = {t["target_id"] for t in tax}
    all_goals = {t["goal_id"] for t in tax}

    def by_project(rows_, key):
        """Distinct projects per key, not rows: a project with five targets in
        one goal must not count five times towards that goal."""
        seen = collections.defaultdict(set)
        for r in rows_:
            seen[key(r)].add(r["project_id"])
        return {k: len(v) for k, v in seen.items()}

    goal_projects = by_project(
        [r for r in assigned if r["sdg_goal_uri"] not in NOT_A_TARGET],
        lambda r: r["sdg_goal_uri"][len(URI):])

    # --- dimensions ----------------------------------------------------------
    # Each is "of the projects with this attribute, how many carry at least one
    # target". A raw count of assignments would just re-report how many projects
    # each programme has.
    def rate_by(attribute):
        total = collections.Counter()
        hit = collections.Counter()
        with_target = {r["project_id"] for r in assigned}
        for pid, rec in records.items():
            if pid not in in_table:
                continue
            for value in attribute(rec):
                total[value] += 1
                if pid in with_target:
                    hit[value] += 1
        out = []
        for k in total:
            out.append({"key": k, "projects": total[k], "with_a_target": hit[k],
                        "rate": round(hit[k] / total[k], 4)})
        out.sort(key=lambda d: (-d["projects"], str(d["key"])))
        return out

    def one(value):
        return [value if value and value != "(absent)" else "(absent)"]

    def many(value):
        if not value or value == "(absent)":
            return ["(absent)"]
        return list(value)

    def org_types(rec):
        orgs = rec.get("participating_organisations")
        if not orgs or orgs == "(absent)":
            return ["(absent)"]
        return sorted({o.get("activity_type") or "(blank)" for o in orgs})

    def fields(rec):
        cats = rec.get("eurosciwoc_categories")
        if not cats or cats == "(absent)":
            return ["(absent)"]
        # The top level of the EuroSciVoc path is the scientific field.
        return sorted({c.split("/")[0].strip() for c in cats})

    figures = {
        "_what_this_is": (
            "The counts behind registration section 6 item 4's visualisations. "
            "Data, not pictures: see the module docstring."),
        "registration_sha256": metrics["registration_sha256"],
        "pipeline_commit": commit,
        "snapshot_sha256": snap,
        "mapping_table_sha256": hashlib.sha256(
            (ROOT / args.table).read_bytes()).hexdigest(),
        "partial": bool(missing),
        "coverage": {
            "projects_in_records": len(records),
            "projects_in_table": len(in_table),
            "projects_missing_from_table": missing,
        },
        "corpus_shape": {
            "rows": len(rows),
            "projects_with_a_target": len({r["project_id"] for r in assigned}),
            "projects_goal_level_only": len({r["project_id"] for r in goal_only}),
            "projects_unassigned": len({r["project_id"] for r in none_rows}),
        },
        "most_linked_targets": counted(target_ids, top=25),
        "least_linked_targets": {
            "targets_in_taxonomy": len(all_targets),
            "targets_never_assigned": sorted(all_targets - set(target_ids)),
            "_note": "A target reached by nothing cannot appear in a count of "
                     "what was assigned, so it is listed rather than plotted.",
        },
        "goals_by_project_count": sorted(
            ({"goal_id": k, "projects": v} for k, v in goal_projects.items()),
            key=lambda d: -d["projects"]),
        "goals_never_assigned": sorted(all_goals - set(goal_ids), key=int),
        "confidence_bands": counted(r["confidence_band"] for r in assigned),
        "by_programme_master_call": rate_by(lambda r: one(r.get("master_call"))),
        "by_legal_basis": rate_by(lambda r: one(r.get("legal_basis"))),
        "by_topic": rate_by(lambda r: one(r.get("topics")))[:40],
        "by_country": rate_by(lambda r: many(r.get("countries")))[:40],
        "by_organisation_type": rate_by(org_types),
        "by_duration": rate_by(lambda r: [duration_band(r)]),
        "by_scientific_field": rate_by(fields),
        "where_the_mapping_is_uncertain": {
            "_what_this_is": (
                "Section 6 item 4's last clause. Uncertainty here is not a "
                "guess about a row: it is the measured shape of the method's "
                "error on the held-out 100, plus the bands and the fallbacks "
                "that mark a weak assignment on the corpus."),
            "evaluation_target_level": metrics["target_level"],
            "evaluation_goal_level": metrics["goal_level_secondary"],
            "recall_ceiling": {
                k: v for k, v in metrics["recall_ceiling"].items()
                if not k.startswith("_")},
            "disagreement_shape_on_the_evaluation_100": {
                "projects_disagreeing": len(metrics["confusion_cases_by_project_id"]),
                "recall_only": sum(
                    1 for r in metrics["confusion_cases_by_project_id"]
                    if not r["pipeline_only"]),
                "precision_only": sum(
                    1 for r in metrics["confusion_cases_by_project_id"]
                    if not r["reference_only"]),
                "both_directions": sum(
                    1 for r in metrics["confusion_cases_by_project_id"]
                    if r["pipeline_only"] and r["reference_only"]),
            },
            "corpus_rows_with_no_band": sum(
                1 for r in assigned if r["confidence_band"].startswith("(none")),
            "corpus_projects_at_goal_level_only": len(
                {r["project_id"] for r in goal_only}),
            "corpus_projects_over_the_cap": sum(
                1 for r in rows if str(r["overflow_beyond_cap"]).isdigit()
                and int(r["overflow_beyond_cap"]) > 0),
        },
    }

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(figures, indent=1, ensure_ascii=False) + "\n")

    print("wrote", args.out)
    if missing:
        print("PARTIAL: %d of %d projects are in the table"
              % (len(in_table), len(records)))
    c = figures["corpus_shape"]
    print("  rows %d   with a target %d   goal level only %d   unassigned %d"
          % (c["rows"], c["projects_with_a_target"],
             c["projects_goal_level_only"], c["projects_unassigned"]))
    print("  targets never assigned: %d of %d"
          % (len(figures["least_linked_targets"]["targets_never_assigned"]),
             len(all_targets)))
    print("  goals never assigned  :",
          figures["goals_never_assigned"] or "none")
    print("  most linked:", ", ".join(
        "%s (%d)" % (d["key"], d["count"]) for d in figures["most_linked_targets"][:6]))


if __name__ == "__main__":
    main()
