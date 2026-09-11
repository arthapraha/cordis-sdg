# Negation and context rule

**Registration v9 `72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c`, section 3.3.**

> "a committed negation/context rule says **when a match near a negation or a 'not related to' phrase is discarded**. Both exist before the first full run and change only by amendment to this registration."

This file is the rule. `negation-patterns.csv` is its machine-readable form. Like
the key-term rule, it was written before it was run and before any project text
was read, and the script is a transcription of it.

## What this rule is for, and what it is not for

A lexical matcher that finds "renewable energy" cannot tell the difference
between a project that builds renewable energy systems and one that says its
method is **not** applicable to renewable energy. Research prose contains the
second kind of sentence often, because stating scope exclusions is what a good
objective does. **This rule discards a match when the text around it says the
project is not doing that thing.**

It is not a sentiment rule and it is not an attempt to read intent. It fires on
a short, fixed list of surface patterns, in a stated window, and it does nothing
else. **Every discard is recorded on the project's row with the pattern that
caused it**, so a reader can see what was thrown away and disagree with it.

## The rule

Let a **match** be an occurrence of a committed key term or synonym in one of
section 3.4's five source fields.

**1. The window is the sentence containing the match.** Sentence boundaries are
`.`, `?`, `!` followed by whitespace, or a newline. If no boundary is found
within 300 characters either side, the window is those 300 characters. The
sentence is the window because a negation in the previous sentence usually
governs the previous subject, and widening past it produced, in the judgement
behind this rule, more wrong discards than right ones.

**2. A match is discarded if a pattern in `negation-patterns.csv` of class
`scope_exclusion` appears anywhere in the window before the match**, within 60
characters of it. These are phrases that announce something is out of scope:
"not related to", "does not address", "outside the scope of", "with the exception
of", "other than".

**3. A match is discarded if a pattern of class `direct_negation` appears within
5 words before the match.** These are ordinary negations attached to the term
itself: "no", "not", "without", "neither", "nor", "never", "lack of", "absence
of", "failure to".

**4. A match is NOT discarded by a negation that is part of the target's own
subject.** Several targets are about ending, eliminating or reducing a bad thing,
so text saying a project reduces something is evidence FOR that target, not
against it. Patterns of class `negative_subject` — "reduce", "reduction of",
"eliminate", "prevent", "mitigate", "combat", "tackle", "avoid", "decrease",
"minimise", "minimize" — **suppress rules 2 and 3 for that match**. Without this
carve-out the rule would discard exactly the evidence that targets 1.1, 3.4, 6.3,
12.4 and 13.1 are looking for.

**5. A match inside a comparison or a citation is discarded**: patterns of class
`comparison` — "unlike", "in contrast to", "as opposed to", "compared with",
"compared to", "rather than", "instead of" — within 40 characters before the
match. Project prose uses these to position work against a field it is not in.

**6. Order of application.** Rule 4 is evaluated first and is decisive. If no
`negative_subject` pattern applies, rules 2, 3 and 5 are evaluated in that order
and the first that fires discards the match and is recorded as the reason.

**7. Nothing else discards a match.** In particular, the rule does not consider
the confidence of the match, the field it came from, or how many other matches
the project has. Those belong to section 3.5's scoring, not here.

## What this rule will get wrong, stated in advance

- **Multi-clause sentences.** "The project does not model combustion, but does
  optimise renewable energy dispatch" will discard the renewable energy match
  under rule 3 if the negation falls within the five-word window. The sentence
  window is too blunt for this and a clause parser is out of scope for a rule a
  reader can run by hand.
- **Negations after the match.** "Renewable energy is not considered here" is not
  caught, because rules 2, 3 and 5 all look backwards only. Looking forwards as
  well was considered and rejected: it roughly doubles the discard rate in
  hand-checking on the target labels themselves, and the asymmetry of English
  scope-marking means a following negation more often belongs to a later clause.
- **The carve-out in rule 4 is deliberately broad**, so it will protect some
  matches that should have been discarded. That direction of error is the one
  this entry prefers, because a false positive is visible on the mapping row with
  its evidence phrase and a reader can reject it, whereas a silent discard is
  not.

**Every one of these is a limitation to report under criterion 7, not a defect to
hide.** The count of discards by pattern class, and the count of matches
protected by rule 4, are reported with the results.

## Tuning

Section 3.5 permits the stop-list and this rule to be tuned **on the development
50 only**, and then frozen by the owner's word before the evaluation set is
scored. **Nothing in this file has been tuned on any project text.** It was
written from the target labels and from general knowledge of how research
objectives are written, before the sample was drawn. That is recorded here so the
first tuning pass has a baseline it can be compared against.
