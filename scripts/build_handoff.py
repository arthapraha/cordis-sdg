#!/usr/bin/env python3
"""Build the labelling hand-off artefact for the drawn 150.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 4.5: "Code_Cordis posts the drawn sample as an artefact: project ids plus
the section 2 fields, no scores, no pipeline artefacts... that artefact carries
full prose for 150 projects... with each project's absent fields marked absent so
labellers and the pipeline read the same text. All labellers work from that
artefact and nothing else."

TWO RULES GOVERN THIS FILE AND THEY PULL IN THE SAME DIRECTION.

No scores, no pipeline output, no crosswalk, no key terms, no synonyms. A
labeller who can see the method is not labelling blind, and section 4.4 is why
counsel cannot label the evaluation set at all. Nothing here is derived from
anything in data/terms or data/crosswalk.

An absent field is marked absent and never silently omitted. A labeller who
cannot tell "this project has no editorial description" from "this field was not
included" will read the same gap two ways on two different projects. Every
project carries an explicit absent_fields list, and every absent field is present
in the record with the literal value "(absent)". The pipeline reads the same
artefact, so it sees the same gaps the labellers do, which is what makes the
agreement figure mean anything.

Reads the four hashed CORDIS distributions and nothing else. Writes
data/sample/handoff-150.json.
"""

import collections
import csv
import json
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import read_projects

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
SAMPLE = ROOT / "data/sample"
OUT = SAMPLE / "handoff-150.json"

ABSENT = "(absent)"

# Section 2's fields, as v9 defines them. The editorial description is the
# reports JSON's four narrative fields, in this order, because no CSV
# distribution of the dataset carries it.
EDITORIAL_FIELDS = ["teaser", "summary", "workPerformed", "finalResults"]


def load_ids(name):
    path = SAMPLE / name
    if not path.is_file():
        sys.exit("run scripts/draw_sample.py first: %s missing" % path)
    return path.read_text(encoding="utf-8").split("\n")


def load_eurosciwoc(wanted):
    csv.field_size_limit(1 << 30)
    out = collections.defaultdict(list)
    with open(RAW / "cordis-horizon-projects/euroSciVoc.csv",
              encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        h = next(r)
        i_path, i_pid = h.index("euroSciVocPath"), h.index("projectID")
        for row in r:
            if len(row) == len(h) and row[i_pid] in wanted:
                p = row[i_path].strip()
                if p and p not in out[row[i_pid]]:
                    out[row[i_pid]].append(p)
    return out


def load_organisations(wanted):
    csv.field_size_limit(1 << 30)
    out = collections.defaultdict(list)
    with open(RAW / "cordis-horizon-projects/organization.csv",
              encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        h = next(r)
        idx = {k: h.index(k) for k in
               ("projectID", "name", "country", "activityType", "role")}
        for row in r:
            if len(row) != len(h) or row[idx["projectID"]] not in wanted:
                continue
            out[row[idx["projectID"]]].append({
                "name": row[idx["name"]],
                "country": row[idx["country"]],
                "activity_type": row[idx["activityType"]],
                "role": row[idx["role"]],
            })
    return out


def load_deliverables(wanted):
    out = collections.defaultdict(list)
    with zipfile.ZipFile(RAW / "cordis-HORIZONprojectDeliverables-csv.zip") as z:
        with z.open("projectDeliverables.csv") as fh:
            import io
            r = csv.reader(io.TextIOWrapper(fh, encoding="utf-8", newline=""),
                           delimiter=";")
            h = next(r)
            i_pid, i_desc = h.index("projectID"), h.index("description")
            i_type = h.index("deliverableType")
            for row in r:
                if len(row) == len(h) and row[i_pid] in wanted and row[i_desc].strip():
                    out[row[i_pid]].append({
                        "type": row[i_type],
                        "description": row[i_desc].strip(),
                    })
    return out


def load_editorial(wanted):
    """The editorial description, from the reports JSON's four narrative fields.

    A report links to its project through relations.associations[] where the
    association's categories carry the code "/project" — not through a column.
    """
    out = collections.defaultdict(list)
    with zipfile.ZipFile(RAW / "cordis-HORIZONreports-json.zip") as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if not info.filename.endswith(".json"):
                continue
            try:
                rec = json.loads(z.read(info.filename))
            except Exception:
                continue
            pids = set()
            for a in (rec.get("relations") or {}).get("associations") or []:
                cats = (a.get("relations") or {}).get("categories") or []
                if "/project" in {c.get("code") for c in cats} and a.get("id"):
                    pids.add(a["id"])
            if not (pids & wanted):
                continue
            block = {f: (rec.get(f) or "").strip() for f in EDITORIAL_FIELDS}
            if not any(block.values()):
                continue
            block["report_title"] = (rec.get("title") or "").strip()
            for pid in pids & wanted:
                out[pid].append(block)
    return out


def main():
    development = load_ids("development-50.txt")
    evaluation = load_ids("evaluation-100.txt")
    wanted = set(development) | set(evaluation)
    if len(wanted) != 150:
        sys.exit("expected 150 drawn ids, got %d" % len(wanted))

    header, rows = read_projects.load()
    by_id = {r[0]: dict(zip(header, r)) for r in rows}
    broken_for_csv_module = read_projects.csv_module_disagreements()

    voc = load_eurosciwoc(wanted)
    orgs = load_organisations(wanted)
    deliv = load_deliverables(wanted)
    editorial = load_editorial(wanted)

    records = []
    for pid in development + evaluation:
        p = by_id.get(pid)
        if p is None:
            sys.exit("drawn id not in the projects extract: %s" % pid)
        absent = []

        def field(value):
            value = (value or "").strip()
            return value if value else ABSENT

        ed = editorial.get(pid) or []
        dv = [d["description"] for d in deliv.get(pid, [])]
        cats = voc.get(pid) or []
        orgl = orgs.get(pid) or []

        rec = {
            "id": pid,
            "set": "development" if pid in set(development) else "evaluation",
            "acronym": field(p["acronym"]),
            "title": field(p["title"]),
            "objective": field(p["objective"]),
            "editorial_description": ed if ed else ABSENT,
            "deliverable_descriptions": dv if dv else ABSENT,
            "eurosciwoc_categories": cats if cats else ABSENT,
            "keywords": field(p["keywords"]),
            "topics": field(p["topics"]),
            "master_call": field(p["masterCall"]),
            "sub_call": field(p["subCall"]),
            "legal_basis": field(p["legalBasis"]),
            "start_date": field(p["startDate"]),
            "end_date": field(p["endDate"]),
            "participating_organisations": orgl if orgl else ABSENT,
            "countries": sorted({o["country"] for o in orgl if o["country"]}) or ABSENT,
        }
        for k, v in rec.items():
            if v == ABSENT:
                absent.append(k)
        rec["absent_fields"] = absent
        # Not a field of the project: a note about how the source stores it, so a
        # labeller reading unusual punctuation knows it is the data and not us.
        rec["source_note"] = (
            "objective is under-escaped in the CORDIS export and a standard CSV "
            "reader breaks this row; read through scripts/read_projects.py"
            if pid in broken_for_csv_module else "")
        records.append(rec)

    doc = {
        "what_this_is": (
            "The section 4.5 labelling hand-off for registration v9's seeded draw "
            "of 150 projects. Label from this artefact and nothing else."
        ),
        "registration_sha256":
            "72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c",
        "draw": json.loads((SAMPLE / "draw.json").read_text(encoding="utf-8")),
        "contains_no": [
            "scores", "assignments", "confidence bands", "matched phrases",
            "the crosswalk", "key terms", "synonyms", "the stop-list",
            "the negation rule", "any pipeline output",
        ],
        "absent_field_convention": (
            "Every field is present on every record. A field with no content in "
            "the snapshot carries the literal string \"%s\", and its name is "
            "listed in that record's absent_fields. Absence is therefore always "
            "explicit and never a missing key." % ABSENT
        ),
        "editorial_description_is": (
            "the reports JSON distribution's teaser, summary, workPerformed and "
            "finalResults, read in that order, per v9 section 2. A project may "
            "have more than one report; each is a separate block."
        ),
        "label_format": (
            "id -> list of SDG target URIs, no justifications, per section 4.5."
        ),
        "projects": records,
    }

    # newline="" for the same reason as everywhere else here: the labellers
    # compare this artefact by hash, and a CRLF translation would give two
    # correct builds two different hashes.
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    dev = [r for r in records if r["set"] == "development"]
    ev = [r for r in records if r["set"] == "evaluation"]
    def pct(rs, key):
        return 100.0 * sum(1 for r in rs if r[key] != ABSENT) / len(rs)
    print("wrote", OUT.relative_to(ROOT), "%.1f KB" % (OUT.stat().st_size / 1024))
    print("projects: %d development, %d evaluation" % (len(dev), len(ev)))
    for k in ("objective", "editorial_description", "deliverable_descriptions",
              "eurosciwoc_categories", "keywords"):
        print("  %-26s present on %5.1f%% of the 150" % (k, pct(records, k)))
    print("  rows a standard CSV reader breaks:",
          sum(1 for r in records if r["source_note"]))


if __name__ == "__main__":
    main()
