#!/usr/bin/env python3
"""Section 3.7: the explanation pass, which explains a decision already made.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 3.7: "For each assignment the model receives only the evidence rows and
writes two sentences a non-technical reader can check against them. Model name,
version, prompt text, parameters and the prompt's hash are recorded in the repo
and on every row. The model sees no project the rules did not already map, and
its output cannot add or remove an assignment."

THREE THINGS THIS FILE IS BUILT NOT TO BE ABLE TO DO.

It cannot see a project the pipeline did not map. It iterates the assignments in
the pipeline's own output; a project with no assignment is never sent.

It cannot see anything except the evidence. The prompt carries the target's
label, the matched phrases and their source fields, and the crosswalk
justification where one fired. It does NOT carry the objective, the title, the
abstract or any other project text, so the model cannot reason from the project
and then dress it up as reading the evidence.

It cannot change an assignment. The only field it writes is `explanation`, onto a
row whose target, score and confidence are already fixed. Nothing downstream
reads its output back into the decision.

On the LLM rule the notebook cites Q11 BY NUMBER, per section 9: all LLMs may be
used and the requirement is a transparent and reproducible methodology; Q11 warns
that a commercial API's reproducibility has inherent limits because the provider
may change the model. That is precisely why the per-row record below exists.

No credential is read from anywhere but the environment, by name, per section 9.
"""

import argparse
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

KEY_VAR = "ANTHROPIC_API_KEY"

PROMPT_TEMPLATE = """You are writing a short justification that a non-technical reader can check.

SDG target {target_id}: {target_label}

The evidence that this project was mapped to that target, and the only evidence
you may use:
{evidence}

Write exactly two sentences. The first says what the evidence shows. The second
says what it does not establish. Name at least one of the matched phrases
verbatim. Do not speculate about the project beyond the evidence above. Do not
use the words "clearly", "strongly" or "obviously".
"""


def evidence_block(assignment):
    lines = []
    for e in assignment["evidence"]:
        if e["source"] == "lexical":
            lines.append("- the phrase \"%s\" appears in the project's %s"
                         % (e["phrase"], e["field"].replace("_", " ")))
        else:
            lines.append("- the project is classified under \"%s\", which the "
                         "reviewed crosswalk maps to this target as %s evidence: %s"
                         % (e["category"], e["strength"], e["justification"]))
    return "\n".join(lines)


def build_prompt(assignment, target_label):
    return PROMPT_TEMPLATE.format(
        target_id=assignment["target_id"],
        target_label=target_label,
        evidence=evidence_block(assignment))


def load_target_labels():
    import csv
    path = ROOT / "data/terms/sdg-targets.csv"
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["target_id"]: r["target_label"]
                for r in csv.DictReader(fh, delimiter=";")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    results = json.loads(pathlib.Path(args.results).read_text(encoding="utf-8"))
    labels = load_target_labels()

    prompts = []
    for row in results["results"]:
        for a in row["assignments"]:
            prompts.append({
                "project_id": row["id"],
                "target_id": a["target_id"],
                "prompt": build_prompt(a, labels.get(a["target_id"], "")),
            })
    for p in prompts:
        p["prompt_sha256"] = hashlib.sha256(p["prompt"].encode("utf-8")).hexdigest()

    record = {
        "_what_this_is": "Section 3.7 explanation pass over a decision already "
                         "fixed by sections 3.4 to 3.6. The model cannot add or "
                         "remove an assignment.",
        "registration_sha256": results["registration_sha256"],
        "source_results_sha256": hashlib.sha256(
            pathlib.Path(args.results).read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256(
            PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
        "model_requested": args.model,
        "parameters": {"max_tokens": args.max_tokens,
                       "temperature": args.temperature},
        "llm_rule": "Q11 of the competition Q&A, cited by number per section 9",
        "explanations_to_write": len(prompts),
    }

    if not os.environ.get(KEY_VAR):
        # SECTION 9: "a per-run ceiling is stated in the notebook before the full
        # run and the run parks past it". The same discipline applies to a
        # missing credential: park, say so, and leave the prompts recorded so the
        # pass is a re-run and not a rebuild. No key is invented, no provider is
        # substituted, and nothing is written that pretends to be a model's work.
        record["status"] = "parked"
        record["parked_because"] = (
            "%s is not set in this environment. Section 9 forbids credentials in "
            "the repository or the room, so the key is read by name from the "
            "environment or the pass does not run." % KEY_VAR)
        record["prompts"] = prompts
        record["explanations"] = []
    else:
        sys.exit("a key is present but the provider call is not wired in this "
                 "commit; refusing to pretend otherwise")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(record, indent=1, ensure_ascii=False) + "\n")

    print("wrote", out)
    print("status:", record["status"])
    print("explanations to write:", len(prompts))
    print("distinct prompt hashes:", len({p["prompt_sha256"] for p in prompts}))
    if record["status"] == "parked":
        print("parked because:", KEY_VAR, "is not set")


if __name__ == "__main__":
    main()
