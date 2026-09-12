# Working rules for this repository

**Scope: this file carries the repository's rules and nothing else.** The
project's governance — who may ratify, freeze, merge or submit, and what each
seat may read — lives in the ratified registration and is not copied here. A rule
that lives in two places drifts, and this registration has paid for that four
times in its own sections. **If you want to know what is permitted, read the
registration; if you want to know how to write code here, read this.**

The registration in force is named in `README.md` with its sha256. Nothing in
this file overrides it.

---

## The one failure this repository keeps having

**A control reported as applying to a tree it was not run against.** Seven
instances so far, every one found by a reviewer rather than by the author:

- a marker-parity check that could not fail, cited as evidence a bug was fixed;
- a regression test that stashed the fix before running, so it tested the old code;
- a verifier that checked identifiers and never the content of what it verified;
- a script banner echoing the name that was *requested*, read as the identity *granted*;
- a guard testing one spelling of the thing it forbade, bypassed by the flag one word over;
- a reproduction hash checked before the last edit and quoted after;
- "both directions are tested", true of what was run and false of what was committed.

**The lesson is not "be more careful".** It is:

1. **A check must be able to fail.** Before trusting one, make it fail on purpose.
2. **A check must run against the state being claimed**, which means last, after
   the final edit, on the committed tree.
3. **A check must not share the assumption it is checking.** A verifier that
   parses a file the same wrong way as the code it verifies cannot see the bug.
4. **A check must not mutate what it checks.** Regenerate into a scratch copy and
   compare; never write into the tree and then ask whether the tree is clean.

`scripts/hooks/precommit_check.py` enforces 2 and 4 at commit time. It is not a
substitute for 1 and 3, which are yours.

---

## Writing files

**Every write uses `newline=""`.** Python translates `\n` to CRLF on Windows, git
stores LF, and the file then regenerates differently in the fresh clone that
counsel verifies from. This has cost three commits.

**`csv.writer` also needs `lineterminator="\n"`**, which it does not take from
`newline=""`.

**Quote every free-text column in a committed CSV.** These files are
semicolon-delimited and free text contains semicolons. Four committed files were
written with unquoted free text: 29 crosswalk justifications truncate where the
pipeline reads them, and two stop-list rows are column-shifted so the field that
states a rule displays the tail of the previous field instead.

This is the same defect the repository documents at length in
`scripts/read_projects.py` as a fault in CORDIS's export. **It was diagnosed in
someone else's data and reproduced in ours the same day**, because "their export
is broken" was treated as a fact about them rather than a property of the format.

---

## Hashes and provenance

**Hash the values, never the file.** An artefact that records the sha256 of a
parameters file makes documenting a parameter indistinguishable from changing
one. `pipeline.py` records `parameters_values_sha256`, computed with every
underscore-prefixed documentation key stripped.
`scripts/test_parameters_provenance.py` asserts both directions and must keep
passing.

**A hash you post is the hash the committed tree produces.** Run the
reproduction after the last edit, not before it. Both times this was got wrong,
the check itself was sound and the claim was about a different tree.

**Never transcribe a hash by hand.** Compute it, print it, paste it.

---

## Data

**`data/raw/` is never committed and never hand-edited.** It is 180 MB of
snapshot payload; `data/manifest.json` carries a sha256 for every file so a
re-download is verifiable without the bytes in git history.
`scripts/hooks/guard_paths.py` refuses writes there.

**`project.csv` is read only through `scripts/read_projects.py`.** A standard CSV
reader breaks 193 of its rows and silently corrupts 801 more. Do not add a second
reader.

**No credentials in the repository, ever.** Keys are read by name from the
environment. If a key is absent the run parks and says so; it does not invent
one, substitute a provider, or write output that pretends to be a model's work.

---

## Generated artefacts

`data/terms/sdg-targets.csv` and `data/terms/target-key-terms.csv` are generated
and committed. If you change a generator, regenerate and stage the result in the
same commit; the pre-commit hook refuses otherwise.

**Where a rule is written in prose and transcribed into code, the prose governs
and the code is the defect.** `data/terms/key-term-rule.md` says so explicitly and
has been right twice.

---

## Claims

**Do not assert a property of the data without computing it.** Every number that
has been wrong here was one nobody asked the data about: a count of lines read as
a count of rows, archive entries read as records, a denominator read as a
coincidence, a truncated label never measured for length.

**Name what was counted, not just the total.** "65 words, 8 theme, 19 generic, 20
structural, 18 verb" survives a miscount; "65" does not.

**When a measurement contradicts something already reported, withdraw it
explicitly** rather than adjusting it quietly. One figure here was reported with
an invented explanation attached; the number was wrong and the explanation was
worse.
