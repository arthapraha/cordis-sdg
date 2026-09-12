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
PIPELINE = ROOT / "scripts/pipeline.py"
PARAMS = ROOT / "data/pipeline/parameters-v1.json"
HANDOFF = ROOT / "data/sample/handoff-150.json"


def run_pipeline(out_path):
    r = subprocess.run(
        [sys.executable, str(PIPELINE), "--handoff", str(HANDOFF),
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
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        backup = tmp / "parameters.bak"
        shutil.copy2(PARAMS, backup)
        try:
            baseline = run_pipeline(tmp / "baseline.json")
            print("baseline output", baseline[:16] + "…")

            # DIRECTION ONE: documentation must be inert.
            doc = json.loads(original)
            doc["_a_documentation_key_added_by_the_test"] = (
                "this must not move the output hash")
            doc["assignment"]["_another_one_nested"] = "nor must this"
            with open(PARAMS, "w", encoding="utf-8", newline="") as fh:
                fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            documented = run_pipeline(tmp / "documented.json")
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
            with open(PARAMS, "w", encoding="utf-8", newline="") as fh:
                fh.write(json.dumps(changed, indent=2, ensure_ascii=False) + "\n")
            moved = run_pipeline(tmp / "moved.json")
            if moved == baseline:
                failures.append(
                    "changing threshold %s -> %s left the output identical; the "
                    "output is not recording the parameters at all"
                    % (before, before + 0.5))
            else:
                print("ok    threshold %.1f -> %.1f              output changed"
                      % (before, before + 0.5))
        finally:
            shutil.copy2(backup, PARAMS)

    if PARAMS.read_text(encoding="utf-8") != original:
        failures.append("the test did not restore parameters-v1.json")
    else:
        print("ok    parameters-v1.json restored unchanged")

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("Both directions hold.")


if __name__ == "__main__":
    main()
