#!/usr/bin/env python3
"""Extract the SDG goals and targets from the hashed taxonomy snapshot.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 2: the taxonomy is "EU Vocabularies SDG authority table: goals, targets,
indicator concepts; one snapshot, URI-keyed, hash in the manifest".

Everything downstream — the key terms, the synonym list, the crosswalk — keys on
the URIs this script emits, so that no label is ever transcribed by hand from the
UN website or from memory. The labels here are the taxonomy's own bytes.

The distribution uses SKOS-XL: a concept's prefLabel is a REFERENCE to a label
resource, and the literal lives on that resource with its language tag. Reading
skos:prefLabel directly returns nothing, which is the trap this file exists to
document as much as to avoid.

Writes data/terms/sdg-targets.csv. Reads only data/raw/sdg-skos-ap-eu.rdf.
"""

import csv
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/raw/sdg-skos-ap-eu.rdf"
OUT = ROOT / "data/terms/sdg-targets.csv"

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
XL = "{http://www.w3.org/2008/05/skos-xl#}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

GOAL = re.compile(r"^http://data\.europa\.eu/sdg/(\d+)$")
TARGET = re.compile(r"^http://data\.europa\.eu/sdg/(\d+)\.([0-9a-z]+)$")


def load():
    if not SOURCE.is_file():
        sys.exit("missing taxonomy snapshot: %s" % SOURCE.relative_to(ROOT))
    root = ET.parse(SOURCE).getroot()

    # Pass one: every label resource, by URI, by language.
    labels = {}
    for d in root:
        uri = d.get(RDF + "about")
        if not uri:
            continue
        lit = d.find(XL + "literalForm")
        if lit is not None:
            labels.setdefault(uri, {})[lit.get(XML_LANG)] = (lit.text or "").strip()

    # Pass two: every concept and the label resources it points at.
    concepts = {}
    for d in root:
        uri = d.get(RDF + "about")
        if not uri:
            continue
        refs = [p.get(RDF + "resource") for p in d.findall(XL + "prefLabel")]
        refs = [r for r in refs if r]
        if refs:
            concepts[uri] = refs
    return labels, concepts


def english(labels, refs):
    """The English prefLabel, or empty. Language is read, never assumed.

    A concept may carry MORE THAN ONE English prefLabel, and taking the first in
    document order is wrong. Exactly one target in this snapshot does: 12.3 has
    `label_11f52c55fa`, whose literal is the truncated fragment "By 2030,d", and
    `label_5a4f01a073`, which carries the full 165-character target text. The
    truncated one comes first, so the first-match reading gave target 12.3 the
    label "By 2030,d" and the key-term rule then emitted exactly two terms from
    it: "2030" and "d".

    "2030" is the damaging one. Horizon Europe objectives mention 2030 constantly
    — it is in the programme's own framing and in Agenda 2030 — so target 12.3
    would have fired on a large share of the corpus on the strength of a year.
    A truncated label did not merely lose evidence, it manufactured a false
    positive generator, and it was invisible because the pipeline had no reason
    to look at a label's length.

    The longest English label is taken instead. That is deterministic, it needs
    no list of exceptions, and it is right for the general case: a truncation is
    always shorter than the text it truncates. Found by Hermes Cordis in the
    section 4.6 pass (cordis-sdg seq 103) and verified here from the taxonomy's
    own bytes rather than from an external source.
    """
    candidates = [labels.get(r, {}).get("en") for r in refs]
    candidates = [c for c in candidates if c]
    if not candidates:
        return ""
    return max(candidates, key=len)


def main():
    labels, concepts = load()

    goals = {}
    for uri, refs in concepts.items():
        m = GOAL.match(uri)
        if m:
            goals[m.group(1)] = english(labels, refs)

    rows = []
    for uri, refs in concepts.items():
        m = TARGET.match(uri)
        if not m:
            continue
        goal_id, suffix = m.group(1), m.group(2)
        label = english(labels, refs)
        if not label:
            continue
        rows.append({
            "target_uri": uri,
            "target_id": "%s.%s" % (goal_id, suffix),
            "goal_id": goal_id,
            "goal_uri": "http://data.europa.eu/sdg/%s" % goal_id,
            "goal_label": goals.get(goal_id, ""),
            "is_means_of_implementation": "yes" if suffix.isalpha() else "no",
            "target_label": label,
        })

    # Sort by goal then by target, numerically where the suffix is a number and
    # after the numbered ones where it is a letter, which is the order the UN
    # prints them in (1.1 … 1.5, then 1.a, 1.b).
    def key(r):
        _, suffix = r["target_id"].split(".", 1)
        return (int(r["goal_id"]), suffix.isalpha(),
                int(suffix) if suffix.isdigit() else 0, suffix)

    rows.sort(key=key)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        # lineterminator is explicit: the csv module writes CRLF by default even
        # with newline="", which would make a regeneration in a fresh clone
        # differ from the committed file on every line.
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    means = sum(1 for r in rows if r["is_means_of_implementation"] == "yes")
    print("wrote", OUT.relative_to(ROOT))
    print("goals:", len(goals))
    print("targets:", len(rows), "(%d outcome, %d means of implementation)"
          % (len(rows) - means, means))


if __name__ == "__main__":
    main()
