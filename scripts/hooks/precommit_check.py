#!/usr/bin/env python3
"""Refuse a commit whose generated artefacts do not reproduce, or whose verifiers fail.

Authorised by the owner in cordis-sdg at seq 157, on counsel's advice at seq 155.

WHY THIS EXISTS. Seven times in this build a control was reported as applying to
a tree it had not been run against, and twice that was a hash checked before the
last edit and quoted after. The discipline counsel imposed — run the reproduction
last — is a thing a person remembers. This makes it a property of the repository.

WHY IT REGENERATES INTO A SCRATCH COPY AND NEVER INTO THE TREE. The first version
of this hook, in my own recommendation, regenerated in place and then asked
whether the working tree was clean. That is a control that MUTATES THE THING IT
CHECKS: if a generator had drifted, the hook would overwrite the committed bytes
before anyone could see the difference, and the evidence would be gone by the
time the question was asked. Counsel caught it at seq 155, in a post I had
written about controls that cannot fail. The tree is never written here. A
temporary copy is built, the generators run inside it, and the results are
compared byte for byte against what is committed.

WHAT IT DELIBERATELY DOES NOT DO. It does not run the pipeline, the guard test or
the provenance test. Those take minutes, and a hook slow enough to be switched
off is the same failure wearing a different hat. They stay manual.

It also does not yet assert that no committed CSV row parses with a None key.
That assertion is owed inside the pipeline release, where the four affected files
are quoted in the same commit; adding it here first would block every commit
including the one that fixes it. Once verify_crosswalk.py carries it, this hook
picks it up for free, because it runs that verifier rather than reimplementing it.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Copied into the scratch tree. data/raw is 180 MB and mostly irrelevant here:
# only the taxonomy and the EuroSciVoc extract are read by anything this hook
# runs, so those two are copied and the rest is left alone.
COPY_DIRS = ["scripts", "data/terms", "data/crosswalk", "sources"]
COPY_FILES = [
    "data/raw/sdg-skos-ap-eu.rdf",
    "data/raw/cordis-horizon-projects/euroSciVoc.csv",
]

# (generator, artefacts it must reproduce byte for byte)
GENERATORS = [
    ("scripts/extract_targets.py", ["data/terms/sdg-targets.csv"]),
    ("scripts/extract_key_terms.py", ["data/terms/target-key-terms.csv"]),
]

VERIFIERS = ["scripts/verify_crosswalk.py", "scripts/verify_licences.py"]


def is_a_commit(payload):
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    return "git commit" in cmd or "git -c" in cmd and "commit" in cmd


def build_scratch(tmp):
    for d in COPY_DIRS:
        src = ROOT / d
        if src.is_dir():
            shutil.copytree(src, tmp / d,
                            ignore=shutil.ignore_patterns("__pycache__"))
    for f in COPY_FILES:
        src = ROOT / f
        if src.is_file():
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / f)


def run(script, cwd):
    return subprocess.run([sys.executable, script], cwd=str(cwd),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)          # not a hook payload we understand; do not block
    if not is_a_commit(payload):
        sys.exit(0)

    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        build_scratch(tmp)

        for script, artefacts in GENERATORS:
            # Remove the artefact from the scratch copy before regenerating it.
            # Without this the scratch already holds a copy of the committed
            # file, so a generator that exits 0 WITHOUT WRITING would be
            # compared against that copy and pass. Deleting first means "did not
            # produce" is distinguishable from "produced the same bytes", which
            # is the difference between a check that can fail and one that
            # cannot.
            for a in artefacts:
                (tmp / a).unlink(missing_ok=True)
            r = run(script, tmp)
            if r.returncode != 0:
                problems.append("%s failed in the scratch copy: %s"
                                % (script, r.stderr.strip()[:200]))
                continue
            for a in artefacts:
                committed, regenerated = ROOT / a, tmp / a
                if not regenerated.is_file():
                    problems.append("%s did not produce %s" % (script, a))
                elif not committed.is_file():
                    problems.append("%s is generated but not committed" % a)
                elif committed.read_bytes() != regenerated.read_bytes():
                    problems.append(
                        "%s does not reproduce: the committed file and a fresh "
                        "run of %s differ. The tree was NOT modified; regenerate "
                        "deliberately and stage the result." % (a, script))

        for v in VERIFIERS:
            r = run(v, tmp)
            if r.returncode != 0:
                tail = (r.stdout + r.stderr).strip().splitlines()
                problems.append("%s failed: %s" % (v, tail[-1] if tail else "?"))

    if problems:
        print("commit refused — the repository does not reproduce itself:",
              file=sys.stderr)
        for p in problems:
            print("  * %s" % p, file=sys.stderr)
        print("\nNothing in your working tree was changed by this check.",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
