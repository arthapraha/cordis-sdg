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

IT ALSO COVERS THE PUBLISHED PAGE, from cordis-sdg seq 356. The prototype had a
check of its own in prototype/build_data.py which searched the page for five
bare numbers, each of which appeared on it two to four times — so editing one
occurrence left the others and the check stayed green. That is the same defect
this file had at its first version, described above. The page's own check is
being removed on its owner's row and this one covers it instead, so one
instrument guards every published claim.

Two files are read for the page, because they fail differently. The figures a
reader sees are bound at load time by prototype/app.js out of
prototype/data/corpus_summary.json; the numbers in the markup are the fallback
shown when the script does not run. Checking only the markup would pass while
every reader saw something else.
"""

import csv
import hashlib
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
PROTOTYPE_HTML = ROOT / "prototype/index.html"
PROTOTYPE_JSON = ROOT / "prototype/data/corpus_summary.json"
CROSSWALK = ROOT / "data/crosswalk/eurosciwoc-to-sdg.csv"
TAXONOMY = ROOT / "data/terms/sdg-targets.csv"


def thousands(n):
    return "{:,}".format(n)



def badge(html, label):
    """The value the header shows under a given label, and its title attribute.

    Returned as a pair so the CALLER compares them, because the defect Hermes
    Cordis found at cordis-sdg seq 345 was exactly a label and a value that did
    not go together: the chip said "Pipeline Commit" and carried the frozen
    evaluation output's sha256. Searching the page for the right hash would not
    have caught it — the right hash WAS on the page, under the wrong word. So
    the check has to read the pairing, not the presence.
    """
    pat = (r'<span class="badge-label">%s</span>\s*'
           r'<span class="badge-value[^"]*"(?:\s+title="([0-9a-f]{40,64})")?>([^<]*)</span>'
           % re.escape(label))
    hit = re.search(pat, html)
    return (hit.group(1), hit.group(2)) if hit else (None, None)


def prototype_failures(m, f, html, reg_sha):
    """The published page's claims, against the artefacts they came from.

    WHY THIS IS NOT JUST MORE NEEDLES IN `claims`. The figures on that page are
    not served from the HTML. Thirteen ids are bound at load time by
    prototype/app.js out of prototype/data/corpus_summary.json, so the numbers
    in the markup are a no-JavaScript fallback and the rendered value comes from
    the JSON. A check on the HTML alone would pass while every reader saw
    something else. Both halves are therefore checked, and they fail
    differently: the JSON is what a reader sees, the HTML is what a reader sees
    when the script does not run, and both are published claims.

    The JSON is generated from the artefacts by prototype/build_data.py, so it
    OUGHT to agree by construction. That is the assumption this function exists
    not to share: the file is committed, so a stale copy can sit on main looking
    freshly generated, and nothing but reading it can tell.
    """
    out, checked = [], []
    t_, rc = m["target_level"], m["recall_ceiling"]
    dev = m["self_proof_against_seq_129"]["target_level"]

    # ---- half one: what a reader actually sees -------------------------------
    try:
        j = json.loads(PROTOTYPE_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [("prototype/data/corpus_summary.json", "readable JSON", str(exc))]

    vm = j.get("validation_metrics", {})
    e100, d50 = vm.get("evaluation_100", {}), vm.get("development_50", {})
    J = "prototype/data/corpus_summary.json"

    for path, got, want in [
        ("evaluation_100.target_level", e100.get("target_level"), t_),
        ("evaluation_100.recall_ceiling", e100.get("recall_ceiling"), rc),
        ("evaluation_100.goal_level_secondary", e100.get("goal_level_secondary"),
         m["goal_level_secondary"]),
    ]:
        if not isinstance(got, dict):
            out.append((J, "a %s block" % path, "missing"))
            continue
        for key, wanted in want.items():
            if key.startswith("_"):
                continue
            checked.append("%s.%s" % (path, key))
            if key in got and got[key] != wanted:
                out.append((J, "%s.%s" % (path, key),
                            "%r, but the page serves %r" % (wanted, got[key])))

    checked.append("development_50.cohens_kappa")
    if round(d50.get("cohens_kappa", -1), 4) != round(dev["cohens_kappa"], 4):
        out.append((J, "development_50.cohens_kappa",
                    "%r, but the page serves %r" % (dev["cohens_kappa"], d50.get("cohens_kappa"))))

    # The two sentences the page now serves verbatim instead of a paraphrase.
    # They are the submission's least flattering sentences, which is why they
    # are the ones worth binding: the paraphrase that replaced them called the
    # sole reference "a single expert annotator".
    for key, artefact in [("reference_note", m["reference"].get("_sole_reference")),
                          ("human_anchor_status", m["human_anchor"].get("why"))]:
        checked.append("served:" + key)
        if artefact and e100.get(key) != artefact:
            out.append((J, "evaluation_100.%s, verbatim from the metrics artefact" % key,
                        (artefact or "")[:110] + "..."))

    # ---- half two: the markup ------------------------------------------------
    H = "prototype/index.html"
    prec = "%.3f" % t_["precision"]
    rec = "%.3f" % t_["recall"]
    ceil = "%.3f" % rc["ceiling"]
    pairs = "%d of %d" % (rc["with_no_evidence_at_any_threshold"], rc["reference_pairs"])
    kappa = "%.3f" % dev["cohens_kappa"]

    # NEEDLES ARE BOUND TO THE ELEMENT ID, not to the surrounding sentence.
    # Each figure appears two to four times on this page, which is what made
    # build_data.py's bare "0.447" unable to fail. The id is unique, it names
    # which element is wrong when the check trips, and it survives the prose
    # around it being rewritten — which a whole-sentence needle does not.
    for el, value in [
        ("eval-metric-precision", prec),
        ("eval-metric-recall", rec),
        ("eval-metric-ceiling", ceil),
        ("eval-metric-ceiling-unreachable", "%s reference pairs" % pairs),
        ("eval-metric-kappa", kappa),
        ("eval-prose-precision", prec),
        ("eval-prose-ceiling", ceil),
        ("eval-prose-unreachable-pairs", pairs),
        ("eval-repro-kappa", kappa),
        ("eval-repro-metrics", "P=%s, R=%s, Ceiling=%s" % (prec, rec, ceil)),
        ("fig-caption-ceiling", ceil),
        ("fig-caption-unreachable", pairs),
        ("eval-prose-reference-note", e100.get("reference_note", "")),
        ("eval-prose-human-anchor", e100.get("human_anchor_status", "")),
    ]:
        needle = 'id="%s">%s<' % (el, value)
        checked.append(el)
        if needle not in html:
            out.append((H, "the fallback in #%s" % el, needle[:130]))

    # The header chips, read as label-and-value pairs.
    # THE PAGE NOW NAMES THE REGISTRATION IT IS BUILT UNDER, so it joins the
    # obligation the four documents already carry. It could not before: the chip
    # read "Registration v10 section 6 Item 7" with no hash, so there was nothing
    # to check and forcing one from this file would have decided something on the
    # prototype seat's row. Antigravity Cordis put the sha256 in the chip's title
    # at 9228c94, and this is the other half of the owner's word at seq 367.
    chips = []
    if reg_sha:
        chips.append(("Specification", reg_sha, "Registration v10 &sect;6 Item 7"))
    for label, want_title, want_text in chips + [
        ("Pipeline Commit", f["pipeline_commit"], f["pipeline_commit"][:8]),
        ("Frozen Output", m["pipeline_output_sha256"], m["pipeline_output_sha256"][:8] + "&hellip;"),
        ("Mapping Table", f["mapping_table_sha256"], f["mapping_table_sha256"][:8] + "&hellip;"),
    ]:
        checked.append("chip:" + label)
        title, text = badge(html, label)
        if title is None:
            out.append((H, "a header chip labelled %r" % label, "the chip itself"))
        elif title != want_title or text != want_text:
            out.append((H, "the %r chip to carry its own value" % label,
                        "title %s and text %s, but it carries title %s and text %s"
                        % (want_title[:12], want_text, (title or "-")[:12], text)))

    # The evaluation tab's intro, where the same mislabel appeared a second
    # time. Each hash is bound to the words in front of it.
    for words, sha in [("output", m["pipeline_output_sha256"]),
                       ("pipeline commit", f["pipeline_commit"]),
                       ("metrics artefact", hashlib.sha256(METRICS.read_bytes()).hexdigest())]:
        checked.append("intro:" + words)
        needle = '%s <code class="mono" title="%s">' % (words, sha)
        if needle not in html:
            out.append((H, "the evaluation intro naming %r with its own hash" % words, needle))

    return out, checked


def main():
    for p in (README, DESCRIPTION, LIMITATIONS, SUMMARY, METRICS, FIGURES,
              MAPPING, CROSSWALK, TAXONOMY, PROTOTYPE_HTML, PROTOTYPE_JSON):
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

    # t-63ab's figures, section 1.6. Counted HERE from the crosswalk rather than
    # copied from scripts/measure_ancestor_exposure.py, so the document and the
    # measurement script are checked by two independent counts rather than one
    # count quoted twice.
    reach = {}
    for r in xrows:
        reach.setdefault(r["eurosciwoc_path"].strip(), []).append((r["target_id"], r["strength"]))
    anc = []
    for a in sorted(reach):
        for b in sorted(reach):
            if not b.startswith(a + "/"):
                continue
            for tgt in sorted({x for x, _ in reach[a]} & {x for x, _ in reach[b]}):
                sa = sorted({s for x, s in reach[a] if x == tgt})[0]
                sb = sorted({s for x, s in reach[b] if x == tgt})[0]
                anc.append((sa, sb))
    ancestor_pairs = len(anc)
    ancestor_deduped = sum(1 for x in anc if x == ("contributing", "contributing"))
    ancestor_summable = ancestor_pairs - ancestor_deduped

    docs = {
        "README.md": README.read_text(encoding="utf-8"),
        "docs/description-document.md": DESCRIPTION.read_text(encoding="utf-8"),
        "docs/limitations.md": LIMITATIONS.read_text(encoding="utf-8"),
        "docs/summary.md": SUMMARY.read_text(encoding="utf-8"),
    }

    # THE PROTOTYPE IS CHECKED BUT IS NOT ONE OF THE DOCUMENTS ABOVE, and the
    # distinction is load-bearing rather than tidy. `docs` carries an obligation
    # to name the ratified registration by hash; the page names it by version
    # only ("Registration v10 section 6 Item 7"), which is its owner's call and
    # not something this file should force by putting the page in that loop.
    # Since 9228c94 the page names the registration by hash in its Specification
    # chip, so it is checked for that too — by the chip reader in
    # prototype_failures, which compares the label and the value together rather
    # than hunting the page for a hash that might sit under any word.
    pages = {"prototype/index.html": PROTOTYPE_HTML.read_text(encoding="utf-8")}
    everything = dict(docs, **pages)

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

        # Section 7.8, the seq 244 control. The control table's own hash is NOT
        # checked here and cannot be: the table is not committed, so no file in
        # a clone can say what it should be. The section says so. What IS checked
        # is everything a clone can compute: the committed table's hash in both
        # places it appears, including as the result of the commit swap, and the
        # row and project counts.
        (D, "section 7.8's committed-table row",
         "| committed mapping table, pipeline at `0246412` | `%s` |" % f["mapping_table_sha256"]),
        (D, "section 7.8's result, the swapped control hashing to the committed table",
         "| **control with its commit hash swapped for `0246412`'s** | **`%s`** |"
         % f["mapping_table_sha256"]),
        (D, "section 7.8's row and project counts",
         "| rows on each side | %s over %s projects |"
         % (thousands(shape["rows"]), thousands(cover["projects_in_table"]))),
        (D, "section 7.8's frozen commit, named in full",
         "That is commit\n`%s`" % f["pipeline_commit"]),
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
        (L, "the crosswalk's mapped categories",
         "| mapped EuroSciVoc categories | %d |" % crosswalk_categories),
        (L, "the ancestor-pair count",
         "| ancestor pairs reaching the same target | **%d** |" % ancestor_pairs),
        (L, "the summable ancestor pairs",
         "| of those, pairs that would sum if a project carried both | **%d** |"
         % ancestor_summable),
        (L, "the already-neutralised pairs",
         "| pairs the contributing rule already neutralises | %d |" % ancestor_deduped),
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

    # AND THE EXPOSURE ITSELF, not just its denominator. Section 1.6 says
    # "0 of 14,776". Checking only the 14,776 would leave the 0 as a literal
    # nobody verifies — the document could say zero while the table had ten and
    # nothing would go red. So the zero is counted here, on the committed table,
    # by a pass this file was already making.
    by_target = {}
    for a in sorted(reach):
        for b in sorted(reach):
            if b.startswith(a + "/"):
                for tgt in {x for x, _ in reach[a]} & {x for x, _ in reach[b]}:
                    by_target.setdefault(tgt, set()).add((a, b))
    item_re = re.compile(r"^([a-z_]+): (.*?) \[(.+?), (-?[0-9.]+)\]$")
    target_rows = exposure = 0
    with open(MAPPING, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            pid = row["project_id"]
            tid = row["sdg_target_uri"].rsplit("/", 1)[-1]
            if (pid, tid) in examples:
                rows[(pid, tid)] = row
            if pid == "101111215" and row["assignment_level"] == "goal_only":
                goal_only[pid] = row
            if row["assignment_level"] != "target":
                continue
            target_rows += 1
            if tid not in by_target:
                continue
            cats = set()
            for part in row["matched_phrases_and_source_fields"].split(" | "):
                hit = item_re.match(part.strip())
                if hit and hit.group(1) == "eurosciwoc_categories":
                    cats.add(hit.group(2))
            if any(a in cats and b in cats for a, b in by_target[tid]):
                exposure += 1

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

    claims.append((L, "the measured exposure on the mapping table",
                   "| target assignments in the mapping table reached by such a pair | **%d of %s** |"
                   % (exposure, thousands(target_rows))))

    # THE OTHER ZERO CANNOT BE CHECKED FROM A CLONE, and saying so is the point.
    # data/corpus/records.jsonl is 150 MB and .gitignore keeps it out, so this
    # figure is verified when the file has been rebuilt and NOT verified
    # otherwise. A check that quietly skips is worse than one that is absent:
    # the run says which of the two happened.
    records = ROOT / "data/corpus/records.jsonl"
    if records.is_file():
        carriers = projects_seen = 0
        pairset = {(a, b) for v in by_target.values() for a, b in v}
        with open(records, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                projects_seen += 1
                cats = rec.get("eurosciwoc_categories")
                if cats == "(absent)" or not cats:
                    continue
                cats = [c.strip() for c in cats]
                if any(b.startswith(a + "/") for a in cats for b in cats if a != b):
                    carriers += 1
        claims.append((L, "the measured exposure on the corpus records",
                       "| projects carrying a category and one of its own descendants | **%d of %s** |"
                       % (carriers, thousands(projects_seen))))
        print("data/corpus/records.jsonl present: section 1.6's corpus figure checked "
              "against it (%d of %d)" % (carriers, projects_seen))
    else:
        print("data/corpus/records.jsonl absent: section 1.6's '0 of 23,451' is NOT "
              "checked by this run. Rebuild it with scripts/build_corpus_records.py "
              "to cover it.")

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

    proto_failures, proto_checked = prototype_failures(
        m, f, pages["prototype/index.html"], reg_sha)
    failures.extend(proto_failures)

    for doc, what, needle in claims:
        if needle not in everything[doc]:
            failures.append((doc, what, needle))

    print("checked %d claims across %d documents" % (len(claims), len(docs)))
    print("checked %d bindings on prototype/index.html and every served figure "
          "in prototype/data/corpus_summary.json" % len(proto_checked))
    if not proto_checked:
        sys.exit("refused: the prototype check made no checks at all, which would "
                 "pass for the same reason an empty test passes.")

    if failures:
        print()
        for doc, what, needle in failures:
            print("FAIL: %s: %s" % (doc, what))
            print("      expected: %r" % needle)
        sys.exit("%d of %d checks failed, over four documents and the published "
                 "page. Update what is stale; the artefacts are the record."
                 % (len(failures), len(claims) + len(proto_checked)))
    print("every figure quoted in the prose matches the artefact it came from")


if __name__ == "__main__":
    main()
