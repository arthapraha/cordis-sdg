#!/usr/bin/env python3
"""The provenance property, as a test that can fail for someone other than me.

Registration v9, section 3.5. The pipeline's output records
`parameters_values_sha256` rather than the hash of `parameters-v1.json`, so that

    documenting a parameter  ->  the output does not move
    changing a parameter     ->  the output moves

I checked both directions by hand, reported them as tested, and committed no
test. Counsel's note at cordis-sdg seq 137: "both directions are tested" was true
of what I ran and not of what I committed, so the property would not survive the
next editor. That is the seventh time in this build a control has been described
as applying when nothing committed enforced it, and the previous six were all
found by someone else.

This file is that control. It edits a scratch copy of the parameters, never the
committed file, so a failure cannot leave the repository dirty.

    python scripts/test_parameters_provenance.py
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARAMS = ROOT / "data/pipeline/parameters-v1.json"
HANDOFF = ROOT / "data/sample/handoff-150.json"
NEWLINE = chr(10)


def build_tree(tmp):
    """A working copy, because this test edits the FROZEN parameters.

    THE EARLIER VERSION EDITED THE REAL FILE AND RESTORED IT IN A `finally`.
    That is a check writing to the artefact registration section 3.5 froze — to
    prove a property OF that artefact. It restored correctly every time and the
    blast radius was small, since a half-restored file fails the guard's second
    condition and shows in `git status`. It was still the shape CLAUDE.md warns
    about: a control that mutates what it checks. A scratch tree costs a copy
    and removes the question, which is what test_pipeline_guard.py already does.
    """
    dst = pathlib.Path(tmp) / "tree"
    (dst / "data/pipeline").mkdir(parents=True)
    (dst / "data/sample").mkdir(parents=True)
    shutil.copytree(ROOT / "scripts", dst / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data/terms", dst / "data/terms")
    shutil.copytree(ROOT / "data/crosswalk", dst / "data/crosswalk")
    shutil.copy2(PARAMS, dst / "data/pipeline/parameters-v1.json")
    shutil.copy2(HANDOFF, dst / "data/sample/handoff-150.json")
    return dst


def run_pipeline(tree, out_path):
    r = subprocess.run(
        [sys.executable, str(tree / "scripts/pipeline.py"),
         "--handoff", str(tree / "data/sample/handoff-150.json"),
         "--set", "development", "--out", str(out_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("pipeline failed: %s" % (r.stderr.strip()[:300]))
    import hashlib
    return hashlib.sha256(out_path.read_bytes()).hexdigest()


def main():
    for path in (PARAMS, HANDOFF):
        if not path.is_file():
            sys.exit("missing %s — run the earlier steps first" % path.name)

    original = PARAMS.read_text(encoding="utf-8")
    original_bytes = PARAMS.read_bytes()
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        tree = build_tree(tmp)
        scratch = tree / "data/pipeline/parameters-v1.json"
        baseline = run_pipeline(tree, tmp / "baseline.json")
        print("baseline output", baseline[:16] + "…")

        # DIRECTION ONE: documentation must be inert.
        doc = json.loads(original)
        doc["_a_documentation_key_added_by_the_test"] = (
            "this must not move the output hash")
        doc["assignment"]["_another_one_nested"] = "nor must this"
        with open(scratch, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        documented = run_pipeline(tree, tmp / "documented.json")
        if documented != baseline:
            failures.append(
                "adding documentation keys moved the output: %s -> %s"
                % (baseline[:16], documented[:16]))
        else:
            print("ok    documentation keys added        output unchanged")

        # DIRECTION TWO: a real parameter must NOT be inert. A test that only
        # checked direction one would pass on a pipeline that recorded no
        # provenance at all.
        changed = json.loads(original)
        before = changed["assignment"]["threshold"]
        changed["assignment"]["threshold"] = before + 0.5
        with open(scratch, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(changed, indent=2, ensure_ascii=False) + "\n")
        moved = run_pipeline(tree, tmp / "moved.json")
        if moved == baseline:
            failures.append(
                "changing threshold %s -> %s left the output identical; the "
                "output is not recording the parameters at all"
                % (before, before + 0.5))
        else:
            print("ok    threshold %.1f -> %.1f              output changed"
                  % (before, before + 0.5))

        # DIRECTION THREE, AND IT IS THE ONE THAT ISOLATES THE PROPERTY.
        #
        # Direction two moves the threshold, which moves the SCORES, so the
        # output hash moves whether or not the parameters are recorded in it at
        # all. Measured: with `parameters_values_sha256` replaced by a constant,
        # directions one and two both still pass. The comment above claimed
        # direction two covered that case and it does not.
        #
        # This one changes a parameter that CANNOT change a scored row. The cap
        # is five, no development project reaches it — the most any row carries
        # is four and the overflow count is zero on all fifty — so raising it to
        # six leaves every row byte-identical. The only route left for the
        # output to move is the recorded digest, so if the output does not move,
        # the provenance is not being recorded.
        inert = json.loads(original)
        cap = inert["assignment"]["max_targets_per_project"]
        inert["assignment"]["max_targets_per_project"] = cap + 1
        with open(scratch, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(inert, indent=2, ensure_ascii=False) + NEWLINE)
        inert_hash = run_pipeline(tree, tmp / "inert.json")
        rows_same = (json.loads((tmp / "inert.json").read_text(encoding="utf-8"))["results"]
                     == json.loads((tmp / "baseline.json").read_text(encoding="utf-8"))["results"])
        if not rows_same:
            failures.append(
                "raising the cap %d -> %d changed a scored row, so this probe "
                "no longer isolates the provenance; pick another inert "
                "parameter" % (cap, cap + 1))
        elif inert_hash == baseline:
            failures.append(
                "raising the cap %d -> %d changed no row AND left the output "
                "hash identical, so the output is not recording the parameters"
                % (cap, cap + 1))
        else:
            print("ok    cap %d -> %d, no row moved       output changed anyway"
                  % (cap, cap + 1))
    # Nothing to restore: the committed file was never opened for writing.
    if PARAMS.read_bytes() != original_bytes:
        failures.append("the committed parameters file changed during this test")
    else:
        print("ok    the committed parameters file was never written to")

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("All three directions hold.")


if __name__ == "__main__":
    main()
