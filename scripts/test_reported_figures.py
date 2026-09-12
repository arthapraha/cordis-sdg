#!/usr/bin/env python3
"""Every figure quoted in the prose must equal the artefact it came from.

    python scripts/test_reported_figures.py

WHY THIS EXISTS, AND WHY IT IS MINE TO WRITE. At cordis-sdg seq 289 I asked
another seat to guard against exactly this: numbers hard-coded into a page while
the artefact they came from can be regenerated, so they are right today and
silently wrong later. Counsel made it a condition at seq 291.

THE SAME HAZARD IS IN MY OWN DOCUMENTS. `README.md` and
`docs/description-document.md` quote 0.447, 0.221, 0.442, 0.677, 23,451, 53 of
95 and a dozen more as literal text. They are correct against `babd3741…` and
`03d79580…` today. Nothing made them fail if those artefacts moved.

Asking for a guard and not writing one for the same defect in my own deliverable
is the kind of thing this repository is supposed to catch, so here it is.

WHAT IT DOES NOT DO. It does not hunt for numbers in the prose and try to work
out what they mean; that would be a parser with opinions, and it would fail on
"seq 207" and "v10" and every other number in a sentence. Each claim below names
the document, the exact string that must appear in it, and the artefact
expression the string is computed from. If the artefact moves, the computed
string changes, the assertion fails, and the message says which document to fix
and what to.

IT IS A CHECK ON THE PROSE, NOT ON THE PIPELINE. A failure here means a document
is stale, never that a result is wrong.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DESCRIPTION = ROOT / "docs/description-document.md"
METRICS = ROOT / "data/pipeline/evaluation-100-metrics.json"
FIGURES = ROOT / "data/corpus/figures.json"


def thousands(n):
    return "{:,}".format(n)


def main():
    for p in (README, DESCRIPTION, METRICS, FIGURES):
        if not p.is_file():
            sys.exit("missing: %s" % p.relative_to(ROOT))

    def ratio3(tp, other):
        """Three decimals of the TRUE ratio, not of a stored rounding of it.

        The artefact stores precision to four decimals. Rounding 0.4085 by hand
        gives 0.409; the true value is 29/71 = 0.408451, which is 0.408. That
        double rounding is how the description document came to disagree with
        the notebook, and computing from the counts removes the intermediate
        step that caused it.
        """
        return "%.3f" % (tp / (tp + other)) if (tp + other) else "n/a"

    m = json.loads(METRICS.read_text(encoding="utf-8"))
    f = json.loads(FIGURES.read_text(encoding="utf-8"))
    t, g = m["target_level"], m["goal_level_secondary"]
    rc = m["recall_ceiling"]
    proof = m["self_proof_against_seq_129"]
    shape = f["corpus_shape"]
    cover = f["coverage"]
    unc = f["where_the_mapping_is_uncertain"]["disagreement_shape_on_the_evaluation_100"]
    bands = {d["key"]: d["count"] for d in f["confidence_bands"]}

    docs = {
        "README.md": README.read_text(encoding="utf-8"),
        "docs/description-document.md": DESCRIPTION.read_text(encoding="utf-8"),
    }

    # (document, what the claim is, the string that must appear)
    #
    # EVERY NEEDLE CARRIES ITS CONTEXT, and the first version of this file did
    # not. It searched for the bare string "0.447", which appears in the table
    # AND in the sentence about reading precision against the labellers' kappa —
    # so changing the table to 0.457 left the other occurrence and the check
    # passed. A check that cannot fail, written into the file whose whole
    # subject is checks that cannot fail. Whole table rows and full sentences
    # are used instead, so a needle matches in exactly one place or nowhere.
    D = "docs/description-document.md"
    R = "README.md"
    claims = [
        (D, "the evaluation table's target row",
         "| **target level** | %d | %d | %d | **%s** | **%s** | %s |"
         % (t["true_positives"], t["false_positives"], t["false_negatives"],
            ratio3(t["true_positives"], t["false_positives"]),
            ratio3(t["true_positives"], t["false_negatives"]), "%.3f" % t["f1"])),
        (D, "the evaluation table's goal row",
         "| goal level, secondary | %d | %d | %d | %s | %s | %s |"
         % (g["true_positives"], g["false_positives"], g["false_negatives"],
            ratio3(g["true_positives"], g["false_positives"]),
            ratio3(g["true_positives"], g["false_negatives"]), "%.3f" % g["f1"])),
        (D, "the reference's size",
         "%d pairs over %d projects, %d of which carry no target"
         % (m["reference"]["pairs"], m["reference"]["projects"],
            m["reference"]["projects_with_no_target"])),
        (D, "development kappa at target level",
         "| Cohen's kappa, target level | **%.3f** |" % proof["target_level"]["cohens_kappa"]),
        (D, "development kappa at goal level",
         "| Cohen's kappa, goal level | **%.3f** |" % proof["goal_level_secondary"]["cohens_kappa"]),
        (D, "development agreement rate and item count",
         "| agreement rate | %.4f over %s (project, target) items |"
         % (proof["target_level"]["agreement_rate"], thousands(proof["target_level"]["items"]))),
        (D, "the corpus row for projects scored",
         "| projects scored | **%s** |" % thousands(cover["projects_in_table"])),
        (D, "the corpus row for table rows",
         "| rows in the mapping table | %s |" % thousands(shape["rows"])),
        (D, "the corpus row for projects with a target",
         "| with at least one target | %s (%.1f%%) |"
         % (thousands(shape["projects_with_a_target"]),
            100 * shape["projects_with_a_target"] / cover["projects_in_table"])),
        (D, "the corpus row for goal-level-only projects",
         "| goal level only | %s (%.1f%%) |"
         % (thousands(shape["projects_goal_level_only"]),
            100 * shape["projects_goal_level_only"] / cover["projects_in_table"])),
        (D, "the corpus row for unassigned projects",
         "| **nothing at all** | **%s (%.1f%%)** |"
         % (thousands(shape["projects_unassigned"]),
            100 * shape["projects_unassigned"] / cover["projects_in_table"])),
        (D, "targets never assigned",
         "| targets never assigned anywhere | **%d of %d** |"
         % (len(f["least_linked_targets"]["targets_never_assigned"]),
            f["least_linked_targets"]["targets_in_taxonomy"])),
        (D, "the ceiling row",
         "| **recall ceiling** | **%.3f** |" % rc["ceiling"]),
        (D, "pairs with no evidence",
         "| **with no evidence at any threshold** | **%d** |"
         % rc["with_no_evidence_at_any_threshold"]),
        (D, "pairs with some evidence",
         "| with some evidence | %d |" % rc["with_some_evidence"]),
        (D, "the unreachable-pairs sentence",
         "**%d of %d pairs are not recoverable"
         % (rc["with_no_evidence_at_any_threshold"], rc["reference_pairs"])),
        (D, "the disagreement count",
         "Of the %d projects where the pipeline and" % unc["projects_disagreeing"]),
        (D, "recall-only disagreements",
         "**%d are recall-only**" % unc["recall_only"]),
        (D, "precision-only disagreements",
         "**%d are precision-only**, and %d disagree in both directions"
         % (unc["precision_only"], unc["both_directions"])),
        (D, "the band counts",
         "Of %s target assignments: **%s low, %s medium, %s high.**"
         % (thousands(sum(bands.values())), thousands(bands["low"]),
            thousands(bands["medium"]), thousands(bands["high"]))),
        (D, "the unassigned-corpus sentence",
         "**%s of %s projects get no assignment at all**"
         % (thousands(shape["projects_unassigned"]), thousands(cover["projects_in_table"]))),
        (D, "the mapping table hash", f["mapping_table_sha256"]),
        (D, "the pipeline commit", f["pipeline_commit"]),
        (D, "the snapshot hash", f["snapshot_sha256"]),
        (D, "the parameters values digest", m["parameters_values_sha256"]),
        (D, "the evaluation output hash", m["pipeline_output_sha256"]),
        (D, "the hand-off the run read", m["handoff_sha256"]),
        (D, "the reference label set hash", m["reference"]["sha256"]),
        (R, "the corpus size in the mapping-table section",
         "covers %s projects rather than 150" % thousands(cover["projects_in_table"])),
    ]

    failures = []
    for doc, what, needle in claims:
        if needle not in docs[doc]:
            failures.append((doc, what, needle))

    print("checked %d claims across %d documents" % (len(claims), len(docs)))

    if failures:
        print()
        for doc, what, needle in failures:
            print("FAIL: %s does not contain the current %s" % (doc, what))
            print("      expected to find: %r" % needle)
        sys.exit("%d of %d claims in the prose no longer match the artefacts. "
                 "Update the document; the artefacts are the record."
                 % (len(failures), len(claims)))
    print("every figure quoted in the prose matches the artefact it came from")


if __name__ == "__main__":
    main()
