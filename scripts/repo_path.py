#!/usr/bin/env python3
"""One helper, because one bug was written three times in one day.

`pathlib.Path.relative_to` RAISES when the path is not under the base. Every
script here that takes an `--out` announces the file it wrote with
`out.relative_to(ROOT)`, which is correct while `--out` points into the
repository and raises the moment it does not — after the file has been written,
correctly, and hashed correctly. The script then exits non-zero.

That is a script that FAILS AFTER SUCCEEDING, which a reader treats as a failed
build and a caller treats as an error. It is harmless where `--out` sits in the
tree, which is exactly why it survived: the seq-215 evaluation hand-off was
built into the tree and nobody saw it. It surfaced only when a reproduction
check wrote to a scratch directory.

By the time counsel named it at cordis-sdg seq 248 it existed in three scripts,
fixed inline in two of them within an hour of each other. Three inline fixes of
one mistake is a mistake about where the fix belongs, so it lives here.

NOT APPLIED TO EVERY relative_to IN scripts/. The others resolve fixed in-tree
constants — the taxonomy, the parameters, the committed vocabularies — which
cannot be outside the repository, and rewriting a call that cannot fail is churn
that has to be reviewed for nothing. This is for paths a caller chose.
"""

import pathlib


def shown(path, root):
    """The path as a reader should see it: relative to the repository if it is
    inside it, and whole if it is not. Never raises."""
    path = pathlib.Path(path)
    try:
        return path.relative_to(root)
    except ValueError:
        return path
