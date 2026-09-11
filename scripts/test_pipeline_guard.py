#!/usr/bin/env python3
"""The guard that keeps the evaluation 100 unscored, and a test that can fail.

Registration v9, section 4.3: the owner's freeze word comes first, and only then
is the evaluation set scored. pipeline.py carries a guard for that, and the
README claimed the registration could not be breached by typing the wrong flag.

IT COULD, BY THE FLAG ONE WORD OVER. The guard tested `--set evaluation` and the
flag had a third choice, `--set all`, which the record filter admitted. Counsel
ran it and got 150 rows scored, 100 of them evaluation, exit 0 (cordis-sdg seq
127). A guard on one spelling of the thing it forbids is not a guard.

This file exists because that hole was found by a reader and not by a test. It
runs the real script as a subprocess, because the hole was in argument handling
and a unit test that imported run() would have passed while the script stayed
open. Every mode that could reach an evaluation record must exit non-zero and
write nothing.

    python scripts/test_pipeline_guard.py
"""

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "scripts/pipeline.py"
HANDOFF = ROOT / "data/sample/handoff-150.json"


def run(set_name, out_path):
    return subprocess.run(
        [sys.executable, str(PIPELINE), "--handoff", str(HANDOFF),
         "--set", set_name, "--out", str(out_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    if not HANDOFF.is_file():
        sys.exit("run scripts/build_handoff.py first")

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)

        # Every mode that can reach an evaluation record must refuse.
        for mode in ("evaluation", "all"):
            out = tmp / ("%s.json" % mode)
            r = run(mode, out)
            if r.returncode == 0:
                failures.append(
                    "--set %s exited 0; it must refuse. %s" %
                    (mode, "It wrote %d bytes." % out.stat().st_size
                     if out.exists() else "It wrote nothing, but still exited 0."))
            elif out.exists():
                failures.append("--set %s refused but still wrote a file" % mode)
            elif "4.3" not in (r.stderr + r.stdout):
                failures.append("--set %s refused without naming section 4.3" % mode)
            else:
                print("ok    --set %-11s refuses, names section 4.3, writes nothing" % mode)

        # And the one permitted mode must still work, or the guard has eaten the
        # pipeline rather than protected it.
        out = tmp / "development.json"
        r = run("development", out)
        if r.returncode != 0:
            failures.append("--set development exited %d: %s"
                            % (r.returncode, r.stderr.strip()[:200]))
        elif not out.exists():
            failures.append("--set development wrote nothing")
        else:
            doc = json.loads(out.read_text(encoding="utf-8"))
            sets = {row["set"] for row in doc["results"]}
            if sets != {"development"}:
                failures.append("--set development produced rows for %s" % sorted(sets))
            elif doc["projects"] != 50:
                failures.append("--set development scored %d projects, expected 50"
                                % doc["projects"])
            else:
                print("ok    --set development scores 50 development rows and no other")

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("All guard checks passed.")


if __name__ == "__main__":
    main()
