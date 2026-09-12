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
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TERMS = ROOT / "data/terms"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
PARAMS = ROOT / "data/pipeline/parameters-v1.json"

ABSENT = "(absent)"

# The two trees section 3.5's freeze covers. Everything in them is rule data
# except the prose README beside the crosswalk, which is excluded by name and
# only there.
FROZEN_TREES = ("data/terms", "data/crosswalk")
FROZEN_TREE_EXCLUDES = {"data/crosswalk/README.md"}

# EVERY DATA FILE THIS RUN OPENED, MEASURED BY THE INTERPRETER AND NOT BY ME.
#
# Condition 4 is "the run hashes the files it loads". A list of those paths
# written next to the loaders would be this repository's recurring failure in
# its purest form — a control reported as covering a thing it was never run
# against — because such a list is checked against my memory of the loaders, not
# against the loaders. I said so at cordis-sdg seq 216 before building it.
#
# So it is not a list. sys.addaudithook fires on the interpreter's own "open"
# event, underneath this file and underneath csv and json, and records every
# path this process opens anywhere under data/. The guard then requires each one
# to be a file _frozen covers, or one of the two inputs hashed separately in the
# output. A loader added tomorrow that reads a sixth rule file is refused
# without anyone remembering to declare it, wherever under data/ it puts it.
#
# It deliberately records the whole of data/ and not just the frozen trees. A
# check scoped to those two trees would be redundant — every file in them is
# already covered by walking them — and would miss the case worth catching,
# which is a loader reading rule data from a directory nobody froze.
OPENED = set()


def _audit(event, args):
    if event != "open" or not args:
        return
    path = args[0]
    if isinstance(path, int):          # an already-open file descriptor
        return
    try:
        # relpath and abspath are string operations; neither opens anything, so
        # the hook cannot re-enter itself. Path.resolve() would stat, which is
        # why it is not used here.
        rel = os.path.relpath(os.path.abspath(os.fsdecode(path)), str(ROOT))
    except (TypeError, ValueError, OSError):
        return
    rel = rel.replace(os.sep, "/")
    if rel.startswith("data/"):
        OPENED.add(rel)


sys.addaudithook(_audit)

# Section 3.4's five sources. The order is fixed so that "which sources were
# present" is the same list on every row.
SOURCES = ["title", "keywords", "objective", "editorial_description",
           "deliverable_descriptions"]


def effective_parameters(obj):
    """The parameters with every documentation key removed, recursively.

    WHY THE OUTPUT HASHES THIS AND NOT THE FILE. The first version recorded the
    sha256 of parameters-v1.json itself. That makes adding a comment
    indistinguishable from changing a weight: counsel asked for a note about what
    `independent_sources` counts, the note went into the file, the file's hash
    moved, and the output's hash moved with it — on a run whose every scored row
    was byte-identical. I then claimed the output reproduced, because I had
    checked before writing the note and not after (cordis-sdg seq 132).

    Provenance should answer "were these the numbers?", not "was this the same
    prose?". Keys beginning with an underscore are documentation and are stripped
    here, so the recorded hash moves when a parameter moves and stays still when
    someone explains one. The file's own hash is recorded in the commit and the
    README, where a changing hash costs nothing.
    """
    if isinstance(obj, dict):
        return {k: effective_parameters(v) for k, v in obj.items()
                if not k.startswith("_")}
    if isinstance(obj, list):
        return [effective_parameters(v) for v in obj]
    return obj


def values_digest(params):
    return hashlib.sha256(
        json.dumps(effective_parameters(params), sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def frozen_tree_files():
    """Every rule file in the frozen trees, read from the trees themselves.

    Walked rather than listed, so a file that exists cannot fail to be covered
    because nobody remembered it. The first version of _frozen listed seven
    filenames and omitted data/terms/sdg-targets.csv; nothing could have caught
    that, because the list was the only statement of what the list should be.
    """
    out = []
    for tree in FROZEN_TREES:
        for p in sorted((ROOT / tree).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if rel not in FROZEN_TREE_EXCLUDES:
                out.append(rel)
    return sorted(out)


def sha256_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def freeze_conditions(params, freeze_seq_arg, handoff, opened):
    """Registration section 4.3's four conditions. Returns those that FAILED.

    All four are required before an evaluation record is scored. Each returns
    its own sentence, so a refusal says which one stopped the run rather than
    that something about the freeze was wrong. They are evaluated together and
    all failures are reported: a run that satisfies three of four should be told
    about the fourth, not sent round again to discover the next one.

    Condition 4 is the one with teeth, and it is three checks that have to hold
    together. _frozen must carry a digest for every file in the frozen trees;
    every digest it carries must equal the file on disk; and every data file
    this process actually opened must be one it carries. Drop any of the three
    and the guard has a hole: without the first the record can be narrowed,
    without the second it is a list of names that proves nothing, without the
    third a loader can read rule data from a directory nobody froze.
    """
    failed = []
    frozen = params.get("_frozen") or {}

    # ---- 1: the freeze is recorded at all ----------------------------------
    if "freeze_seq" not in frozen:
        failed.append(
            "condition 1: _frozen.freeze_seq is absent from %s. Section 4.3 "
            "scores the evaluation set only after the owner's freeze word, and "
            "an unrecorded freeze is not one."
            % PARAMS.relative_to(ROOT))

    # ---- 2: the parameters are the ones that were frozen -------------------
    recorded_values = frozen.get("parameters_values_sha256")
    actual_values = values_digest(params)
    if recorded_values != actual_values:
        failed.append(
            "condition 2: the parameters' values digest is %s and _frozen "
            "records %s. A weight, threshold or band has moved since the "
            "freeze. Documentation keys are stripped before this hash, so this "
            "cannot be a comment."
            % (actual_values, recorded_values))

    # ---- 3: the caller names the freeze, and names it right -----------------
    #
    # Deliberately not defaulted. The value the run is checked against must be
    # typed by whoever starts the run, so that scoring the held-out set is an
    # act with a number in it rather than something a script fell into.
    if freeze_seq_arg is None:
        failed.append(
            "condition 3: --freeze-seq was not given. Scoring the evaluation "
            "set requires the caller to state which freeze they are running "
            "under; it is not defaulted from the file being checked.")
    elif freeze_seq_arg != frozen.get("freeze_seq"):
        failed.append(
            "condition 3: --freeze-seq %s does not match _frozen.freeze_seq %r."
            % (freeze_seq_arg, frozen.get("freeze_seq")))

    # ---- 4: the rule files are the frozen rule files ------------------------
    failed.extend(rule_file_failures(frozen, handoff, opened))
    return failed


def rule_file_failures(frozen, handoff, opened):
    """Condition 4, against `opened` — the snapshot taken when loading FINISHED.

    Not against OPENED itself. This function hashes every file _frozen records,
    and read_bytes opens them, so reading the live set here would mean the check
    reporting on paths the checker opened rather than paths the loaders did. The
    first version did exactly that: it named all eight rule files as read by the
    run, when the run reads five. A control that reports on its own footprint is
    this repository's recurring failure wearing a new coat.
    """
    recorded = frozen.get("rule_file_sha256")
    if not isinstance(recorded, dict) or not recorded:
        return ["condition 4: _frozen carries no rule_file_sha256 block, so "
                "nothing states what the rule files were at the freeze."]

    out = []
    on_disk = frozen_tree_files()

    missing = [f for f in on_disk if f not in recorded]
    if missing:
        out.append("condition 4: _frozen records no digest for %d file(s) that "
                   "exist in the frozen trees: %s. A partial record reads as "
                   "coverage and is not."
                   % (len(missing), ", ".join(missing)))

    gone = [f for f in sorted(recorded) if not (ROOT / f).is_file()]
    if gone:
        out.append("condition 4: _frozen records a digest for %d file(s) that "
                   "are not in the tree: %s." % (len(gone), ", ".join(gone)))

    moved = []
    for f in sorted(recorded):
        if f in gone:
            continue
        actual = sha256_file(f)
        if actual != recorded[f]:
            moved.append("%s is %s, frozen as %s" % (f, actual, recorded[f]))
    if moved:
        out.append("condition 4: %d rule file(s) differ from the freeze: %s."
                   % (len(moved), "; ".join(moved)))

    # The two files under data/ that are legitimately not rule data: the
    # hand-off artefact the labellers worked from and the parameters. Both are
    # hashed in the output in their own right — handoff_sha256 and
    # parameters_values_sha256 — so neither is unaccounted for, and this is a
    # two-item exemption rather than a way of naming things off the list.
    allowed = set(recorded) | {PARAMS.relative_to(ROOT).as_posix()}
    if handoff is not None:
        try:
            allowed.add(os.path.relpath(
                os.path.abspath(str(handoff)), str(ROOT)).replace(os.sep, "/"))
        except (TypeError, ValueError, OSError):
            pass
    undeclared = sorted(p for p in opened if p not in allowed)
    if undeclared:
        out.append("condition 4: this run opened %d file(s) under data/ that "
                   "_frozen does not cover and that are neither the hand-off "
                   "artefact nor the parameters: %s. A file the run reads and "
                   "the freeze does not name is rule data outside the freeze."
                   % (len(undeclared), ", ".join(undeclared)))
    return out


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
    # KEEP ONLY THE LAST BOUNDARY. This accumulated — `left = left + m.end()` —
    # while every m.end() indexes the same slice taken at the original left, so
    # two boundaries in the lookback pushed `left` past the match and `before`
    # came back empty. negation_verdict then saw nothing and kept every match.
    # Measured on the development 50 before the fix: 847 matches examined, 224
    # with an empty window, 26.4%. Section 3.3 is committed data and the code was
    # not running it on a quarter of its matches. Found by counsel at cordis-sdg
    # seq 149.
    window_start = left
    for m in re.finditer(r"[.?!]\s|\n", text[window_start:start]):
        left = window_start + m.end()
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
            # A PHRASE ABSENT AS A PLAIN SUBSTRING CANNOT MATCH THE PATTERN
            # BELOW, so skipping it here changes how fast this loop reaches its
            # answer and cannot change the answer. The pattern's core is
            # re.escape(phrase) — the literal characters, no alternation, no
            # character class, no IGNORECASE — wrapped in two zero-width
            # lookarounds, and a zero-width assertion cannot make a literal
            # match text that does not contain it. The test runs on `low`, the
            # same string the pattern runs on.
            #
            # It is here because the corpus is 23,451 projects and the
            # vocabulary is 1,222 phrases, so the full snapshot took about ten
            # hours: the cost is the vocabulary, not the text. Owner's word at
            # cordis-sdg seq 244, on counsel's reading at seq 242, with the
            # proof being 0938fe34… and 45a514cf… reproduced byte-identical
            # from this code. Nothing under section 3 moves: no rule file
            # changes, so _frozen.rule_file_sha256 stands, and no parameter
            # changes, so the values digest stands.
            if phrase not in low:
                continue
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
        # A CONTRIBUTING ROW COUNTS AT MOST ONCE PER TARGET.
        #
        # Two contributing rows each say "this discipline is a route to the
        # target, not its subject", and at these weights two of them sum to 3.0
        # — exactly one direct row, which says "this is what the target is
        # about". That is arithmetic standing in for a reviewed judgement. On the
        # corpus, 338 (project, target) pairs are reached by more than one row
        # and 100 cross the threshold only because the rows were summed; every
        # one of those is contributing plus contributing.
        #
        # Direct rows still sum, deliberately. Two direct rows come from two
        # different category branches — zero ancestor pairs exist in the whole
        # corpus — so they are two independent reviewed claims about the same
        # target, which is corroboration rather than duplication.
        contributing_counted = set()
        for path in cats:
            for row in crosswalk.get(path.strip(), []):
                if row["strength"] == "contributing":
                    if row["target_id"] in contributing_counted:
                        continue
                    contributing_counted.add(row["target_id"])
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
                # Section 3.6 does not say whether a target refused at target
                # level for lacking discriminating evidence may still push a goal
                # over the fallback threshold. parameters-v1.json now states that
                # it may not, and says why: otherwise the discriminating
                # requirement is a formality, since the same evidence reaches the
                # same project by a weaker route.
                if (a["requires_discriminating_evidence"]
                        and params["ambiguity"]["fallback_requires_discriminating_evidence"]
                        and not t["has_discriminating"]):
                    continue
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
    # which rule stopped them. A value that selects no record is refused below
    # by name, and a value that selects an evaluation record meets the four
    # conditions rather than the spelling of the flag.
    ap.add_argument("--set", default="development")
    ap.add_argument("--out", required=True)
    ap.add_argument("--freeze-seq", type=int, default=None,
                    help="the cordis-sdg seq of the owner's freeze word. "
                         "Required to score any evaluation record, and checked "
                         "against _frozen.freeze_seq. Never defaulted.")
    args = ap.parse_args()

    params = json.loads(PARAMS.read_text(encoding="utf-8"))

    # A tuned threshold below the low band's minimum makes band() fall through to
    # null, and an empty confidence column is a submission defect under section 6
    # item 2. At threshold 2.5 the development 50 produced 7 assignments with no
    # band and no warning. Counsel raised it at cordis-sdg seq 149; it is not a
    # bug at any setting used so far, and it becomes one the moment tuning
    # touches the threshold, which is exactly when nobody is looking at bands.
    low = params["confidence_bands"]["low"]["min_score"]
    threshold = params["assignment"]["threshold"]
    if low > threshold:
        sys.exit("refused: confidence_bands.low.min_score (%s) exceeds "
                 "assignment.threshold (%s), so every assignment between them "
                 "would be written with a null confidence band. Lower the band "
                 "or raise the threshold; do not ship an empty column."
                 % (low, threshold))

    doc = json.loads(pathlib.Path(args.handoff).read_text(encoding="utf-8"))
    records = [r for r in doc["projects"] if r["set"] == args.set]
    if not records:
        sys.exit("no records for set %s" % args.set)

    # THE GUARD IS ON THE RECORDS, NOT ON THE SPELLING OF A FLAG.
    #
    # The first version tested `--set == "evaluation"`, and the flag had a third
    # choice, `--set all`, which the record filter admitted. Counsel ran it and
    # scored 150 rows, 100 of them evaluation, exit 0 (cordis-sdg seq 127),
    # while the README claimed the registration could not be breached by a wrong
    # flag. A guard on one spelling of the thing it forbids is not a guard. So
    # what triggers the four conditions is an evaluation record being in hand,
    # whatever route put it there; a flag added tomorrow cannot reopen the hole.
    holds_evaluation = any(r["set"] == "evaluation" for r in records)

    # Loaded BEFORE the guard runs and BEFORE anything is scored, because
    # condition 4 asks what this run opened and there is no answer to that until
    # it has opened them. Loading reads committed rule data and decides nothing.
    vocab, stop = load_vocabulary()
    crosswalk = load_crosswalk()
    patterns = load_negation()
    # Snapshot NOW: everything this run opens as INPUT has been opened, and
    # nothing the guard opens to hash has been. See rule_file_failures.
    loaded = frozenset(OPENED)

    failures = freeze_conditions(params, args.freeze_seq, args.handoff, loaded)
    if holds_evaluation and failures:
        sys.exit("refused: %d of registration section 4.3's four conditions did "
                 "not hold, and all four are required before an evaluation "
                 "record is scored. %d evaluation record(s) were selected and "
                 "none was scored.\n\n  %s"
                 % (len(failures), sum(1 for r in records
                                       if r["set"] == "evaluation"),
                    "\n\n  ".join(failures)))

    # A development run is not gated on the freeze — section 3.5 permits tuning
    # on the 50 — but condition 4 is about the rule data itself, and a run on
    # rule files that have moved since the freeze is wrong at any time. It
    # refuses here too, and says so plainly rather than warning into a log.
    rule_failures = rule_file_failures(params.get("_frozen") or {},
                                       args.handoff, loaded)
    if rule_failures:
        sys.exit("refused: %s" % "\n\n  ".join(rule_failures))

    rows = run(records, vocab, stop, crosswalk, patterns, params)

    artefact_hash = hashlib.sha256(
        pathlib.Path(args.handoff).read_bytes()).hexdigest()
    result = {
        "_what_this_is": "Pipeline v1 output, sections 3.4 to 3.6. No model was "
                         "called; section 3.7's explanations are added downstream "
                         "and cannot change any assignment here.",
        "registration_sha256": params["_registration_sha256"],
        "parameters_version": params["version"],
        "parameters_values_sha256": values_digest(params),
        "parameters_values_sha256_is": (
            "sha256 of the parameters with every underscore-prefixed "
            "documentation key stripped, serialised as compact JSON with sorted "
            "keys. It moves when a parameter moves and not when one is "
            "explained. The file's own hash is in the commit and the README."),
        "freeze_seq": (params.get("_frozen") or {}).get("freeze_seq"),
        "freeze_seq_asserted_by_caller": args.freeze_seq,
        "rule_file_sha256": {f: sha256_file(f) for f in frozen_tree_files()},
        "rule_file_sha256_is": (
            "the sha256 of every rule file in data/terms and data/crosswalk, "
            "measured from the files themselves and not from "
            "_frozen. Section 4.3 condition 4 required every one of them to "
            "equal the digest _frozen records for it, or the run would have "
            "refused before scoring. The README beside the crosswalk is prose "
            "about the data rather than rule data and is the one exclusion."),
        "rule_files_this_run_opened": sorted(loaded),
        "rule_files_this_run_opened_is": (
            "the paths the interpreter reports this process opened under data/, recorded by an audit hook rather than declared beside "
            "the loaders, and snapshotted the moment loading finished so that "
            "the guard's own hashing of the eight does not appear here. Fewer "
            "than the eight above: the key-term and negation rules are prose "
            "the vocabularies were built from, and the targets list reaches "
            "this run through those vocabularies. Every path here had to be one "
            "_frozen covers, or the hand-off, or the parameters."),
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
