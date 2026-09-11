#!/usr/bin/env python3
"""The seeded draw of 150 projects, and its 50/100 split.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 4.1: "One seeded draw of 150 projects from the snapshot, the seed and the
draw recorded in the notebook. Split by the same seed into 50 development and 100
evaluation."

THE SEED IS THE RATIFIED REGISTRATION'S OWN HASH. It was pre-registered in
cordis-sdg at seq 119, before this script ran and before any id was drawn. A
freely chosen seed is one that could have been chosen after looking at the
result, and nobody could ever prove otherwise; this one was fixed by the owner's
ratifying line at seq 86, before a draw existed.

NO RANDOM MODULE IS USED. random.sample would tie the draw to one language's
generator and, worse, to a particular version of it. The order here is a keyed
sha256 sort, which any language reproduces for ever:

    key(id)  = sha256(SEED + ":" + id) as lowercase hex
    order    = ids sorted ascending by (key, id)
    drawn    = first 150
    development = drawn[0:50]     evaluation = drawn[50:150]

The population is every project id in the snapshot: 23,451, read through
read_projects, which parses the file the way CORDIS actually writes it. An
earlier reader dropped 193 rows it could not parse and the population was
reported three times as 23,258 before anyone asked the data what it meant.

Writes data/sample/development-50.txt, evaluation-100.txt and draw.json.
"""

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import read_projects

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/sample"

SEED = "72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c"
DRAW_SIZE = 150
DEVELOPMENT_SIZE = 50


def key(project_id):
    return hashlib.sha256((SEED + ":" + project_id).encode("utf-8")).hexdigest()


def digest(ids):
    """sha256 of the id list, one per line, no trailing newline.

    Stated exactly because counsel and the builder compare these digests to find
    out whether they drew the same sample, and a trailing newline would make two
    correct draws look different.
    """
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def main():
    header, rows = read_projects.load()
    population = sorted({r[0] for r in rows})
    if len(population) != len(rows):
        sys.exit("population is not one id per row: %d ids, %d rows"
                 % (len(population), len(rows)))

    drawn = sorted(population, key=lambda i: (key(i), i))[:DRAW_SIZE]
    development = drawn[:DEVELOPMENT_SIZE]
    evaluation = drawn[DEVELOPMENT_SIZE:]

    if len(set(drawn)) != DRAW_SIZE:
        sys.exit("the draw is not distinct")
    if set(development) & set(evaluation):
        sys.exit("the split overlaps")

    OUT.mkdir(parents=True, exist_ok=True)
    # newline="" on every write in this repository. Python translates "\n" to
    # CRLF on Windows by default, git stores LF, and the file then regenerates
    # differently in the fresh clone counsel checks it from. This is the third
    # time that trap has appeared here, after the manifest and the derived term
    # files, which is why it is a comment and not just a keyword argument.
    for name, ids in (("development-50", development), ("evaluation-100", evaluation)):
        with open(OUT / (name + ".txt"), "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(ids))

    record = {
        "registration_sha256": SEED,
        "seed": SEED,
        "seed_is": ("the ratified registration's own hash, pre-registered in "
                    "cordis-sdg at seq 119 before this script was run"),
        "method": ("order the population ascending by (sha256(seed + ':' + id), id); "
                   "take the first 150; positions 1-50 are development, 51-150 "
                   "are evaluation"),
        "population_size": len(population),
        "population_source": "field 0 of project.csv, read through scripts/read_projects.py",
        "draw_size": DRAW_SIZE,
        "development_size": len(development),
        "evaluation_size": len(evaluation),
        "development_sha256": digest(development),
        "evaluation_sha256": digest(evaluation),
        "digest_definition": "sha256 of the id list, one id per line, no trailing newline",
    }
    with open(OUT / "draw.json", "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    print("population:", len(population))
    print("development 50 sha256:", record["development_sha256"])
    print("evaluation 100 sha256:", record["evaluation_sha256"])
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
