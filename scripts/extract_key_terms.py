#!/usr/bin/env python3
"""Apply the committed key-term extraction rule to the 169 SDG target labels.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 3.2. THE RULE IS data/terms/key-term-rule.md AND THIS FILE IS ITS
TRANSCRIPTION. The rule was written first. Where the two disagree the markdown is
the rule and this script is the defect; the step numbers below are that file's
step numbers so the two can be read side by side.

This script reads the taxonomy-derived target list and this repository's own
stop-list. IT NEVER READS PROJECT TEXT. That is what keeps section 4's
development and evaluation split meaningful: a vocabulary tuned, even
accidentally, on the corpus it will be matched against is not a held-out test of
anything.

Writes data/terms/target-key-terms.csv.
"""

import collections
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "data/terms/sdg-targets.csv"
STOPLIST = ROOT / "data/terms/stop-list.csv"
OUT = ROOT / "data/terms/target-key-terms.csv"

# Step 1. The deadline preamble.
PREAMBLE = re.compile(r"^by\s+\d{4},?\s+", re.I)

# Step 2. The indicator parenthetical.
PARENTHETICAL = re.compile(r"\([^)]*\)")

# Step 3. Span separators, longest first so " as well as " wins over " as ".
SEPARATORS = [
    " as well as ", " such as ", " in particular ", " including ",
    " and/or ", " and ", " or ", ";", ":", ",",
]

# Step 4. Verbs of commitment, longest first for the same reason.
COMMITMENT_VERBS = [
    "substantially reduce", "substantially increase", "significantly reduce",
    "achieve", "adopt", "build", "create", "develop", "double", "eliminate",
    "end", "enhance", "ensure", "eradicate", "expand", "facilitate", "halve",
    "implement", "improve", "increase", "maintain", "promote", "protect",
    "provide", "reduce", "strengthen", "support", "sustain", "take", "upgrade",
]

# Step 5. Function words stripped from the EDGES of a span only. A word in this
# list that sits inside a span is kept, because "access to energy" is a term and
# "access" and "energy" separately are not.
EDGE_WORDS = {
    "a", "an", "the", "of", "to", "for", "in", "on", "at", "by", "with",
    "from", "into", "through", "their", "its", "our", "that", "which",
    "is", "are", "be", "being", "been", "as", "s",
    "all", "any", "such", "other", "more", "most", "least",
    "substantially", "significantly", "progressively", "particularly",
    "especially", "inter", "alia", "appropriate", "relevant", "national",
    "global", "international", "per", "cent", "proportion", "share", "number",
    "level", "levels",
}

# Step 8.
DISCRIMINATING_LIMIT = 4


def load_stop_terms():
    """The generic stop-list, used by step 6 only.

    Only terms whose class is generic, theme or structural gate step 6. The verb
    class is already handled by step 4 and is listed in that file for a reader's
    benefit, not for this one.
    """
    if not STOPLIST.is_file():
        sys.exit("missing stop-list: %s" % STOPLIST.relative_to(ROOT))
    terms = set()
    with open(STOPLIST, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            terms.add(row["term"].strip().lower())
    return terms


def split_spans(text):
    """Step 3."""
    spans = [text]
    for sep in SEPARATORS:
        out = []
        for s in spans:
            out.extend(s.split(sep))
        spans = out
    return [s.strip() for s in spans if s.strip()]


def strip_commitment_verb(span):
    """Step 4."""
    low = span.lower()
    for verb in sorted(COMMITMENT_VERBS, key=len, reverse=True):
        if low.startswith(verb + " "):
            return span[len(verb) + 1:].strip()
        if low == verb:
            return ""
    return span


def strip_edges(span):
    """Step 5."""
    words = [w for w in re.split(r"\s+", span) if w]
    while words and re.sub(r"[^a-z]", "", words[0].lower()) in EDGE_WORDS:
        words.pop(0)
    while words and re.sub(r"[^a-z]", "", words[-1].lower()) in EDGE_WORDS:
        words.pop()
    return " ".join(words)


def head_phrase(span):
    """Step 7. The last two or three words, minus trailing function words."""
    words = [w for w in span.split() if w]
    if len(words) <= 3:
        return ""
    head = strip_edges(" ".join(words[-3:]))
    if head and head != span and len(head.split()) >= 2:
        return head
    head = strip_edges(" ".join(words[-2:]))
    return head if head and head != span and len(head.split()) >= 2 else ""


def normalise(term):
    term = re.sub(r"[^a-z0-9\s\-]", " ", term.lower())
    return re.sub(r"\s+", " ", term).strip()


def main():
    if not TARGETS.is_file():
        sys.exit("run scripts/extract_targets.py first: %s missing"
                 % TARGETS.relative_to(ROOT))
    stop_terms = load_stop_terms()

    with open(TARGETS, encoding="utf-8", newline="") as fh:
        targets = list(csv.DictReader(fh, delimiter=";"))

    emitted = []
    for t in targets:
        label = t["target_label"]
        text = PREAMBLE.sub("", label)                      # step 1
        text = PARENTHETICAL.sub(" ", text)                 # step 2
        seen = set()
        for raw in split_spans(text):                       # step 3
            span = strip_commitment_verb(raw)               # step 4
            span = strip_edges(span)                        # step 5
            term = normalise(span)
            if not term:
                continue
            words = term.split()
            # Step 6 gates the FULL span only.
            if 1 <= len(words) <= 6 and not all(w in stop_terms for w in words):
                if term not in seen:
                    seen.add(term)
                    emitted.append((t, term, raw.strip(), 6))
            # Step 7 runs whether or not step 6 kept the span above. A span of
            # more than six words is dropped by step 6 but its head is exactly
            # what was wanted; gating step 7 on step 6 left eight targets with
            # no term at all, target 7.2 among them.
            head = normalise(head_phrase(span))
            if head and head not in seen:
                hw = head.split()
                if 1 <= len(hw) <= 6 and not all(w in stop_terms for w in hw):
                    seen.add(head)
                    emitted.append((t, head, raw.strip(), 7))

    # step 8
    counts = collections.Counter(term for _, term, _, _ in emitted)
    rows = []
    for t, term, source, step in emitted:
        rows.append({
            "target_uri": t["target_uri"],
            "target_id": t["target_id"],
            "goal_id": t["goal_id"],
            "term": term,
            "source_span": source,
            "emitted_by_step": step,
            "target_count": counts[term],
            "discriminating": "no" if counts[term] > DISCRIMINATING_LIMIT else "yes",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        # lineterminator is explicit: the csv module writes CRLF by default even
        # with newline="", which would make a regeneration in a fresh clone
        # differ from the committed file on every line.
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    non_disc = sum(1 for r in rows if r["discriminating"] == "no")
    per_target = collections.Counter(r["target_id"] for r in rows)
    print("wrote", OUT.relative_to(ROOT))
    print("terms:", len(rows), "over", len(per_target), "targets")
    print("distinct terms:", len(counts))
    print("marked not discriminating (emitted by more than %d targets): %d"
          % (DISCRIMINATING_LIMIT, non_disc))
    print("targets with no term at all:",
          [t["target_id"] for t in targets if t["target_id"] not in per_target] or "none")
    print("fewest terms:", per_target.most_common()[-3:])


if __name__ == "__main__":
    main()
