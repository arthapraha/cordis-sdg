# Key-term extraction rule

**Registration v9 `72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c`, section 3.2.**

> "Matching therefore runs against **key terms extracted from each target's label by a stated, committed rule** plus a curated synonym list per target, both committed as data and reviewed. **The extraction rule is written down before it is run.**"

This file is the rule. It was written before `scripts/extract_key_terms.py` was
run for the first time, and the script is a transcription of it, not the other
way round. If the two ever disagree, this file is the rule and the script is the
defect.

## Why a rule at all

SDG target labels are long UN sentences. Target 6.3 is 49 words. Matched whole
against a project objective, a target label fires against nothing, ever. Matched
as a bag of its own words, it fires against everything, because those words are
"water", "quality", "global" and "by 2030". **Neither extreme is a method**, so
the label has to be reduced to the terms that carry its meaning, by a rule
someone can run by hand and check.

## The rule, in order

Each of the 169 target labels is processed as follows. Every step is
case-insensitive; output terms are lowercased.

**1. Strip the deadline preamble.** Remove a leading `By <year>, ` or
`By <year> ` (for example "By 2030, " and "By 2020, "). It dates the target, not
its subject, and it appears in 120 of the 169 labels, so it would otherwise be
the most frequent term in the vocabulary.

**2. Strip the indicator parenthetical.** Remove any text in parentheses. In these
labels parentheses carry measurement notes and examples ("currently measured as
people living on less than $1.25 a day"), not the target's subject.

**3. Split into candidate spans** at commas, semicolons, colons, and at the
conjunctions ` and `, ` or `, ` including `, ` in particular `, ` such as `,
` as well as `. A UN target sentence is a list of commitments joined this way,
and each span is a separate thing the target asks for.

**4. Strip leading verbs of commitment** from each span. The verbs are the ones
these labels use to introduce an action rather than name a subject: achieve,
adopt, build, create, develop, double, eliminate, end, enhance, ensure, eradicate,
expand, facilitate, halve, implement, improve, increase, maintain, promote,
protect, provide, reduce, strengthen, substantially reduce, support, sustain,
take, upgrade. Their presence is what makes a span a commitment; the subject is
what follows them.

**5. Drop function words** at the **edges** of each remaining span, repeatedly,
from both ends. A word on this list that sits **inside** a span is kept, because
"access to energy" is a term where "access" and "energy" separately are not. The
list is closed and is exactly this:

> a, an, the, of, to, for, in, on, at, by, with, from, into, through, their, its,
> our, that, which, is, are, be, being, been, as, s, and the quantifier and
> scoping words these labels use structurally: all, any, such, other, more, most,
> least, substantially, significantly, progressively, particularly, especially,
> inter, alia, appropriate, relevant, national, global, international, per, cent,
> proportion, share, number, level, levels.

**6. Keep a span as a key term if, after 4 and 5, it is 1 to 6 words long and
contains at least one word that is not on the generic stop-list** in
`stop-list.csv`. A span that reduces to nothing but stop-list words is dropped
here, which is the point of doing this before matching rather than after.

**7. Emit the head noun phrase as well**, for any span longer than three words,
so that "sustainable management of water" and "management of water" both count as
the same target's evidence. The head is the last two or three words of the span,
excluding trailing function words. **Step 7 applies whether or not step 6 kept
the full span.** A span of more than six words is too long to match usefully and
step 6 drops it, but its head is exactly what was wanted — target 7.2 is one
sentence with no commas and reduces to a seven-word span, so a step 7 that only
ran on kept spans would leave the whole of "renewable energy in the global energy
mix" with no term at all.

A head must be **at least two words** after trailing function words are removed.
A one-word head is not a phrase, and the words these spans end in — "average",
"countries", "population" — are qualifiers rather than subjects.

**Two targets therefore emit no key term at all, and this is recorded rather than
patched around.** Target 3.a is the Framework Convention on Tobacco Control "in
all countries, as appropriate", and target 10.1 is income growth of the bottom 40
per cent "at a rate higher than the national average". Both are long clauses
whose last three words are qualifiers, so a last-three-words head rule finds
nothing in them. **Making the rule cleverer until those two produced something
would be tuning the rule against its own output**, which is the habit this whole
section exists to prevent. They are reachable through the curated synonym list
instead, which is what section 3.2 provides it for, and both carry synonyms.

**8. De-duplicate** within a target, then across targets record the term's
`target_count`: how many of the 169 targets emit it. **A term emitted by more
than four targets is marked `discriminating = no`** and, per section 3.3, counts
only in the contexts the stop-list states. It is kept in the file rather than
deleted so a reader can see what was excluded and why.

## What the rule deliberately does not do

- **No stemming and no lemmatisation.** Both would collapse "sustainable" and
  "sustained", which mean different things across these targets, and both are
  hard for a reader to run by hand. Inflectional variants that matter are in the
  curated synonym list instead, where they are visible.
- **No embeddings, no model.** Section 3 requires the mapping decision to be
  made by rules a reader can run by hand. A term that appears in this file got
  there by the eight steps above and nothing else.
- **No frequency weighting from the project corpus.** The corpus is not consulted
  by this rule at all. Terms are derived from the taxonomy alone, so the
  vocabulary cannot be tuned, even accidentally, to the text it will be matched
  against. This is what keeps section 4's development and evaluation split
  meaningful.

## Output

`target-key-terms.csv`, one row per (target, term):

| column | meaning |
|---|---|
| `target_uri` | the SDG target's URI in the taxonomy snapshot |
| `target_id` | its notation, e.g. `6.3` |
| `goal_id` | the goal it belongs to |
| `term` | the extracted key term, lowercased |
| `source_span` | the span of the label it came from, before steps 4 and 5 |
| `emitted_by_step` | 6 or 7, so a reader can tell a span from its head |
| `target_count` | how many targets emit this term |
| `discriminating` | `no` where `target_count` > 4, else `yes` |

Regenerate with `python scripts/extract_key_terms.py`. It reads only the hashed
taxonomy snapshot and this repository's own committed files.
