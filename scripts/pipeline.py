#!/usr/bin/env python3
"""Pipeline v1: sections 3.4 to 3.6, the part a reader can run by hand.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c.

  3.4  lexical evidence, every match recorded as the exact phrase found with its
       source field, and which of the five sources were present for the project
  3.5  score, threshold, the cap of five, the goal assigned with its target
  3.6  confidence band, cross-cutting and ambiguous projects

SECTION 3 IS EXPLICIT THAT THE DECISION IS MADE HERE AND NOT BY A MODEL: "The
mapping DECISION is made by rules a reader can run by hand. A language model
writes the explanation of a decision already made; it never makes one." Nothing
in this file calls a model. The explanation pass is section 3.7 and lives in
explain.py, downstream of a decision this file has already fixed, and its output
cannot add or remove an assignment.

INPUT IS THE HAND-OFF ARTEFACT, NOT THE SNAPSHOT. The labellers work from
handoff-150.json and section 4.5 requires the pipeline to read the same text they
do, gaps included. Reading the raw extracts here instead would let the pipeline
see a field a labeller was not shown, and the agreement figure would then be
measuring two different inputs.

Everything it needs is committed: the crosswalk, the key terms, the synonyms, the
stop-list, the negation patterns and parameters-v1.json. No project text reaches
this file except through the artefact.
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TERMS = ROOT / "data/terms"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
PARAMS = ROOT / "data/pipeline/parameters-v1.json"

ABSENT = "(absent)"

# Section 3.4's five sources. The order is fixed so that "which sources were
# present" is the same list on every row.
SOURCES = ["title", "keywords", "objective", "editorial_description",
           "deliverable_descriptions"]


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def load_vocabulary():
    """Every committed term, keyed by the phrase to look for.

    A phrase can carry evidence for more than one target, so the value is a list.
    """
    stop = {r["term"].strip().lower() for r in read_csv(TERMS / "stop-list.csv")}
    vocab = collections.defaultdict(list)
    for r in read_csv(TERMS / "target-key-terms.csv"):
        vocab[r["term"]].append({
            "target_id": r["target_id"],
            "kind": "key_term",
            "discriminating": r["discriminating"] == "yes",
            "words": len(r["term"].split()),
        })
    for r in read_csv(TERMS / "synonyms.csv"):
        vocab[r["synonym"].strip().lower()].append({
            "target_id": r["target_id"],
            "kind": "synonym_" + r["kind"].strip(),
            "discriminating": True,
            "words": len(r["synonym"].split()),
        })
    return vocab, stop


def load_crosswalk():
    out = collections.defaultdict(list)
    for r in read_csv(CROSSWALK):
        out[r["eurosciwoc_path"].strip()].append(
            {"target_id": r["target_id"], "strength": r["strength"],
             "justification": r["justification"]})
    return out


def load_negation():
    rows = read_csv(TERMS / "negation-patterns.csv")
    by_class = collections.defaultdict(list)
    for r in rows:
        by_class[r["class"]].append(r["pattern"].strip().lower())
    return by_class


def normalise(text):
    return re.sub(r"\s+", " ", text or "").strip()


def field_text(record, name):
    """The text of one section 3.4 source, or None when the field is absent.

    None and "" are different and must stay different: None means the snapshot
    has nothing, which is what the labellers were shown, and section 3.6 counts
    independent sources over present fields only.
    """
    value = record.get(name)
    if value == ABSENT or value is None:
        return None
    if name == "editorial_description":
        parts = []
        for block in value:
            for k in ("teaser", "summary", "workPerformed", "finalResults"):
                if block.get(k):
                    parts.append(block[k])
        return normalise(" ".join(parts)) or None
    if name == "deliverable_descriptions":
        return normalise(" ".join(value)) or None
    return normalise(value) or None


def sentence_window(text, start, end):
    """Section 3.3's window: the sentence containing the match, or 300 characters
    either side when no boundary is found."""
    left = max(0, start - 300)
    right = min(len(text), end + 300)
    for m in re.finditer(r"[.?!]\s|\n", text[left:start]):
        left = left + m.end()
    nxt = re.search(r"[.?!]\s|\n", text[end:right])
    if nxt:
        right = end + nxt.start()
    return text[left:start], text[end:right]


def negation_verdict(before, patterns):
    """Apply the committed negation rule. Returns None to keep the match, or the
    pattern class that discards it.

    Rule 4 first and decisive: a target that asks for a reduction is evidenced by
    text about reducing, so a negative-subject verb protects the match.
    """
    low = before.lower()
    if any(p in low for p in patterns["negative_subject"]):
        return None
    tail60 = low[-60:]
    for p in patterns["scope_exclusion"]:
        if p in tail60:
            return "scope_exclusion"
    words = re.findall(r"[a-z']+|non-", low)
    last5 = " ".join(words[-5:])
    for p in patterns["direct_negation"]:
        if re.search(r"(^|\s)" + re.escape(p) + r"(\s|$)", last5) or (
                p == "non-" and last5.endswith("non-")):
            return "direct_negation"
    tail40 = low[-40:]
    for p in patterns["comparison"]:
        if p in tail40:
            return "comparison"
    return None


def find_matches(record, vocab, stop, patterns):
    """Section 3.4. Every match with its exact phrase and its source field."""
    matches = []
    discards = []
    present = []
    for name in SOURCES:
        text = field_text(record, name)
        if text is None:
            continue
        present.append(name)
        low = text.lower()
        for phrase, entries in vocab.items():
            if phrase in stop:
                continue          # a matched phrase that is one stop-list word
            # ONE MATCH PER PHRASE PER FIELD, and the first occurrence that
            # SURVIVES the negation rule is the one that counts. A phrase is
            # evidence that a project mentions a thing, not a measure of how
            # often, so repetition does not raise a score. But the surviving
            # occurrence must be sought, not assumed to be the first: a project
            # that writes "not related to water quality" in its scope sentence
            # and "we improve water quality" in its aim has said the second
            # thing, and stopping at the first occurrence would lose it. If
            # every occurrence is discarded, the discard is recorded once.
            first_discard = None
            kept = False
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", low):
                before, _ = sentence_window(low, m.start(), m.end())
                why = negation_verdict(before, patterns)
                row = {"field": name, "phrase": text[m.start():m.end()],
                       "at": m.start()}
                if why:
                    if first_discard is None:
                        first_discard = dict(row, discarded_by=why,
                                             targets=[e["target_id"] for e in entries])
                    continue
                for e in entries:
                    matches.append(dict(row, **e))
                kept = True
                break
            if not kept and first_discard is not None:
                discards.append(first_discard)
    return matches, discards, present


def score(record, matches, crosswalk, params):
    """Sections 3.5 and 3.6."""
    w = params["evidence_weights"]
    fm = params["field_multipliers"]
    per_target = collections.defaultdict(
        lambda: {"score": 0.0, "evidence": [], "fields": set(),
                 "has_discriminating": False})

    for m in matches:
        if m["kind"] == "key_term":
            if not m["discriminating"]:
                base = w["key_term_not_discriminating"]
            elif m["words"] > 1:
                base = w["key_term_multi_word"]
            else:
                base = w["key_term_single_word"]
        else:
            base = w.get(m["kind"], w["synonym_domain"])
        value = base * fm.get(m["field"], 1.0)
        t = per_target[m["target_id"]]
        t["score"] += value
        t["fields"].add(m["field"])
        if m["discriminating"]:
            t["has_discriminating"] = True
        t["evidence"].append({"source": "lexical", "field": m["field"],
                              "phrase": m["phrase"], "kind": m["kind"],
                              "weight": round(value, 3)})

    cats = record.get("eurosciwoc_categories")
    if cats != ABSENT and cats:
        for path in cats:
            for row in crosswalk.get(path.strip(), []):
                value = w["crosswalk_" + row["strength"]] * fm["eurosciwoc_categories"]
                t = per_target[row["target_id"]]
                t["score"] += value
                t["fields"].add("eurosciwoc_categories")
                if row["strength"] == "direct":
                    t["has_discriminating"] = True
                t["evidence"].append({"source": "crosswalk", "category": path,
                                      "strength": row["strength"],
                                      "justification": row["justification"],
                                      "weight": round(value, 3)})
    return per_target


def band(score_value, sources, params):
    for name in ("high", "medium", "low"):
        rule = params["confidence_bands"][name]
        if score_value >= rule["min_score"] and sources >= rule["min_independent_sources"]:
            return name
    return None


def run(records, vocab, stop, crosswalk, patterns, params):
    a = params["assignment"]
    out = []
    for rec in records:
        matches, discards, present = find_matches(rec, vocab, stop, patterns)
        per_target = score(rec, matches, crosswalk, params)

        eligible = [
            (tid, t) for tid, t in per_target.items()
            if t["score"] >= a["threshold"]
            and (t["has_discriminating"] or not a["requires_discriminating_evidence"])
        ]
        eligible.sort(key=lambda kv: (-kv[1]["score"], kv[0]))
        kept = eligible[:a["max_targets_per_project"]]
        overflow = len(eligible) - len(kept)

        assignments = []
        for tid, t in kept:
            assignments.append({
                "target_id": tid,
                "target_uri": "http://data.europa.eu/sdg/" + tid,
                "goal_id": tid.split(".")[0],
                "goal_uri": "http://data.europa.eu/sdg/" + tid.split(".")[0],
                "score": round(t["score"], 3),
                "independent_sources": len(t["fields"]),
                "confidence": band(t["score"], len(t["fields"]), params),
                "evidence": t["evidence"],
            })

        goals = {a_["goal_id"] for a_ in assignments}
        fallback = []
        if not assignments:
            by_goal = collections.defaultdict(float)
            for tid, t in per_target.items():
                by_goal[tid.split(".")[0]] += t["score"]
            for gid, s in sorted(by_goal.items(), key=lambda kv: -kv[1]):
                if s >= params["ambiguity"]["goal_level_fallback_threshold"]:
                    fallback.append({"goal_id": gid,
                                     "goal_uri": "http://data.europa.eu/sdg/" + gid,
                                     "score": round(s, 3)})
            fallback = fallback[:1]

        out.append({
            "id": rec["id"],
            "set": rec["set"],
            "acronym": rec["acronym"],
            "sources_present": present,
            "sources_absent": [s for s in SOURCES if s not in present],
            "assignments": assignments,
            "goal_level_only": fallback,
            "unassigned": not assignments and not fallback,
            "cross_cutting": len(goals) >= 2,
            "overflow_beyond_cap": overflow,
            "discarded_by_negation_rule": discards,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True,
                    help="path to handoff-150.json")
    # No `choices` list. argparse would reject an unknown value with "invalid
    # choice" and exit 2, which is a refusal that does not say why — and the
    # point of this guard is that a person who types the wrong thing is told
    # which rule stopped them. Every value except "development" is refused here,
    # by one path, naming section 4.3 and the value that was asked for.
    ap.add_argument("--set", default="development")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # THE GUARD IS ON THE DATA, NOT ON THE SPELLING OF A FLAG.
    #
    # The first version of this tested `--set == "evaluation"` and the flag had a
    # third choice, `--set all`, which the record filter admitted. Counsel ran it
    # and scored 150 rows, 100 of them evaluation, exit 0 (cordis-sdg seq 127),
    # while the README claimed the registration could not be breached by a wrong
    # flag. A guard on one spelling of the thing it forbids is not a guard.
    #
    # `all` is gone, and what remains refuses on the records themselves: if any
    # selected record is an evaluation record, this script stops, whatever route
    # brought it here. A future flag cannot reopen the hole because the check no
    # longer looks at flags.
    REFUSAL = ("refused --set %s: registration section 4.3 requires the owner's "
               "freeze word before the evaluation set is scored, and section 3.5 "
               "before any parameter is frozen. This script scores the "
               "development 50 and nothing else on its own say-so.")

    if args.set != "development":
        sys.exit(REFUSAL % args.set)

    params = json.loads(PARAMS.read_text(encoding="utf-8"))
    doc = json.loads(pathlib.Path(args.handoff).read_text(encoding="utf-8"))
    records = [r for r in doc["projects"] if r["set"] == args.set]
    # Belt to the braces above, and the one that survives a future flag: whatever
    # route selected these records, if any of them is an evaluation record this
    # script stops before scoring a single one.
    if any(r["set"] != "development" for r in records):
        sys.exit(REFUSAL % args.set)
    if not records:
        sys.exit("no records for set %s" % args.set)

    vocab, stop = load_vocabulary()
    crosswalk = load_crosswalk()
    patterns = load_negation()
    rows = run(records, vocab, stop, crosswalk, patterns, params)

    artefact_hash = hashlib.sha256(
        pathlib.Path(args.handoff).read_bytes()).hexdigest()
    result = {
        "_what_this_is": "Pipeline v1 output, sections 3.4 to 3.6. No model was "
                         "called; section 3.7's explanations are added downstream "
                         "and cannot change any assignment here.",
        "registration_sha256": params["_registration_sha256"],
        "parameters_version": params["version"],
        "parameters_sha256": hashlib.sha256(PARAMS.read_bytes()).hexdigest(),
        "handoff_sha256": artefact_hash,
        "set": args.set,
        "projects": len(rows),
        "results": rows,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

    assigned = sum(1 for r in rows if r["assignments"])
    print("wrote", out)
    print("projects scored:", len(rows))
    print("with at least one target:", assigned)
    print("goal level only:", sum(1 for r in rows if r["goal_level_only"]))
    print("unassigned:", sum(1 for r in rows if r["unassigned"]))
    print("cross-cutting:", sum(1 for r in rows if r["cross_cutting"]))
    print("overflow beyond the cap:", sum(r["overflow_beyond_cap"] for r in rows))
    print("matches discarded by the negation rule:",
          sum(len(r["discarded_by_negation_rule"]) for r in rows))


if __name__ == "__main__":
    main()
