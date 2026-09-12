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

import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DESCRIPTION = ROOT / "docs/description-document.md"
LIMITATIONS = ROOT / "docs/limitations.md"
SUMMARY = ROOT / "docs/summary.md"
METRICS = ROOT / "data/pipeline/evaluation-100-metrics.json"
FIGURES = ROOT / "data/corpus/figures.json"
MAPPING = ROOT / "data/corpus/mapping-table-0246412.csv"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
TAXONOMY = ROOT / "data/terms/sdg-targets.csv"


def thousands(n):
    return "{:,}".format(n)


def main():
    for p in (README, DESCRIPTION, LIMITATIONS, SUMMARY, METRICS, FIGURES,
              MAPPING, CROSSWALK, TAXONOMY):
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

    import hashlib
    METRICS_SHA = hashlib.sha256(METRICS.read_bytes()).hexdigest()
    TAXONOMY_SHA = hashlib.sha256(TAXONOMY.read_bytes()).hexdigest()
    FIGURES_SHA = hashlib.sha256(FIGURES.read_bytes()).hexdigest()

    m = json.loads(METRICS.read_text(encoding="utf-8"))
    f = json.loads(FIGURES.read_text(encoding="utf-8"))
    t, g = m["target_level"], m["goal_level_secondary"]
    rc = m["recall_ceiling"]
    proof = m["self_proof_against_seq_129"]
    shape = f["corpus_shape"]
    cover = f["coverage"]
    unc = f["where_the_mapping_is_uncertain"]["disagreement_shape_on_the_evaluation_100"]
    bands = {d["key"]: d["count"] for d in f["confidence_bands"]}

    # The crosswalk's own coverage, counted from the crosswalk and the taxonomy
    # rather than copied from a sentence. docs/limitations.md section 1.6 turns
    # on "199 categories, 87 targets with none", and both move if a row is added.
    with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
        xrows = list(csv.DictReader(fh, delimiter=";"))
    crosswalk_categories = len({r["eurosciwoc_path"] for r in xrows})
    crosswalk_targets = len({r["target_id"] for r in xrows})
    with open(TAXONOMY, encoding="utf-8-sig", newline="") as fh:
        taxonomy_targets = len({r["target_id"] for r in csv.DictReader(fh, delimiter=";")})

    docs = {
        "README.md": README.read_text(encoding="utf-8"),
        "docs/description-document.md": DESCRIPTION.read_text(encoding="utf-8"),
        "docs/limitations.md": LIMITATIONS.read_text(encoding="utf-8"),
        "docs/summary.md": SUMMARY.read_text(encoding="utf-8"),
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
    L = "docs/limitations.md"
    S = "docs/summary.md"
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
        # THESE TWO MOVED FROM THE DESCRIPTION DOCUMENT TO docs/limitations.md
        # when section 6 became a pointer on the owner's word at cordis-sdg seq
        # 335. The check follows the prose; leaving them pointed at D would have
        # failed, and repointing them without moving the prose would have been
        # the check reporting on a document that no longer says it.
        (L, "the band counts",
         "Of %s target assignments: **%s low, %s medium, %s high.**"
         % (thousands(sum(bands.values())), thousands(bands["low"]),
            thousands(bands["medium"]), thousands(bands["high"]))),
        (L, "the unassigned-corpus sentence",
         "**%s of %s projects get no assignment at all**, and %d of the %d targets"
         % (thousands(shape["projects_unassigned"]), thousands(cover["projects_in_table"]),
            len(f["least_linked_targets"]["targets_never_assigned"]),
            f["least_linked_targets"]["targets_in_taxonomy"])),
        (D, "the mapping table hash", f["mapping_table_sha256"]),
        (D, "the pipeline commit", f["pipeline_commit"]),
        (D, "the snapshot hash", f["snapshot_sha256"]),
        (D, "the parameters values digest", m["parameters_values_sha256"]),
        (D, "the evaluation output hash", m["pipeline_output_sha256"]),
        (D, "the hand-off the run read", m["handoff_sha256"]),
        (D, "the reference label set hash", m["reference"]["sha256"]),
        (R, "the reproduction table's taxonomy hash",
         "| `data/terms/sdg-targets.csv` | `%s` |" % TAXONOMY_SHA),
        (R, "the reproduction table's frozen-run hash",
         "the frozen run | `%s` |" % m["pipeline_output_sha256"]),
        (R, "the reproduction table's metrics hash",
         "| `data/pipeline/evaluation-100-metrics.json` | `%s` |" % METRICS_SHA),
        (R, "the reproduction table's hand-off hash",
         "| `data/sample/handoff-evaluation-100.json` | `%s` |" % m["handoff_sha256"]),
        (R, "the corpus size in the mapping-table section",
         "covers %s projects rather than 150" % thousands(cover["projects_in_table"])),

        # docs/limitations.md — section 6 item 5's own deliverable.
        (L, "the ceiling in the section 1.1 heading",
         "### 1.1 Recall is bounded at %.3f by the method" % rc["ceiling"]),
        (L, "the ceiling row",
         "| **recall ceiling** | **%.3f** |" % rc["ceiling"]),
        (L, "pairs with no evidence",
         "| **with no evidence at any threshold** | **%d** |"
         % rc["with_no_evidence_at_any_threshold"]),
        (L, "pairs with some evidence",
         "| with some evidence | %d |" % rc["with_some_evidence"]),
        (L, "the unrecoverable-pairs sentence",
         "**%d of %d pairs are not recoverable by this method at any threshold.**"
         % (rc["with_no_evidence_at_any_threshold"], rc["reference_pairs"])),
        (L, "the goal-level-only count",
         "A further %s projects reach a goal" % thousands(shape["projects_goal_level_only"])),
        (L, "the crosswalk's coverage",
         "%d EuroSciVoc categories carry a crosswalk row and **%d of the %d targets have"
         % (crosswalk_categories, taxonomy_targets - crosswalk_targets, taxonomy_targets)),
        (L, "the disagreement table's total",
         "| projects where pipeline and reference disagree | %d |" % unc["projects_disagreeing"]),
        (L, "the disagreement table's recall-only row",
         "| **recall-only**, the pipeline found nothing the labeller found | **%d** |"
         % unc["recall_only"]),
        (L, "the disagreement table's precision-only row",
         "| **precision-only**, the pipeline found something the labeller did not | **%d** |"
         % unc["precision_only"]),
        (L, "the disagreement table's both-directions row",
         "| both directions | %d |" % unc["both_directions"]),
        (L, "improvement 3.1's honest scope",
         "**Would not fix** recall, which is %d of the %d disagreements."
         % (unc["recall_only"], unc["projects_disagreeing"])),
        (L, "improvement 3.2's goal-level population",
         "among the %s goal-level-only projects" % thousands(shape["projects_goal_level_only"])),
        (L, "improvement 3.2's residue",
         "**Would not fix** the %d pairs with no evidence at any threshold."
         % rc["with_no_evidence_at_any_threshold"]),

        # docs/summary.md — section 6 item 6. The owner's word at cordis-sdg seq
        # 335 requires every figure and hash on that page to be covered here, so
        # this block is the page read back line by line rather than a sample of
        # it. The two evaluation rows are computed from the counts by ratio3 for
        # the reason ratio3 exists.
        (S, "the evaluation table's target row",
         "| **target level** | %d | %d | %d | **%s** | **%s** | %s |"
         % (t["true_positives"], t["false_positives"], t["false_negatives"],
            ratio3(t["true_positives"], t["false_positives"]),
            ratio3(t["true_positives"], t["false_negatives"]), "%.3f" % t["f1"])),
        (S, "the evaluation table's goal row",
         "| goal level, secondary | %d | %d | %d | %s | %s | %s |"
         % (g["true_positives"], g["false_positives"], g["false_negatives"],
            ratio3(g["true_positives"], g["false_positives"]),
            ratio3(g["true_positives"], g["false_negatives"]), "%.3f" % g["f1"])),
        (S, "the reference's size",
         "The reference is %d pairs over %d projects, %d of which carry no target."
         % (m["reference"]["pairs"], m["reference"]["projects"],
            m["reference"]["projects_with_no_target"])),
        (S, "the ceiling",
         "a ceiling of **%.3f**" % rc["ceiling"]),
        (S, "the unrecoverable pairs",
         "**%d of %d reference pairs have no evidence at any threshold**"
         % (rc["with_no_evidence_at_any_threshold"], rc["reference_pairs"])),
        (S, "the disagreement shape",
         "`%d disagreeing, %d recall-only`"
         % (unc["projects_disagreeing"], unc["recall_only"])),
        (S, "development kappa",
         "`Cohen's kappa %.3f`" % proof["target_level"]["cohens_kappa"]),
        (S, "the corpus size",
         "the whole snapshot, %s Horizon Europe projects" % thousands(cover["projects_in_table"])),
        (S, "the corpus row for table rows",
         "| rows in the mapping table | %s |" % thousands(shape["rows"])),
        (S, "the corpus row for projects with a target",
         "| with at least one target | %s |" % thousands(shape["projects_with_a_target"])),
        (S, "the corpus row for goal-level-only projects",
         "| goal level only | %s |" % thousands(shape["projects_goal_level_only"])),
        (S, "the corpus row for unassigned projects",
         "| **nothing at all** | **%s** |" % thousands(shape["projects_unassigned"])),
        (S, "the band row",
         "| bands, of %s target assignments | %s low, %s medium, %s high |"
         % (thousands(sum(bands.values())), thousands(bands["low"]),
            thousands(bands["medium"]), thousands(bands["high"]))),
        (S, "the reproduction table's pipeline commit",
         "| frozen pipeline commit | `%s` |" % f["pipeline_commit"]),
        (S, "the reproduction table's snapshot hash",
         "| snapshot | `%s` |" % f["snapshot_sha256"]),
        (S, "the reproduction table's taxonomy hash",
         "| taxonomy | `%s` |" % TAXONOMY_SHA),
        (S, "the reproduction table's parameters digest",
         "| parameters, values digest | `%s` |" % m["parameters_values_sha256"]),
        (S, "the reproduction table's hand-off hash",
         "| evaluation hand-off | `%s` |" % m["handoff_sha256"]),
        (S, "the reproduction table's reference hash",
         "| reference label set | `%s` |" % m["reference"]["sha256"]),
        (S, "the reproduction table's frozen-output hash",
         "| frozen evaluation output | `%s` |" % m["pipeline_output_sha256"]),
        (S, "the reproduction table's metrics hash",
         "| metrics | `%s` |" % METRICS_SHA),
        (S, "the reproduction table's mapping-table hash",
         "| mapping table | `%s` |" % f["mapping_table_sha256"]),
        (S, "the reproduction table's figure-counts hash",
         "| figure counts | `%s` |" % FIGURES_SHA),
        (S, "the live prototype URL, which the page must end with",
         "**Live prototype: https://cordis-sdg-prototype.vercel.app/**"),
    ]

    # THE REGISTRATION IS NOW IN THE REPOSITORY, so this is a value check like
    # the other thirty-three rather than the agreement check it had to be.
    #
    # Until the owner's ruling at cordis-sdg seq 313 the registration lived only
    # in the room's artefact vault, so no file here could say what its hash
    # ought to be and the best available check was that the two documents named
    # the same 64 hex. A reader could verify every artefact in this repository
    # and not the sentence that governs them. Now the document is committed with
    # -text -diff, and both documents must name ITS hash.
    registration = ROOT / "docs/cordis-sdg-registration-v10.md"
    failures = []
    if not registration.is_file():
        failures.append(("docs/cordis-sdg-registration-v10.md",
                         "the ratified registration, committed", "the file itself"))
        reg_sha = None
    else:
        reg_sha = hashlib.sha256(registration.read_bytes()).hexdigest()
        # EVERY DOCUMENT HERE MUST NAME IT, and that is deliberate rather than
        # incidental: each of these is a deliverable a judge may open on its own,
        # and a deliverable that does not say which registration governs it is
        # one a reader has to take on trust. Adding a document to `docs` above
        # therefore adds this obligation with it.
        for doc, text in docs.items():
            found = re.findall(r"registration-v10[.]md`, sha256 `([0-9a-f]{64})`", text)
            if len(found) != 1:
                failures.append((doc, "exactly one registration hash (found %d)" % len(found), "—"))
            elif found[0] != reg_sha:
                failures.append((doc, "the committed registration's hash", reg_sha))

    # THE WORKED EXAMPLES NAME REAL ROWS OF THE COMMITTED MAPPING TABLE.
    #
    # docs/limitations.md section 2 argues from four projects by id, and quotes
    # each one's score and band. Those are the most perishable numbers in any of
    # these documents: they are single cells of a 28,833-row artefact, and a
    # reader who checks one and finds it stale has been told the wrong thing
    # about the one case the document chose to be concrete about. So each is
    # read back from the table and asserted, and a row that has vanished
    # entirely is its own failure rather than a needle that silently matches
    # nothing.
    examples = {("101113215", "4.6"), ("101203848", "5.2"), ("101203848", "2.2")}
    rows, goal_only = {}, {}
    with open(MAPPING, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            pid = row["project_id"]
            tid = row["sdg_target_uri"].rsplit("/", 1)[-1]
            if (pid, tid) in examples:
                rows[(pid, tid)] = row
            if pid == "101111215" and row["assignment_level"] == "goal_only":
                goal_only[pid] = row

    for pid, tid in sorted(examples):
        row = rows.get((pid, tid))
        if row is None:
            failures.append((L, "mapping-table row for project %s, target %s, "
                                "which section 2 works through" % (pid, tid),
                             "the row itself, which is no longer in the table"))
            continue
        claims.append((L, "project %s's %s row, as the table records it" % (pid, tid),
                       "`%s score %s band %s`"
                       % (tid, row["score"], row["confidence_band"])))

    if "101111215" in goal_only:
        claims.append((L, "project 101111215's goal-only score",
                       "`goal only, score %s`" % goal_only["101111215"]["score"]))
    else:
        failures.append((L, "the goal-level-only row for project 101111215",
                         "the row itself, which is no longer in the table"))

    # THE README'S DELIVERABLES TABLE MUST NAME PATHS THAT EXIST.
    #
    # The owner's word at cordis-sdg seq 335 requires README.md to list all eight
    # of registration section 6's deliverables by path. A list of paths is prose
    # that rots exactly like a figure does, and a judge follows it before reading
    # anything else.
    #
    # The paths are READ OUT OF THE TABLE rather than repeated here. A copy in
    # this file would pass while the README named something else, which is the
    # failure this repository keeps having: a check that shares the assumption it
    # is checking cannot see the bug.
    readme = docs["README.md"]
    head = "## The eight deliverables, by path"
    if head not in readme:
        failures.append((R, "the eight-deliverable table", head))
    else:
        section = readme[readme.index(head) + len(head):]
        section = section[:section.index("\n## ")]
        numbered = re.findall(r"^\| (\d+)\. ", section, re.M)
        if numbered != [str(i) for i in range(1, 9)]:
            failures.append((R, "eight deliverables numbered 1 to 8",
                             "rows numbered %s" % (", ".join(numbered) or "none")))
        named = [s for s in re.findall(r"`([^`]+)`", section)
                 if "/" in s or s.endswith(".txt")]
        if not named:
            failures.append((R, "any path at all in the deliverables table", "—"))
        for rel in named:
            if not (ROOT / rel.rstrip("/")).exists():
                failures.append((R, "a deliverable path that exists", rel))

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
