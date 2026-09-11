# The EuroSciVoc to SDG crosswalk

**Registration v9 `72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c`, section 3.1.**

> "A table from EuroSciVoc categories to SDG targets, built once, every row with a
> one-line justification citing the target's text, reviewed by Hermes (§4.6)
> before use, committed as data. The first of two load-bearing artefacts,
> reusable by CORDIS on its own."

`eurosciwoc-to-sdg.csv` is that table. This file says how it was built, what it
deliberately does not do, and what a reviewer should attack.

## What a row is

| column | meaning |
|---|---|
| `eurosciwoc_path` | the category, spelled as CORDIS spells it in the projects snapshot |
| `target_id` | an SDG target in the taxonomy snapshot, for example `7.2` |
| `strength` | `direct` or `contributing` |
| `justification` | one line, citing what the target's own text says |

**`direct`** means the category names the thing the target is about. Renewable
energy to target 7.2 is direct: the target's subject is the share of renewable
energy. **`contributing`** means the category is a route to the target rather
than its subject. Highway engineering to target 3.6 is contributing: the target
is about halving deaths from road traffic accidents, and road design bears on
that without being it.

**The distinction carries weight in section 3.5's scoring and is therefore part
of the claim, not a comment.** A reviewer who disagrees with a strength is
disagreeing with the entry, and should say so.

## How it was built, and the one thing that matters most

**Nothing in this table was derived from project text.** It was built from the
category vocabulary on one side and the taxonomy's target labels on the other.
The only project data consulted was the list of distinct `euroSciVocPath` values,
which is the table's own left-hand side. No objective, description, deliverable
or title was read. **That is what makes section 4's held-out evaluation set worth
anything**, and it is checkable: `scripts/verify_crosswalk.py` reads exactly the
same two sources and nothing else.

Rows were written at the **most specific level the evidence supports**, which is
usually a leaf or near-leaf category. Where a parent category maps and its
children map to the same target, only the level that carries the claim is listed.

## Coverage, stated plainly

| | |
|---|---|
| categories in the snapshot | 1,007 |
| categories with at least one row | 199 (19.8%) |
| rows | 235 |
| targets reached | 82 of 169 |
| goals reached | 17 of 17 |
| direct rows | 79 |
| contributing rows | 156 |

**Four fifths of the vocabulary is deliberately unmapped**, and that is the
result, not a gap to be filled. Categories like `natural sciences/physical
sciences/quantum physics`, `natural sciences/mathematics/applied mathematics` and
`humanities/languages and literature/linguistics` have no defensible one-line
justification against any target's text. **Inventing one would produce exactly
the superficial mapping criterion 2 penalises.** A project in an unmapped
category is not thereby unmapped: it reaches targets through section 3.4's
lexical evidence, which is the other load-bearing artefact and the one that reads
the project's own words.

**87 of the 169 targets have no crosswalk row**, mostly the means-of-
implementation targets and those about finance, trade and governance
arrangements, which a research discipline does not indicate. They too remain
reachable lexically.

## What a reviewer should attack

Section 4.6 scopes Hermes's pass as "a justification-versus-taxonomy check: does
each row's reason cite concepts that exist in the taxonomy snapshot and relate as
claimed. It is not a re-derivation of the crosswalk." The rows most worth that
scrutiny are these, and they are named rather than left to be found:

- **Nuclear energy is mapped to 7.1 and deliberately NOT to 7.2.** Target 7.2 is
  the share of *renewable* energy and nuclear is not renewable. Target 7.1 is
  affordable, reliable and modern energy services, which it can serve. If that
  reading is wrong it is wrong in a visible place.
- **Fossil energy and carbon capture are mapped to 7.a**, because 7.a's text
  names "advanced and cleaner fossil-fuel technology" within clean energy
  research. This will look wrong to a reader who has not read 7.a.
- **Hydrogen energy is `contributing`, not `direct`**, because hydrogen counts
  towards 7.2 only when produced from renewables, and the category alone does not
  say. The row says so.
- **Recycling carries two rows**, 12.5 and 6.3, and the 6.3 row is narrowed in
  its justification to water recycling only, because 6.3's "increasing recycling
  and safe reuse" is about water. A matcher that ignores the narrowing would
  over-fire.
- **Remote sensing, biosensing, synthetic biology, artificial intelligence and
  computer security** are all method categories whose justification depends on
  what they are applied to. Each is `contributing` and each justification says
  the evidence must name the application. **These are the rows most likely to be
  wrong in practice**, and the per-field evidence record in section 3.4 is how
  that gets checked rather than assumed.

## A defect in the source data, recorded so nobody silently "fixes" it

Exactly one of the 1,007 category paths carries a **trailing space**:
`engineering and technology/medical engineering/wearable medical technology `.
That is CORDIS's spelling, not a parsing artefact here. This table stores the
clean spelling, and every comparison strips surrounding whitespace on both sides.
**Any future join of this table to project rows must do the same**, or it will
silently miss that category. Embedding the invisible character in a committed CSV
was rejected: no reader could see it and most editors would strip it.
