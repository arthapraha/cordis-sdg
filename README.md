# CORDIS → SDG

Entry for the **Mapping CORDIS projects to SDGs** competition, organised by CORDIS
via the European Data Portal.

Everything in this repository is built under a registration that was fixed and
ratified by hash **before any pipeline code was written**, so that results cannot
move the method.

| | |
|---|---|
| registration | `cordis-sdg-registration-v7.md`, sha256 `7eed47e43897f8bd1df673088564ffcad1a80e76d52424577f4d77a61ff82824` (26,598 bytes) |
| ratified | 2026-09-11, by the owner, by hash |
| supersedes | v1 to v6, none of which governs this repository. v1 `c19d7d83…` was never ratified; what each later version changed is logged in v7 section 11, and every hash is in the cordis-sdg record. No superseded hash is written here, so a grep for one returns nothing rather than something a reader has to interpret. |
| this commit covers | registration section 8, ratification-day line: repository, rules re-read, all three CORDIS distributions and the taxonomy hashed, licence lines captured |

Nothing beyond that line is in this repository yet. There is no crosswalk, no
key-term extraction rule, no synonym list, no stop-list, no sample draw, no
labelling and no model call, because none of those are authorised until the
owner's next word.

## Licence

Settled by the owner on ratification day and recorded here because registration
section 9 requires it:

- **CC BY 4.0** for the documentation, the crosswalk and the synonym list.
- **MIT** for the code.

The certificate carries one name, **Attila Angyan**. The agents that built this
are credited in the description document rather than on the certificate.

## Snapshots

Two datasets. The CORDIS dataset is **one dataset with three CSV distributions**,
all three hashed and recorded in `data/manifest.json`, because the projects
extract alone does not carry the fields the registration matches on.

**CORDIS — EU research projects under HORIZON EUROPE (2021-2027)**

| distribution | downloaded | upstream `Last-Modified` | archive sha256 | bytes |
|---|---|---|---|---|
| `cordis-HORIZONprojects-csv.zip` | 2026-09-10T22:37:17Z | Thu, 06 Aug 2026 14:02:10 GMT | `f91d5b6d7f952a4eeb725f4917576ffba652b6b03739d2ba763fa67b5dee6d22` | 36,672,015 |
| `cordis-HORIZONprojectDeliverables-csv.zip` | 2026-09-11T20:31:11Z | Wed, 29 Jul 2026 16:59:50 GMT | `3e17dec2a5d88e491b34a33e3aadd76bf5452b1cb778a5d47b7d98742d2281c6` | 4,665,117 |
| `cordis-HORIZONreports-csv.zip` | 2026-09-11T20:31:11Z | Wed, 29 Jul 2026 16:22:44 GMT | `52a133c5c545760eb66440e1f13c48d194471f4b37b1eba485002553d3b9c219` | 1,034,430 |

**This snapshot is not one upstream moment, and it does not claim to be.** The
projects extract was last modified upstream on **6 August 2026**; the other two
on **29 July 2026**, eight days earlier. They were also retrieved at two
different local moments, a day apart, because the deliverables and reports
extracts were only admitted once registration v7 widened the fields in scope.
Anything computed across the three carries that gap. It is written here as a
fact rather than left to be inferred from three hashes sitting side by side, and
it is stated the same way in the manifest under `snapshot`.

Each archive ships its own `information.zip`. All three are **231,028 bytes and
none of them is the same file**: three different sha256 values at an identical
byte length, which is the plainest possible argument for hashing members rather
than trusting a name and a size.

**Sustainable Development Goals taxonomy — EU Vocabularies**

| | |
|---|---|
| downloaded | 2026-09-10T22:37:51Z |
| concept scheme | `http://data.europa.eu/sdg` |
| distribution | `sdg-skos-ap-eu.rdf`, version 20200930-0 |
| sha256 | `ca4f24d0774991f3e26a5923b93b9d674b73dd391ff80d75c03896af0edfa2c6` |
| size | 6,337,360 bytes |
| goals / targets | 17 / 169 |

The goal and target counts are counted from the downloaded file, not taken from
the competition page, and they agree with what the organisers state in Q5.

The payload files live under `data/raw/` and are **not committed**; their hashes
are, one per file including every member of all three CORDIS archives. To
reproduce, re-download and compare against `data/manifest.json`.

### What the three distributions measure to

| | rows | projects covered |
|---|---|---|
| `project.csv` | 23,451 | 23,258 distinct ids |
| `projectDeliverables.csv` | 58,780 | 11,180 of 23,258 (48.1%) |
| `reportSummaries.csv` | 9,734 | 9,654 of 23,258 (41.5%) |

**A note on the project row count, which is not the number of projects.**
`project.csv` yields 23,451 rows, of which **23,258 parse to the header's 22
fields** and 23,258 are distinct ids with no duplicates. The remaining **193 rows
parse to between 23 and 30 fields**, because they carry an unescaped semicolon
inside a value. A naive read of this file misaligns exactly those rows. The
manifest records both counts under `rows` and `rows_at_header_width` so the gap
is visible rather than discovered later by whoever writes the loader.

## Which distribution carries the editorial description

Registration v7 section 2 admits the **editorial description** and the
**deliverables**, and section 3.4 makes the matcher read both. The owner asked
for the answer as a measurement rather than an assumption. It is not the answer
anyone expected, so here it is with the numbers behind it.

**`projectDeliverables.csv` carries deliverable prose, and it is real.** Eight
columns — `deliverableType`, `description`, `url`, `projectID`,
`projectAcronym`, `contentUpdateDate`, `rcn`, `collection` — with `description`
running to 3,989 characters at its widest across 58,780 rows. That is the
deliverable's own text. **There is no `title` column**, so section 3.4's phrase
"the deliverable titles" has no field to match; `description` is what this
distribution actually provides.

**`reportSummaries.csv` carries no narrative at all.** Its seven columns are
`attachment`, `id`, `title`, `projectID`, `projectAcronym`, `contentUpdateDate`
and `rcn`. The `title` is boilerplate of the form "Periodic Reporting for period
2 - ACRONYM (full name)", and `attachment` holds image file paths and is often
empty. **No column in it is the editorial content the competition page defines
as the project description.**

**So neither authorised CSV distribution carries the project editorial
description.** The competition page's own glossary defines it, from the capture
in `sources/competition-page.html`:

> Project description. Editorial content prepared for CORDIS, providing a more accessible description of the project and its context.

**Where it actually lives, measured and not fetched into this snapshot.** The
same reports distribution published as JSON rather than CSV is 44,040,912 bytes
against the CSV's 1,034,430, and it is one file per report: 9,735 records against
the CSV's 9,734 rows. Each record carries `teaser`, `summary`, `workPerformed`
and `finalResults`, which are the editorial prose, and a `description` field that
is a type marker reading `periodic` rather than text. Of the first 1,500 records
read, `teaser` and `summary` are non-empty in 1,500, `workPerformed` in 1,498 and
`finalResults` in 1,494. **The CSV serialisation drops every one of those
fields.**

That download was made to answer the question and **was deliberately not brought
into this snapshot or this manifest**, because the owner's word authorised the
projectDeliverables and reports distributions and this repository does not
quietly widen its own scope. **What the registration does with the gap is not
this commit's to decide**, and section 3.4 cannot be satisfied for the editorial
description by anything currently hashed here.

## Licences of the source data

Copied verbatim from the pages named, each with the moment it was retrieved and
the sha256 of the bytes retrieved. The captured pages are committed under
`sources/`, so every quotation below can be checked against the bytes it came
from rather than taken on trust. Both datasets now also carry a `licence` field
in `data/manifest.json`, so neither is left to prose alone.

### CORDIS data

From **https://cordis.europa.eu/about/legal**, retrieved **2026-09-10T22:36:51Z**,
HTTP 200, 80,307 bytes,
sha256 `bfe1abf270c3206b3eb444ea2dd6f9b1bdf8fa14c5ee6790e2d84a0be3ee023f`
(`sources/cordis-legal-notice.html`):

> The Commission's reuse policy is implemented by Commission Decision 2011/833/EU of 12 December 2011 on the reuse of Commission documents.

> Unless otherwise noted (e.g. in individual copyright notices), the reuse of the editorial content on this website owned by the EU is authorized under the Creative Commons Attribution 4.0 International (CC BY 4.0) licence. This means that reuse is allowed, provided appropriate credit is given and any changes are indicated.

> You may be required to clear additional rights if a specific content depicts identifiable private individuals or includes third-party works (drawings, photos, audio, video, etc.). To use or reproduce content that is not owned by the EU, you may need to seek permission directly from the respective rightholders. Software or documents covered by industrial property rights, such as patents, trademarks, registered designs, logos and names, are excluded from the Commission's reuse policy and are not licensed to you.

The machine-readable assertion for the same dataset, from its DCAT metadata at
data.europa.eu, retrieved **2026-09-10T22:40:26Z**, HTTP 200, 71,031 bytes,
sha256 `1021951475dc132e90eb6721e5611aa97490c705d9a2ad2116c39fbd3810e099`
(`sources/cordis-dcat.ttl`):

```
        dct:license          <http://data.europa.eu/eli/dec/2011/833/oj>;
```

That URI is Commission Decision 2011/833/EU, the same instrument the prose names.
It appears on the dataset and on each of its distributions, which is why one
licence covers all three archives above. That same capture is where the
deliverables and reports distributions were found.

### EU Vocabularies SDG taxonomy

The SDG distribution carries no licence statement inside the RDF, and the
taxonomy is not published as a data.europa.eu dataset with its own DCAT record,
so the governing statement is the Publications Office notice.

From **https://op.europa.eu/en/web/about-us/legal-notices/publications-office-of-the-european-union-copyright**,
retrieved **2026-09-10T22:39:04Z**, HTTP 200, 378,554 bytes,
sha256 `346494ccba6b09a04b27b3b9ee05799966390a18a52178c5a5c6eea5412e943e`
(`sources/op-copyright-notice.html`):

> The editorial content of this website, which is owned by the EU, is licensed under the Creative Commons Attribution 4.0 International licence. This means that you can reuse it provided you acknowledge the source and indicate any changes you have made.

> Most of the publications on this website are freely available, many of them under Creative Commons licences, and can be downloaded and reproduced provided the source is acknowledged. If you would like to reuse them, please check their respective copyright notices.

A browser reading of this page renders the first sentence as `...International
licence(external link). This means...`. That marker is a `<span class="sr-only">`
inside the anchor, a screen-reader label for the outbound link, and it is not
part of the licence sentence. It is left out above so that the quotation is the
licence text and nothing else. This is the kind of difference that only shows up
if the quotation is checked against the served bytes rather than against what a
browser displays, which is what `scripts/verify_licences.py` does.

### Competition page

From **https://data.europa.eu/dashboard/en/competition/cordis-sdg**, retrieved
**2026-09-10T22:34:00Z**, HTTP 200, 89,505 bytes,
sha256 `b58aadc954dd6917b34a65851356b4981e9602ff7481b8c08e1e65e29b1fdfb9`
(`sources/competition-page.html`). Overview, Rules and Q&A are one document at
that URL.

### One honest note on page hashes

A sha256 is only worth recording if the bytes carry the text being quoted. Two
portal pages return a JavaScript shell to a plain HTTP client and render their
content in the browser: the CORDIS dataset page at data.europa.eu returns 1,599
bytes, and the EU Vocabularies SDG dataset page does not contain its own
distribution link in the fetched bytes. Hashing either would have recorded a
number that proves nothing. The captures above were each checked for the quoted
string before their hash was recorded, and the two client-rendered pages were
replaced by sources that are server-rendered: the DCAT metadata for the CORDIS
licence, and the Publications Office notice for the taxonomy.

## Data handling

Registration v7 section 2 fixes the fields this entry reads: **id, acronym,
title, objective, description (editorial content), EuroSciVoc classification,
keywords, topic, programme part, start and end dates, participating
organisations, countries and deliverables.**

**Section 5 is the rule that governs the rest: person-level fields are not read.**
An organisation is not a person. The competition page's rule, quoted from the
capture in `sources/competition-page.html` and re-checked by
`scripts/verify_licences.py`, is:

> Participants must not process personal data.

Participating organisations and their countries are read, because the page names
them among the relevant fields and section 6's analysis needs them.
`organization.csv` is therefore an **input** to this entry, not an incidental
member of the archive. Read its header and the point is checkable rather than
promised: `projectID`, `projectAcronym`, `organisationID`, `vatNumber`, `name`,
`shortName`, `SME`, `activityType`, `street`, `postCode`, `city`, `country`,
`nutsCode`, `geolocation`, `organizationURL`, `contactForm`,
`contentUpdateDate`, `rcn`, `order`, `role`, `ecContribution`,
`netEcContribution`, `totalCost`, `endOfParticipation`, `active`. **Every one of
those is an organisation-level field. There is no person name, no individual
contact, no natural-person identifier anywhere in it**, so section 5 is honoured
by reading the file as it stands rather than by carving columns out of it.

An earlier commit of this file, written under registration v2, said "no
participant or person fields are read" and described `organization.csv` as hashed
but unread. That was v2's rule and v7 replaced it, for the reason v7 item 23
gives: in CORDIS a participant **is** an organisation, so the old sentence
forbade precisely what section 2 requires.

## Reproducing this commit

```
python scripts/make_manifest.py
python scripts/verify_licences.py
```

`make_manifest.py` rebuilds `data/manifest.json` from the files on disk. Every
sha256 in the manifest is computed from bytes at that moment; none is
transcribed by hand. Retrieval timestamps are the recorded UTC clock readings
from the moment each fetch ran, which is the one thing the filesystem cannot
recover afterwards.

`verify_licences.py` re-checks every licence quotation above, and three
quotations from the competition page, against the captured bytes in `sources/`,
and exits non-zero if any of them has drifted. It reports 11 checks and all of
them pass at this commit.

## Status

Registration v7 is ratified and this repository is anchored to its hash. The
competition page was re-read against the registration's own reading of it before
any of this was written, and the differences found were reported to the project
room first, as the registration requires. This repository follows the
registration exactly as ratified; changing it takes an amendment and a new hash.

One thing the registration asks for is **not** satisfied by anything hashed here,
and it is named rather than worked around: section 3.4's editorial description
has no source in this snapshot. See the measurement above.
