#!/usr/bin/env python3
"""Registration section 4.3's four conditions, each shown refusing on purpose.

    python scripts/test_pipeline_guard.py

WHAT THIS FILE IS FOR. A guard nobody has seen refuse is a guard nobody has
seen. The previous version of this file existed because a hole was found by a
reader rather than by a test: the guard tested `--set evaluation`, the flag had
a third choice `--set all`, and counsel ran it and scored 150 rows, 100 of them
evaluation, exit 0 (cordis-sdg seq 127). A guard on one spelling of the thing it
forbids is not a guard.

The four conditions, from the owner's word at cordis-sdg seq 219:

  1  _frozen.freeze_seq is present
  2  the parameters' values digest equals _frozen.parameters_values_sha256
  3  --freeze-seq is given explicitly and matches that record
  4  _frozen carries the sha256 of every rule file as at ab525b0, the run
     hashes the files it loads, and any difference refuses

Each case below breaks exactly one thing and asserts the refusal NAMES that
condition. A refusal that merely exits non-zero would pass a test that only
checked the exit code, while telling the person who ran it nothing.

IT RUNS AGAINST A COPY OF THE TREE, NEVER THE TREE. Conditions 2 and 4 are
tested by damaging parameters and rule files, and a test that damaged the real
ones would be a test that edits what it is checking. The copy also proves
something the guard claims: the digests are read from the tree the run is in.

NO CASE HERE SCORES A REAL EVALUATION RECORD, AND THAT DOES NOT DEPEND ON THE
GUARD WORKING. Every evaluation invocation breaks one condition and must refuse.
But the only way to learn whether these cases can fail is to weaken the guard and
watch them stop firing, and under a weakened guard they score whatever the
fixture holds. The first version of this file handed them the real
handoff-150.json, so that is exactly what happened: twice to counsel driving a
mutation at cordis-sdg seq 223, and to me the day I wrote it. The evaluation
records here are now three invented in this file. See scratch_handoff().

There is also deliberately no all-four-hold evaluation case: that run is the
frozen run, it happens once, and it happens on the owner's word and not inside a
test.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HANDOFF = "data/sample/handoff-150.json"
PARAMS = "data/pipeline/parameters-v1.json"
NL = chr(10)

# Built once in main() by scratch_handoff(); every scratch tree gets it.
FIXTURE = None


# Three evaluation records invented here, from constants, out of nothing. No
# line of this is derived from any real project: not an id, not a phrase, not a
# field. The prose names renewable energy and water quality so that a weakened
# guard visibly scores something rather than producing an empty file that could
# be mistaken for a refusal.
SYNTHETIC_EVALUATION = [
    {
        "id": "900000001",
        "acronym": "SYNTHETIC-A",
        "title": "SYNTHETIC TEST RECORD. Renewable energy for a test fixture.",
        "objective": "SYNTHETIC TEST RECORD, invented by scripts/"
                     "test_pipeline_guard.py. This project studies renewable "
                     "energy and the share of renewables in the energy mix.",
        "keywords": "renewable energy, solar energy",
    },
    {
        "id": "900000002",
        "acronym": "SYNTHETIC-B",
        "title": "SYNTHETIC TEST RECORD. Water quality for a test fixture.",
        "objective": "SYNTHETIC TEST RECORD, invented by scripts/"
                     "test_pipeline_guard.py. This project improves water "
                     "quality and wastewater treatment.",
        "keywords": "water quality, wastewater",
    },
    {
        "id": "900000003",
        "acronym": "SYNTHETIC-C",
        "title": "SYNTHETIC TEST RECORD. Nothing in particular.",
        "objective": "SYNTHETIC TEST RECORD, invented by scripts/"
                     "test_pipeline_guard.py. It is about nothing the "
                     "vocabulary covers, so it should score nothing.",
        "keywords": "(absent)",
    },
]


def scratch_handoff():
    """The real development 50, and THREE INVENTED evaluation records.

    THE EVALUATION RECORDS HERE ARE NOT REAL AND THAT IS THE POINT. Every
    evaluation case below breaks one condition and relies on the guard to refuse
    before scoring. When the guard is working that reliance is sound; when
    someone is deliberately weakening it — which is the only way to find out
    whether these cases can fail — the fixture is what stands between a broken
    guard and the held-out set.

    The first version of this file passed the real handoff-150.json. Counsel
    drove a mutation against it at cordis-sdg seq 223 and it scored the real
    evaluation 100 twice, in temp trees, deleted unopened; I had done the same
    thing the day I wrote it. A TEST THAT EXERCISES A DEFECT PERFORMS IT, and a
    fixture that only behaves while the code under test is correct is not a
    fixture. Now the worst a weakened guard can do here is score three records
    that were made up in this file.

    The development 50 stay real: they are not held out, the untouched-run case
    asserts the pipeline still scores all 50, and a synthetic development set
    would make that case prove nothing.
    """
    doc = json.loads((ROOT / HANDOFF).read_text(encoding="utf-8"))
    real = [r for r in doc["projects"] if r["set"] == "development"]
    if len(real) != 50:
        raise AssertionError("expected 50 development records, found %d" % len(real))
    template = real[0]
    made_up = []
    for spec in SYNTHETIC_EVALUATION:
        rec = {k: "(absent)" for k in template}
        rec.update(spec)
        rec["set"] = "evaluation"
        rec["editorial_description"] = "(absent)"
        rec["deliverable_descriptions"] = "(absent)"
        rec["eurosciwoc_categories"] = "(absent)"
        rec["participating_organisations"] = "(absent)"
        rec["countries"] = "(absent)"
        rec["source_note"] = ""
        rec["absent_fields"] = sorted(k for k, v in rec.items() if v == "(absent)")
        made_up.append(rec)
    doc["projects"] = real + made_up
    doc["what_this_is"] = (
        "NOT THE HAND-OFF. A fixture built by scripts/test_pipeline_guard.py: "
        "the real development 50, plus three evaluation records invented in "
        "that file. Never label from this and never score it for a result.")
    return doc


def build(tmp):
    """A working copy: the scripts, the two frozen trees, parameters, fixture."""
    dst = pathlib.Path(tmp) / "tree"
    (dst / "data/pipeline").mkdir(parents=True)
    (dst / "data/sample").mkdir(parents=True)
    shutil.copytree(ROOT / "scripts", dst / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data/terms", dst / "data/terms")
    shutil.copytree(ROOT / "data/crosswalk", dst / "data/crosswalk")
    shutil.copy2(ROOT / PARAMS, dst / PARAMS)
    (dst / HANDOFF).write_text(
        json.dumps(FIXTURE, indent=1, ensure_ascii=False) + NL,
        encoding="utf-8", newline="")
    return dst


def params(tree):
    return json.loads((tree / PARAMS).read_text(encoding="utf-8"))


def write_params(tree, doc):
    (tree / PARAMS).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + NL,
                               encoding="utf-8", newline="")


def invoke(tree, which, freeze_seq=None, out_name="out.json"):
    out = tree / out_name
    cmd = [sys.executable, str(tree / "scripts/pipeline.py"),
           "--handoff", str(tree / HANDOFF), "--set", which, "--out", str(out)]
    if freeze_seq is not None:
        cmd += ["--freeze-seq", str(freeze_seq)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r, out


def main():
    if not (ROOT / HANDOFF).is_file():
        sys.exit("run scripts/build_handoff.py first")

    global FIXTURE
    FIXTURE = scratch_handoff()
    made_up = [r for r in FIXTURE["projects"] if r["set"] == "evaluation"]
    real = [r for r in FIXTURE["projects"] if r["set"] == "development"]
    print("fixture: %d real development records, %d invented evaluation records "
          "(%s)" % (len(real), len(made_up),
                    ", ".join(r["id"] for r in made_up)))
    print()

    failures = []
    cases = []          # (label, mutate(tree), set, freeze_seq, expected phrase)

    def case(label, mutate, which, freeze_seq, expect):
        cases.append((label, mutate, which, freeze_seq, expect))

    # ---- condition 1 -------------------------------------------------------
    def drop_seq(t):
        d = params(t)
        d["_frozen"].pop("freeze_seq")
        write_params(t, d)
    case("1  freeze_seq deleted from _frozen", drop_seq,
         "evaluation", 207, "condition 1")

    # ---- condition 2 -------------------------------------------------------
    def move_threshold(t):
        d = params(t)
        d["assignment"]["threshold"] = 3.1
        write_params(t, d)
    case("2  assignment.threshold moved 3.0 -> 3.1", move_threshold,
         "evaluation", 207, "condition 2")

    def halve_a_weight(t):
        d = params(t)
        d["evidence_weights"]["crosswalk_direct"] = 1.5
        write_params(t, d)
    case("2  crosswalk_direct halved", halve_a_weight,
         "evaluation", 207, "condition 2")

    # ---- condition 3 -------------------------------------------------------
    case("3  --freeze-seq not given at all", lambda t: None,
         "evaluation", None, "condition 3")
    case("3  --freeze-seq 206, off by one", lambda t: None,
         "evaluation", 206, "condition 3")

    # ---- condition 4 -------------------------------------------------------
    def edit_rule_file(t):
        p = t / "data/terms/stop-list.csv"
        p.write_text(p.read_text(encoding="utf-8") + "zzz;the;appended" + NL,
                     encoding="utf-8", newline="")
    case("4  a line appended to data/terms/stop-list.csv", edit_rule_file,
         "evaluation", 207, "condition 4")

    def narrow_the_record(t):
        d = params(t)
        d["_frozen"]["rule_file_sha256"].pop("data/terms/sdg-targets.csv")
        write_params(t, d)
    case("4  sdg-targets.csv dropped from the record", narrow_the_record,
         "evaluation", 207, "condition 4")

    def corrupt_a_digest(t):
        d = params(t)
        d["_frozen"]["rule_file_sha256"]["data/terms/synonyms.csv"] = "0" * 64
        write_params(t, d)
    case("4  a recorded digest replaced with zeroes", corrupt_a_digest,
         "evaluation", 207, "condition 4")

    # The audit hook, and the reason it records the whole of data/ rather than
    # the two frozen trees: a loader added tomorrow that reads rule data from a
    # directory nobody froze. Run on DEVELOPMENT, to show condition 4 does not
    # wait for an evaluation record before it bites.
    def loader_from_an_unfrozen_directory(t):
        (t / "data/extra-terms").mkdir()
        (t / "data/extra-terms/more-synonyms.csv").write_text(
            "target_id;synonym;kind;note" + NL +
            "7.2;solar;subject;added tomorrow" + NL,
            encoding="utf-8", newline="")
        f = t / "scripts/pipeline.py"
        src = f.read_text(encoding="utf-8")
        old = '    for r in read_csv(TERMS / "synonyms.csv"):'
        if src.count(old) != 1:
            raise AssertionError(
                "the synonym loader no longer looks like %r, so this case is "
                "not testing what it says it is" % old)
        f.write_text(src.replace(old,
                     '    for r in (read_csv(ROOT / "data/extra-terms/'
                     'more-synonyms.csv")' + NL +
                     '               + read_csv(TERMS / "synonyms.csv")):'),
                     encoding="utf-8", newline="")
    case("4  a loader reads data/extra-terms/, frozen nowhere",
         loader_from_an_unfrozen_directory, "development", None, "condition 4")

    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, mutate, which, seq, expect) in enumerate(cases):
            tree = build(pathlib.Path(tmp) / ("c%d" % i))
            mutate(tree)
            r, out = invoke(tree, which, seq)
            said = r.stdout + r.stderr
            if r.returncode == 0:
                failures.append("%s: exited 0, it must refuse" % label)
            elif out.exists():
                failures.append("%s: refused but still wrote %s" % (label, out.name))
            elif expect not in said:
                failures.append("%s: refused without naming %r. It said: %s"
                                % (label, expect, " ".join(said.split())[:220]))
            else:
                print("ok    %-52s refuses, names %s" % (label, expect))

        # ---- the negative control condition 2 exists for ---------------------
        # Documentation keys are stripped before the values digest, so rewriting
        # a comment must NOT trip condition 2. Without this the cheapest way to
        # pass every case above is to hash the file, which would make every
        # explanatory note a false alarm — the exact defect of cordis-sdg seq
        # 132. On the development set: a passing evaluation run is the frozen
        # run and does not belong in a test.
        tree = build(pathlib.Path(tmp) / "neg")
        d = params(tree)
        d["_frozen"]["_note"] = "this note has been entirely rewritten."
        d["evidence_weights"]["_note"] = "so has this one."
        d["assignment"]["_brand_new_documentation_key"] = "and this is new."
        write_params(tree, d)
        r, out = invoke(tree, "development")
        if r.returncode != 0:
            failures.append("negative control: rewriting comments tripped a "
                            "condition. It said: %s"
                            % " ".join((r.stdout + r.stderr).split())[:220])
        elif not out.exists():
            failures.append("negative control: exited 0 but wrote nothing")
        else:
            doc = json.loads(out.read_text(encoding="utf-8"))
            if doc["projects"] != 50:
                failures.append("negative control scored %d, expected 50"
                                % doc["projects"])
            else:
                print("ok    %-52s does NOT trip condition 2"
                      % "2  three comments rewritten, no value touched")

        # ---- and the pipeline still works ------------------------------------
        tree = build(pathlib.Path(tmp) / "ok")
        r, out = invoke(tree, "development")
        if r.returncode != 0 or not out.exists():
            failures.append("an untouched development run exited %d: %s"
                            % (r.returncode, " ".join(r.stderr.split())[:220]))
        else:
            doc = json.loads(out.read_text(encoding="utf-8"))
            sets = {row["set"] for row in doc["results"]}
            opened = set(doc["rule_files_this_run_opened"])
            recorded = set(doc["rule_file_sha256"])
            stray = sorted(p for p in opened
                           if p not in recorded and p not in {PARAMS, HANDOFF})
            if sets != {"development"}:
                failures.append("development run produced rows for %s" % sorted(sets))
            elif len(recorded) != 8:
                failures.append("the output records %d rule digests, expected 8"
                                % len(recorded))
            elif stray:
                failures.append("the output reports opening %s, which nothing "
                                "covers" % stray)
            else:
                print("ok    %-52s scores 50, records 8 digests, opens %d files"
                      % ("an untouched development run", len(opened)))

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print()
    print("All four conditions refuse on purpose. %d cases." % (len(cases) + 2))


if __name__ == "__main__":
    main()
