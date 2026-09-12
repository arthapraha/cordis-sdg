#!/usr/bin/env python3
"""Registration section 4.7's metrics, with their unit — and a self-proof first.

    python scripts/metrics.py \
        --dev-results data/pipeline/development-50-v1.json \
        --dev-results-sha256 032a4881774ce9adbbc84bb8a949b7d06843ad77a23aae1c4b77d6de522ea460 \
        --results <evaluation output> \
        --results-sha256 <its hash> \
        --out data/pipeline/evaluation-100-metrics.json

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 4.7, quoted rather than paraphrased because every figure below is one of
its sentences:

  "The unit is one (project, target-URI) pair. Inter-rater agreement: pairwise,
  exact target-URI match, reported as agreement rate and Cohen's kappa between
  each pair of labellers; goal-level agreement as a secondary figure. On the
  development 50 that is Hermes against counsel. On the evaluation 100 it is
  Hermes against Attila on his 20 only, since he is the only other labeller
  there — a thin overlap, reported with its n and never presented as agreement
  over the hundred. Pipeline precision and recall against the adjudicated
  evaluation labels at target level, goal level secondary; confusion cases listed
  by project id. Agreement against Attila's 20 reported separately as the human
  anchor."

THE SELF-PROOF, WHICH RUNS FIRST AND STOPS EVERYTHING IF IT FAILS. A metrics
script is the one program here whose output nobody can eyeball for plausibility:
a kappa of 0.71 looks exactly like a kappa of 0.68, and an off-by-one in a
denominator produces a number that reads perfectly well. So before it computes a
single new figure this file recomputes EVERY figure already published at
cordis-sdg seq 129 — the development-50 agreement, its kappa at both levels, and
pipeline v1's precision and recall against each label set and their union — from
the two committed label artefacts and the committed v1 output, and refuses if any
one differs. Those numbers were computed by a different seat, by different code,
on a different day, and they are on the chain. Owner's word at seq 228: "so the
script proves itself on numbers already on the chain."

THREE OF SECTION 4.7's FOUR EVALUATION FIGURES EXIST AND ONE DOES NOT. Attila's
20 hand-labels were never made. That removes the evaluation set's inter-rater
agreement entirely — one labeller cannot disagree with himself — and it removes
the human anchor. It also moves section 4.8: with no 20, Hermes Cordis's labels
are the reference for all 100 and the limitation covers the whole set rather than
80 of it. The missing figure is reported as missing rather than leaving a reader
to count four and find three.

WHAT "ADJUDICATED" MEANS HERE, BECAUSE IT IS NOT WHAT IT SOUNDS LIKE. Section
4.8's adjudication needs two labellers to adjudicate between. On the evaluation
100 there is one. No adjudication was performed and no call was taken; "the
adjudicated evaluation labels" are Hermes Cordis's labels unchanged. That is the
rule section 4.8 fixed in advance for exactly this case, not a decision taken
once the numbers were in view.

ON COHEN'S KAPPA AND WHAT ITS ITEMS ARE. Kappa needs a fixed universe of items
each rater classifies. Multi-label data does not come with one, the choice
changes the number, and so it is made in the open rather than inherited from
whichever loop got written first. The universe is every (project, target) pair
over the 169 targets in the taxonomy snapshot — 50 x 169 = 8,450 on the
development set — each classified yes or no by each labeller. The alternative,
the union of pairs somebody assigned, has no negative class at all, which makes
expected agreement meaningless and kappa undefined. The cost is stated with the
figure: the negative class is enormous, so expected agreement is very high and
kappa is accordingly harsh. That is the right direction for a measure whose
purpose is to discount agreement chance would produce anyway. It is also the
construction seq 129 used, which is why the self-proof can check it.
"""

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
LABELS = ROOT / "data/labels"
TARGETS = ROOT / "data/terms/sdg-targets.csv"

URI = "http://data.europa.eu/sdg/"

# The two draws, by the digest each label set must name as the set it covers.
DRAW_DIGEST = {
    "development": "6f7796e478097f0ebcb3469429c7b54493303485c898bbfcd0bd45f25173d3c6",
    "evaluation": "a09eecf88344d2d916b4cc2c90d4cf33988108f4bd3ba6d72145311ff04ce680",
}
HANDOFF_SHA256 = {
    "development": "fd506beb26684df464127df73d351b26f3cbdd6d8db6a8dacc73581e1d231d11",
    "evaluation": "1603a0d7eb351ac92cf17bc488e7a1180cf40305748120076888ac30383a43cc",
}
FREEZE_SEQ = 207

# Two spellings of the same claim. Hermes writes covers_digest; counsel wrote
# development_50_sha256 on the set it made before that name settled. Both carry
# the digest of the draw the set covers, which is the thing section 4.2 needs
# stated, so both are accepted and the VALUE is what is checked. Accepting a key
# name without checking its value would be the defect this whole file is against.
DRAW_KEYS = ("covers_digest", "development_50_sha256", "evaluation_100_sha256")

# Every figure published at cordis-sdg seq 129, by the seat that computed them
# then. The self-proof refuses on any difference. Precision and recall are
# compared at three decimals because that is how they were posted.
SEQ_129 = {
    "target_agreement": {
        "both_assigned": 52, "only_first": 14, "only_second": 35,
        "neither": 8349, "items": 8450,
        "agreement_rate": 0.9942, "cohens_kappa": 0.677, "jaccard": 0.515,
    },
    "goal_agreement": {
        "items": 850, "agreement_rate": 0.9741, "cohens_kappa": 0.806,
    },
    "pipeline_v1": {
        "hermes": {"precision": 0.155, "recall": 0.227},
        "counsel": {"precision": 0.144, "recall": 0.161},
        "union": {"precision": 0.186, "recall": 0.178,
                  "pairs_either_labeller_made": 101, "pipeline_reached": 18},
    },
}


# --------------------------------------------------------------------------
# reading, and refusing

def sha256_of(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_output(path, expected, what):
    """A pipeline output, refused unless the caller names its hash correctly.

    The hash is TYPED BY THE CALLER and not read out of the file, for the same
    reason --freeze-seq is not defaulted in pipeline.py: it makes "these are the
    figures for artefact X" a claim someone made rather than a label the program
    wrote about whatever it happened to open.
    """
    actual = sha256_of(path)
    if expected != actual:
        sys.exit("refused: %s is %s and you named %s. These metrics would be "
                 "reported against an artefact nobody has on the chain."
                 % (what, actual, expected))
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    doc["_sha256"] = actual
    return doc


def load_labels(name, which_set):
    """A label artefact, refused unless its header names what it must.

    Owner's word at cordis-sdg seq 228: refuse if any label file does not name
    the hand-off it was labelled from, the freeze seq, and the draw digest it
    covers.

    THE FREEZE SEQ IS REQUIRED OF EVALUATION SETS AND FORBIDDEN TO BE WRONG
    ANYWHERE, and it is not required of development sets. Section 4.3's ordering
    is that the freeze word comes first and only then is an EVALUATION label set
    uploaded; the development sets were made at seq 128, seventy-nine messages
    before the freeze existed, and demanding a freeze seq of them would refuse
    two artefacts for not recording a thing that had not happened. Stated here
    because it is a reading of the word rather than the word itself.
    """
    path = LABELS / name
    if not path.is_file():
        sys.exit("missing label artefact: %s" % path.relative_to(ROOT))
    doc = json.loads(path.read_text(encoding="utf-8"))
    rel = path.relative_to(ROOT).as_posix()

    got = doc.get("labelled_from_artefact_sha256")
    if got != HANDOFF_SHA256[which_set]:
        sys.exit("refused: %s names hand-off %s; the %s hand-off is %s. "
                 "Section 4.5 requires labels made from that artefact and "
                 "nothing else." % (rel, got, which_set, HANDOFF_SHA256[which_set]))

    named = [(k, doc[k]) for k in DRAW_KEYS if k in doc]
    if not named:
        sys.exit("refused: %s names no draw digest. Section 4.2 requires a "
                 "label set to state which draw it covers; looked for %s."
                 % (rel, ", ".join(DRAW_KEYS)))
    wrong = [(k, v) for k, v in named if v != DRAW_DIGEST[which_set]]
    if wrong:
        sys.exit("refused: %s says it covers %s=%s; the %s draw is %s."
                 % (rel, wrong[0][0], wrong[0][1], which_set,
                    DRAW_DIGEST[which_set]))

    if which_set == "evaluation":
        if doc.get("freeze_seq") != FREEZE_SEQ:
            sys.exit("refused: %s records freeze_seq %r, not %d. Section 4.3's "
                     "ordering runs one way and an evaluation label set that "
                     "does not name the freeze cannot be shown to follow it."
                     % (rel, doc.get("freeze_seq"), FREEZE_SEQ))
    elif "freeze_seq" in doc and doc["freeze_seq"] != FREEZE_SEQ:
        sys.exit("refused: %s records freeze_seq %r, not %d."
                 % (rel, doc["freeze_seq"], FREEZE_SEQ))

    doc["_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    doc["_file"] = rel
    return doc


def taxonomy_targets():
    with open(TARGETS, encoding="utf-8", newline="") as fh:
        return [r["target_id"] for r in csv.DictReader(fh, delimiter=";")]


def pairs_from_labels(doc):
    """{project id: set of target URIs}, refusing anything that is not a URI.

    A set carrying bare target ids would agree with nothing, silently, because
    section 4.7 matches on the exact URI.
    """
    out = {}
    for pid, uris in doc["labels"].items():
        bad = [u for u in uris if not str(u).startswith(URI)]
        if bad:
            sys.exit("%s: label for %s is not a target URI: %r"
                     % (doc["_file"], pid, bad[0]))
        out[str(pid)] = set(uris)
    return out


def pairs_from_pipeline(results):
    """{project id: set of target URIs} assigned at TARGET level.

    goal_level_only rows are deliberately absent. A project assigned at goal
    level made no target claim, and counting one would invent both a prediction
    and a false positive. They appear in the goal-level figure, where they
    belong.
    """
    return {str(r["id"]): {a["target_uri"] for a in r["assignments"]}
            for r in results}


def goals_from_labels(by_project):
    return {pid: {URI + u[len(URI):].split(".")[0] for u in uris}
            for pid, uris in by_project.items()}


def goals_from_pipeline(results):
    out = {}
    for r in results:
        g = {a["goal_uri"] for a in r["assignments"]}
        g |= {f["goal_uri"] for f in r["goal_level_only"]}
        out[str(r["id"])] = g
    return out


# --------------------------------------------------------------------------
# the measures

def prf(predicted, reference):
    tp = fp = fn = 0
    for pid in reference:
        p, r = predicted.get(pid, set()), reference[pid]
        tp += len(p & r)
        fp += len(p - r)
        fn += len(r - p)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else None
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "predicted_pairs": tp + fp, "reference_pairs": tp + fn,
            "precision": round(prec, 4) if prec is not None else None,
            "recall": round(rec, 4) if rec is not None else None,
            "f1": round(f1, 4) if f1 is not None else None}


def agreement(a, b, projects, universe):
    n = len(projects) * len(universe)
    both = only_a = only_b = 0
    for pid in projects:
        sa, sb = a.get(pid, set()), b.get(pid, set())
        both += len(sa & sb)
        only_a += len(sa - sb)
        only_b += len(sb - sa)
    neither = n - both - only_a - only_b
    observed = (both + neither) / n
    pa_yes, pb_yes = (both + only_a) / n, (both + only_b) / n
    expected = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else None
    union = both + only_a + only_b
    return {
        "projects": len(projects), "items_per_project": len(universe), "items": n,
        "both_assigned": both, "only_first": only_a, "only_second": only_b,
        "neither": neither,
        "agreement_rate": round(observed, 4),
        "expected_agreement": round(expected, 6),
        "cohens_kappa": round(kappa, 4) if kappa is not None else None,
        "jaccard": round(both / union, 4) if union else None,
        "_agreement_rate_is": (
            "dominated by the %d items neither labeller assigned, which is why "
            "kappa and the raw counts are reported beside it." % neither),
    }


def confusion(predicted, reference, order):
    rows = []
    for pid in order:
        p, r = predicted.get(pid, set()), reference.get(pid, set())
        if p == r:
            continue
        rows.append({
            "project_id": pid,
            "pipeline_only": sorted(u[len(URI):] for u in p - r),
            "reference_only": sorted(u[len(URI):] for u in r - p),
            "agreed": sorted(u[len(URI):] for u in p & r),
        })
    return rows


def recall_ceiling(handoff_records, reference):
    """How many reference pairs the pipeline COULD reach, at any threshold.

    Not a section 4.7 figure. Reported because a recall number without it invites
    the reading that tuning would fix it, and on the development 50 it would not.

    It imports pipeline.py and uses that file's own loaders and its own score(),
    rather than reimplementing the scoring: a ceiling computed by a second,
    slightly different matcher would measure the second matcher.

    IT TAKES THE HAND-OFF RECORDS, NOT THE PIPELINE OUTPUT ROWS, and the first
    version took the output rows. Those carry an id, a set and the assignments —
    no title, objective or keywords — so find_matches had nothing to search and
    every pair came back with no evidence. It reported a ceiling of 0.0 on a run
    with 21 true positives, which is impossible on its face and did not crash:
    the house failure again, a measure computed against something other than the
    thing it names. The assertion below is what makes it impossible to repeat
    silently.
    """
    import pipeline
    vocab, stop = pipeline.load_vocabulary()
    crosswalk = pipeline.load_crosswalk()
    patterns = pipeline.load_negation()
    params = json.loads(pipeline.PARAMS.read_text(encoding="utf-8"))
    by_id = {str(r["id"]): r for r in handoff_records}
    reachable, unreachable, with_scores = 0, 0, []
    for pid, wanted in reference.items():
        rec = by_id.get(pid)
        if rec is None or not wanted:
            continue
        matches, _, _ = pipeline.find_matches(rec, vocab, stop, patterns)
        per_target = pipeline.score(rec, matches, crosswalk, params)
        for uri in sorted(wanted):
            tid = uri[len(URI):]
            s = per_target.get(tid, {}).get("score") or 0.0
            if s > 0:
                reachable += 1
                with_scores.append([pid, tid, round(s, 3)])
            else:
                unreachable += 1
    total = reachable + unreachable
    # A pair the pipeline actually ASSIGNED must, necessarily, have had
    # evidence. If the ceiling is below the recall it is measuring the wrong
    # thing, whatever number it produced.
    if total and reachable == 0:
        sys.exit("refused: the recall ceiling came out at zero over %d reference "
                 "pairs. No evidence for any pair is not a finding, it is a "
                 "measurement made against the wrong records." % total)
    return {
        "reference_pairs": total,
        "with_some_evidence": reachable,
        "with_no_evidence_at_any_threshold": unreachable,
        "ceiling": round(reachable / total, 4) if total else None,
        "_what_this_is": (
            "the highest recall this vocabulary and crosswalk could reach on "
            "this reference at ANY threshold, because a pair with no evidence "
            "at all is not recoverable by tuning. Computed with pipeline.py's "
            "own loaders and score(), not a second matcher."),
        "_pairs_with_evidence": with_scores,
    }


# --------------------------------------------------------------------------
# the self-proof

def close(got, want, places=3):
    return got is not None and round(got, places) == round(want, places)


def self_proof(dev_doc):
    """Recompute every figure published at cordis-sdg seq 129. Refuse on any."""
    h = load_labels("hermes-cordis-dev50-labels.json", "development")
    c = load_labels("counsel-dev50-labels.json", "development")
    hp, cp = pairs_from_labels(h), pairs_from_labels(c)
    shared = sorted(set(hp) & set(cp))
    universe = taxonomy_targets()
    goals = sorted({t.split(".")[0] for t in universe})

    ta = agreement(hp, cp, shared, universe)
    ga = agreement(goals_from_labels(hp), goals_from_labels(cp), shared, goals)

    pred = pairs_from_pipeline(dev_doc["results"])
    union = {pid: hp.get(pid, set()) | cp.get(pid, set()) for pid in shared}
    vh, vc, vu = prf(pred, hp), prf(pred, cp), prf(pred, union)

    want = SEQ_129
    checks = [
        ("target both_assigned", ta["both_assigned"], want["target_agreement"]["both_assigned"], 0),
        ("target only_first (Hermes)", ta["only_first"], want["target_agreement"]["only_first"], 0),
        ("target only_second (counsel)", ta["only_second"], want["target_agreement"]["only_second"], 0),
        ("target neither", ta["neither"], want["target_agreement"]["neither"], 0),
        ("target items", ta["items"], want["target_agreement"]["items"], 0),
        ("target agreement rate", ta["agreement_rate"], want["target_agreement"]["agreement_rate"], 4),
        ("target Cohen's kappa", ta["cohens_kappa"], want["target_agreement"]["cohens_kappa"], 3),
        ("target Jaccard", ta["jaccard"], want["target_agreement"]["jaccard"], 3),
        ("goal items", ga["items"], want["goal_agreement"]["items"], 0),
        ("goal agreement rate", ga["agreement_rate"], want["goal_agreement"]["agreement_rate"], 4),
        ("goal Cohen's kappa", ga["cohens_kappa"], want["goal_agreement"]["cohens_kappa"], 3),
        ("v1 precision vs Hermes", vh["precision"], want["pipeline_v1"]["hermes"]["precision"], 3),
        ("v1 recall vs Hermes", vh["recall"], want["pipeline_v1"]["hermes"]["recall"], 3),
        ("v1 precision vs counsel", vc["precision"], want["pipeline_v1"]["counsel"]["precision"], 3),
        ("v1 recall vs counsel", vc["recall"], want["pipeline_v1"]["counsel"]["recall"], 3),
        ("v1 precision vs the union", vu["precision"], want["pipeline_v1"]["union"]["precision"], 3),
        ("v1 recall vs the union", vu["recall"], want["pipeline_v1"]["union"]["recall"], 3),
        ("pairs either labeller made", vu["reference_pairs"],
         want["pipeline_v1"]["union"]["pairs_either_labeller_made"], 0),
        ("of those, the pipeline reached", vu["true_positives"],
         want["pipeline_v1"]["union"]["pipeline_reached"], 0),
    ]
    failures = [(n, g, w) for n, g, w, p in checks if not close(g, w, p)]
    if failures:
        print("SELF-PROOF FAILED against cordis-sdg seq 129:", file=sys.stderr)
        for n, g, w in failures:
            print("  %-32s recomputed %s, published %s" % (n, g, w), file=sys.stderr)
        sys.exit("refused: this script does not reproduce figures already on the "
                 "chain, so no new figure it computes can be trusted. %d of %d "
                 "checks failed." % (len(failures), len(checks)))

    return {
        "_what_this_is": (
            "Every figure published at cordis-sdg seq 129, recomputed here from "
            "the two committed label artefacts and the committed v1 output. All "
            "%d checks passed; the script refuses to report anything new if any "
            "one of them does not." % len(checks)),
        "checks_passed": len(checks),
        "first_labeller": h["labeller"], "first_sha256": h["_sha256"],
        "second_labeller": c["labeller"], "second_sha256": c["_sha256"],
        "pipeline_v1_output_sha256": dev_doc["_sha256"],
        "target_level": ta,
        "goal_level_secondary": ga,
        "pipeline_v1_vs_hermes": vh,
        "pipeline_v1_vs_counsel": vc,
        "pipeline_v1_vs_union": vu,
        "_ordering": (
            "Section 4.2: both development sets were uploaded and hashed before "
            "either was revealed, which is what makes this agreement figure "
            "mean anything."),
    }


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True,
                    help="the evaluation-100 pipeline output")
    ap.add_argument("--results-sha256", required=True)
    ap.add_argument("--dev-results", default="data/pipeline/development-50-v1.json",
                    help="the v1 development output seq 129 measured")
    ap.add_argument("--dev-results-sha256", required=True)
    ap.add_argument("--handoff", required=True,
                    help="the hand-off artefact the run read; its hash is "
                         "checked against the output's handoff_sha256")
    ap.add_argument("--reference", default="hermes-cordis-eval100-labels.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    dev_doc = load_output(ROOT / args.dev_results, args.dev_results_sha256,
                          args.dev_results)
    proof = self_proof(dev_doc)
    print("self-proof: %d of %d figures from cordis-sdg seq 129 reproduced"
          % (proof["checks_passed"], proof["checks_passed"]))
    print()

    out_doc = load_output(args.results, args.results_sha256, args.results)
    results = out_doc["results"]
    ref_doc = load_labels(args.reference, "evaluation")

    # The labeller and the pipeline must have read the same artefact. Section
    # 4.5: "All labellers work from that artefact and nothing else." If these
    # differ, every figure below compares two different inputs.
    if ref_doc["labelled_from_artefact_sha256"] != out_doc.get("handoff_sha256"):
        sys.exit("refused: the labeller read %s and the pipeline read %s."
                 % (ref_doc["labelled_from_artefact_sha256"],
                    out_doc.get("handoff_sha256")))
    if out_doc.get("freeze_seq") != FREEZE_SEQ:
        sys.exit("refused: the pipeline output records freeze_seq %r, not %d."
                 % (out_doc.get("freeze_seq"), FREEZE_SEQ))

    # The hand-off the ceiling reads must be the artefact the run actually
    # read, not merely a file with the right name.
    if sha256_of(args.handoff) != out_doc["handoff_sha256"]:
        sys.exit("refused: --handoff hashes to %s and the output records %s."
                 % (sha256_of(args.handoff), out_doc["handoff_sha256"]))
    handoff_records = json.loads(
        pathlib.Path(args.handoff).read_text(encoding="utf-8"))["projects"]

    reference = pairs_from_labels(ref_doc)
    predicted = pairs_from_pipeline(results)
    if set(reference) != set(predicted):
        sys.exit("refused: the label set covers %d projects and the output %d, "
                 "and they are not the same set."
                 % (len(reference), len(predicted)))

    order = [str(r["id"]) for r in results]
    report = {
        "_what_this_is": (
            "Registration section 4.7's metrics on the evaluation 100. The unit "
            "is one (project, target-URI) pair."),
        "registration_sha256": out_doc["registration_sha256"],
        "pipeline_output_sha256": out_doc["_sha256"],
        "parameters_values_sha256": out_doc["parameters_values_sha256"],
        "freeze_seq": out_doc["freeze_seq"],
        "handoff_sha256": out_doc["handoff_sha256"],
        "self_proof_against_seq_129": proof,
        "reference": {
            "file": ref_doc["_file"], "sha256": ref_doc["_sha256"],
            "labeller": ref_doc.get("labeller"),
            "served_model": ref_doc.get("served_model"),
            "projects": len(reference),
            "pairs": sum(len(v) for v in reference.values()),
            "projects_with_no_target": sum(1 for v in reference.values() if not v),
            "_sole_reference": (
                "Hermes Cordis's set is the sole reference for all 100. Section "
                "4.8 provides for Attila's call on the 20 he hand-labelled and "
                "Hermes's labels as the reference for the other 80; THE 20 WERE "
                "NEVER MADE, so there was nothing to adjudicate, no call was "
                "taken, and the limitation covers the whole hundred."),
        },
        "target_level": prf(predicted, reference),
        "goal_level_secondary": prf(goals_from_pipeline(results),
                                    goals_from_labels(reference)),
        "_goal_level_note": (
            "Goal level includes the pipeline's goal_level_only fallback rows, "
            "which carry a goal and no target. Target level excludes them: a "
            "project assigned at goal level made no target claim."),
        "inter_rater_agreement_evaluation_100": {
            "computed": False,
            "why": (
                "Section 4.7 specifies this as Hermes against Attila on his 20 "
                "only. The 20 were never made, so the evaluation set has ONE "
                "labeller and there is no pair to compare. No substitute is "
                "offered: comparing Hermes to the pipeline would be the "
                "pipeline's own accuracy reported a second time under a name "
                "that implies two humans."),
        },
        "human_anchor": {
            "made": False,
            "why": (
                "Section 4.3 provides for 20 of the 100 to be hand-labelled by "
                "Attila as the human anchor, and section 4.7 reports agreement "
                "against them separately. They were not made. The evaluation "
                "reference rests entirely on one automated labeller working "
                "blind, and nothing in this report is anchored to a human "
                "judgement."),
        },
        "confusion_cases_by_project_id": confusion(predicted, reference, order),
        "recall_ceiling": recall_ceiling(handoff_records, reference),
    }

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(report, indent=1, ensure_ascii=False) + "\n")

    t, g, rc = (report["target_level"], report["goal_level_secondary"],
                report["recall_ceiling"])
    print("EVALUATION 100, pipeline %s against %s"
          % (out_doc["_sha256"][:12], ref_doc.get("labeller")))
    print("  reference            %d pairs over %d projects, %d with no target"
          % (report["reference"]["pairs"], report["reference"]["projects"],
             report["reference"]["projects_with_no_target"]))
    print("  pipeline predicted   %d pairs" % t["predicted_pairs"])
    print("  target level         tp %-3d fp %-3d fn %-3d   P %-6s R %-6s F1 %s"
          % (t["true_positives"], t["false_positives"], t["false_negatives"],
             t["precision"], t["recall"], t["f1"]))
    print("  goal level           tp %-3d fp %-3d fn %-3d   P %-6s R %-6s F1 %s"
          % (g["true_positives"], g["false_positives"], g["false_negatives"],
             g["precision"], g["recall"], g["f1"]))
    print("  recall ceiling       %s — %d of %d reference pairs have any "
          "evidence at all" % (rc["ceiling"], rc["with_some_evidence"],
                               rc["reference_pairs"]))
    print("  disagreeing projects %d of %d"
          % (len(report["confusion_cases_by_project_id"]), len(order)))
    print()
    print("NOT COMPUTED, AND WHY")
    print("  inter-rater agreement on the 100 — Attila's 20 were never made, so")
    print("  there is one labeller and no pair to compare.")
    print("  the human anchor — not made.")
    print()
    print("wrote", out)


if __name__ == "__main__":
    main()
