#!/usr/bin/env python3
"""Regression tests for the two rule fixes in the section 3.5 release.

Both defects were found by counsel's plan review (cordis-sdg seq 149) and both
changed what the method does, so both are frozen into the submission if they are
not caught. Neither had a test; each has one now, and each test was written to
FAIL against the code as it stood.

  1. The negation window kept accumulating boundaries, so a match with two or
     more sentence boundaries behind it got an empty before-window and section
     3.3's rule could not fire. 224 of 847 matches on the development 50, 26.4%.

  2. A contributing crosswalk row was counted once per ROW rather than once per
     TARGET, so two "route to" claims summed to the weight of one "about" claim.
     100 (project, target) pairs on the corpus crossed the threshold only that
     way.

    python scripts/test_scoring_rules.py
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pipeline as P

ROOT = pathlib.Path(__file__).resolve().parent.parent


def negation_window_sees_the_sentence():
    """Two boundaries in the lookback must not swallow the window."""
    failures = []
    patterns = P.load_negation()

    one = "second sentence here. we do not study water quality at all."
    two = "first sentence here. second sentence here. we do not study water quality at all."
    for name, text in (("one boundary", one), ("two boundaries", two)):
        i = text.index("water quality")
        before, _ = P.sentence_window(text, i, i + len("water quality"))
        if not before:
            failures.append("%s: before-window is empty, so the negation rule "
                            "cannot fire" % name)
        elif P.negation_verdict(before, patterns) != "direct_negation":
            failures.append("%s: negation not detected in %r" % (name, before))
    # And the window must still stop AT the boundary rather than run past it:
    # text from the earlier sentence must not leak in.
    i = two.index("water quality")
    before, _ = P.sentence_window(two, i, i + len("water quality"))
    if "first sentence" in before:
        failures.append("the window reached back past the sentence boundary")
    return failures


def contributing_crosswalk_counts_once():
    """Two contributing rows for one target contribute once; two direct rows sum."""
    failures = []
    params = json.loads(P.PARAMS.read_text(encoding="utf-8"))
    w = params["evidence_weights"]

    def score_for(rows, target="7.2"):
        crosswalk = {}
        for i, strength in enumerate(rows):
            crosswalk["cat/%d" % i] = [{"target_id": target,
                                        "strength": strength,
                                        "justification": "test row"}]
        record = {"eurosciwoc_categories": list(crosswalk.keys())}
        per = P.score(record, [], crosswalk, params)
        return per[target]["score"]

    one_c = score_for(["contributing"])
    two_c = score_for(["contributing", "contributing"])
    if two_c != one_c:
        failures.append("two contributing rows scored %.2f, one scored %.2f — a "
                        "contributing row must count at most once per target"
                        % (two_c, one_c))

    one_d = score_for(["direct"])
    two_d = score_for(["direct", "direct"])
    if two_d <= one_d:
        failures.append("two direct rows scored %.2f, one scored %.2f — direct "
                        "rows are two independent reviewed claims and must sum"
                        % (two_d, one_d))

    # And the mixed case: a direct row plus a contributing row for the same
    # target is one of each, not a capped single.
    mixed = score_for(["direct", "contributing"])
    expect = w["crosswalk_direct"] + w["crosswalk_contributing"]
    if abs(mixed - expect) > 1e-9:
        failures.append("direct + contributing scored %.2f, expected %.2f"
                        % (mixed, expect))
    return failures


def band_assertion_is_wired():
    """The parameters must not allow a threshold below the low band's minimum."""
    params = json.loads(P.PARAMS.read_text(encoding="utf-8"))
    low = params["confidence_bands"]["low"]["min_score"]
    thr = params["assignment"]["threshold"]
    if low > thr:
        return ["committed parameters already violate low.min_score <= threshold"]
    return []


def main():
    failures = []
    for check in (negation_window_sees_the_sentence,
                  contributing_crosswalk_counts_once,
                  band_assertion_is_wired):
        found = check()
        name = check.__name__.replace("_", " ")
        print(("ok    " if not found else "FAIL  ") + name)
        failures.extend(found)

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("All scoring-rule checks passed.")


if __name__ == "__main__":
    main()
