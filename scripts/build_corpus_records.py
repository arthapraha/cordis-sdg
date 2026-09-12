#!/usr/bin/env python3
"""Every project in the snapshot, in the hand-off record shape, as JSONL.

    python scripts/build_corpus_records.py --out data/corpus/records.jsonl

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 6 item 2: the mapping table covers the submitted corpus, not the drawn
150, so the frozen pipeline needs a record for every project in exactly the shape
it already reads.

IT IMPORTS build_handoff.py AND CALLS ITS LOADERS. It does not re-read one CORDIS
file for itself. The hand-off is the artefact the labellers worked from and the
frozen run scored, and a second reader of the same four distributions would be a
second chance to read them differently — which is the fault this repository
documents at length in read_projects.py and then committed anyway in four CSVs.
The one thing here that is not build_handoff's is the `set` field, because
"development", "evaluation" and "corpus" is a distinction about the draw.

JSONL RATHER THAN ONE JSON DOCUMENT. The 150-project hand-off is about 1 MB; the
corpus is 23,451 projects of the same prose. Written as one array it would have
to be held in memory whole by everything that touches it, and the scoring pass
that reads this takes hours and must be resumable. One record per line is
readable line by line and appendable.

THIS IS NOT A HAND-OFF ARTEFACT AND MUST NEVER BE USED AS ONE. Section 4.5's
hand-off is fd506beb… and the evaluation hand-off is 1603a0d7…. Those are what
the labellers read and what the frozen run scored, and their hashes are on the
chain. This file is a superset built for the submission table; labelling from it
would be labelling from something nobody sealed.
"""

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build_handoff
import read_projects
from repo_path import shown

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data/sample"
ABSENT = build_handoff.ABSENT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/corpus/records.jsonl")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after this many projects; for timing only, and "
                         "the manifest records that the file is partial")
    args = ap.parse_args()

    header, rows = read_projects.load()
    by_id = {r[0]: dict(zip(header, r)) for r in rows}
    broken = read_projects.csv_module_disagreements()
    ids = [r[0] for r in rows]
    if args.limit:
        ids = ids[:args.limit]
    wanted = set(ids)
    print("projects in the snapshot: %d" % len(ids))

    development = set(build_handoff.load_ids("development-50.txt"))
    evaluation = set(build_handoff.load_ids("evaluation-100.txt"))
    print("drawn: %d development, %d evaluation" % (len(development), len(evaluation)))

    print("reading euroSciVoc…"); voc = build_handoff.load_eurosciwoc(wanted)
    print("reading organizations…"); orgs = build_handoff.load_organisations(wanted)
    print("reading deliverables…"); deliv = build_handoff.load_deliverables(wanted)
    print("reading reports JSON…"); editorial = build_handoff.load_editorial(wanted)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = {"development": 0, "evaluation": 0, "corpus": 0}
    with open(out, "w", encoding="utf-8", newline="") as fh:
        for pid in ids:
            p = by_id[pid]

            def field(value):
                value = (value or "").strip()
                return value if value else ABSENT

            ed = editorial.get(pid) or []
            dv = [d["description"] for d in deliv.get(pid, [])]
            cats = voc.get(pid) or []
            orgl = orgs.get(pid) or []
            which = ("development" if pid in development
                     else "evaluation" if pid in evaluation else "corpus")
            counts[which] += 1

            rec = {
                "id": pid,
                "set": which,
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
            rec["absent_fields"] = [k for k, v in rec.items() if v == ABSENT]
            rec["source_note"] = (
                "objective is under-escaped in the CORDIS export and a standard "
                "CSV reader breaks this row; read through scripts/read_projects.py"
                if pid in broken else "")
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {
        "_what_this_is": (
            "Every project in the snapshot in the section 4.5 hand-off record "
            "shape, for the section 6 mapping table. NOT a hand-off artefact: "
            "nobody labelled from this and nothing was sealed against it."),
        "registration_sha256":
            "72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c",
        "records": len(ids),
        "partial": bool(args.limit),
        "by_set": counts,
        "records_sha256": digest,
        "built_by": "scripts/build_corpus_records.py, calling build_handoff.py's "
                    "own loaders",
    }
    man = out.with_suffix(".manifest.json")
    with open(man, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")

    print()
    print("wrote %s  %.1f MB" % (shown(out, ROOT), out.stat().st_size / 1048576))
    print("  sha256      ", digest)
    print("  records     ", len(ids))
    print("  by set      ", counts)
    print("  manifest    ", shown(man, ROOT))


if __name__ == "__main__":
    main()
