# CORDIS → SDG

Entry for the **Mapping CORDIS projects to SDGs** competition, organised by CORDIS
via the European Data Portal.

Everything in this repository is built under a registration that was fixed and
ratified by hash **before any pipeline code was written**, so that results cannot
move the method.

| | |
|---|---|
| registration | `cordis-sdg-registration-v9.md`, sha256 `72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c` (32,402 bytes) |
| ratified | 2026-09-11, by the owner, by hash |
| supersedes | v1 to v8, none of which governs this repository. v1 was never ratified and neither was v8; what each version changed is logged in v9 section 11, and every hash is in the cordis-sdg record. No superseded hash is written here, so a grep for one returns nothing rather than something a reader has to interpret. |
| this commit covers | registration section 8, ratification-day line: repository, rules re-read, all four CORDIS distributions and the taxonomy hashed, licence lines captured |

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

Two datasets. The CORDIS dataset is **one dataset with four distributions**, all
four hashed and recorded in `data/manifest.json`, because the projects extract
alone does not carry the fields the registration matches on and no CSV
distribution carries the editorial description at all.

**CORDIS — EU research projects under HORIZON EUROPE (2021-2027)**

| distribution | downloaded | upstream `Last-Modified` | archive sha256 | bytes |
|---|---|---|---|---|
| `cordis-HORIZONprojects-csv.zip` | 2026-09-10T22:37:17Z | Thu, 06 Aug 2026 14:02:10 GMT | `f91d5b6d7f952a4eeb725f4917576ffba652b6b03739d2ba763fa67b5dee6d22` | 36,672,015 |
| `cordis-HORIZONprojectDeliverables-csv.zip` | 2026-09-11T20:31:11Z | Wed, 29 Jul 2026 16:59:50 GMT | `3e17dec2a5d88e491b34a33e3aadd76bf5452b1cb778a5d47b7d98742d2281c6` | 4,665,117 |
| `cordis-HORIZONreports-csv.zip` | 2026-09-11T20:31:11Z | Wed, 29 Jul 2026 16:22:44 GMT | `52a133c5c545760eb66440e1f13c48d194471f4b37b1eba485002553d3b9c219` | 1,034,430 |
| `cordis-HORIZONreports-json.zip` | 2026-09-11T20:59:32Z | Wed, 29 Jul 2026 16:22:46 GMT | `a13edd67ac8c2fc1b5db3f2c218f81b9ccab1c336de24c3a09e3889f2c70e110` | 44,040,912 |

**This snapshot is not one upstream moment, and it does not claim to be.** The
projects extract was last modified upstream on **6 August 2026**; the other three
on **29 July 2026**, eight days earlier. They were also retrieved at **three**
local moments rather than one: the projects extract and the taxonomy on
2026-09-10, the two CSV sub-sets on 2026-09-11 once registration v7 widened the
fields in scope, and the reports JSON later the same evening once v9 defined the
editorial description as its four narrative fields. Anything computed across the
four carries that gap. It is written here as a fact rather than left to be
inferred from four hashes sitting side by side, and it is stated the same way in
the manifest under `snapshot`.

**The reports JSON was fetched twice, 28 minutes apart, and both fetches returned
identical bytes.** That is not proof the upstream file is stable, but it is the
only stability evidence available without waiting, and it is cheap to record.

Each archive ships its own `information.zip`, and all four are **231,028 bytes**.
**Three of the four hashes are distinct**: the projects and deliverables archives
each carry their own, and the two reports archives share one, which is what you
would expect of two serialisations of the same sub-set. Identical byte lengths
with different contents are the plainest possible argument for hashing members
rather than trusting a name and a size.

### On hashing the JSON distribution's members

Every other distribution here lists one sha256 per member, because each has fewer
than ten. **The reports JSON archive has 9,735 entries**, and 9,735 lines of hash
would bury the manifest for nothing. Every record is still hashed; those hashes
are reduced to **one digest** over `<name> <sha256> <bytes>` lines sorted by name,
recorded as `records_digest` with its algorithm written out beside it so the check
is reproducible from the manifest alone. `information.zip` is listed individually
because it is the one member that is not a record. **This is a deliberate
departure from the one-hash-per-member rule the other three follow, and it buys
the same guarantee in a file a person can read.**

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
are, one per file for every member of the three small CORDIS archives and one
digest over the 9,734 records of the fourth. To reproduce, re-download and
compare against `data/manifest.json`.

### What the four distributions measure to

| | rows or records | projects covered |
|---|---|---|
| `project.csv` | 23,451 | 23,258 distinct ids |
| `projectDeliverables.csv` | 58,780 | 11,180 of 23,258 (48.1%) |
| `reportSummaries.csv` | 9,734 | 9,654 of 23,258 (41.5%) |
| reports JSON records | 9,734 | 9,654 of 23,258 (41.51%) |

**A note on the project row count, which is not the number of projects.**
`project.csv` yields 23,451 rows, of which **23,258 parse to the header's 22
fields** and 23,258 are distinct ids with no duplicates. The remaining **193 rows
parse to between 23 and 30 fields**, because they carry an unescaped semicolon
inside a value. A naive read of this file misaligns exactly those rows. The
manifest records both counts under `rows` and `rows_at_header_width` so the gap
is visible rather than discovered later by whoever writes the loader.

## Which distribution carries the editorial description

Registration v9 section 2 admits the **editorial description** and the
**deliverable descriptions**, and section 3.4 makes the matcher read both. The
owner asked for the answer as a measurement rather than an assumption. It was not
the answer anyone expected, and v8 and v9 were drafted to meet it: v7 had named
one field that does not exist and one that was not in the snapshot. Here it is
with the numbers behind it.

**`projectDeliverables.csv` carries deliverable prose, and it is real.** Eight
columns — `deliverableType`, `description`, `url`, `projectID`,
`projectAcronym`, `contentUpdateDate`, `rcn`, `collection` — with `description`
running to 3,989 characters at its widest across 58,780 rows. That is the
deliverable's own text. **There is no `title` column.** v7's section 3.4 asked
the matcher to read "the deliverable titles", which named a field that does not
exist; **v9 item 27 renamed it to the deliverable descriptions**, which is what
this distribution actually provides.

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

**Where it lives, now measured over every record rather than a sample.** The same
reports sub-set published as JSON rather than CSV is 44,040,912 bytes against the
CSV's 1,034,430, one file per report. Registration v9 section 2 defines the
editorial description as this distribution's `teaser`, `summary`, `workPerformed`
and `finalResults`, read in that order. Its own `description` field is a type
marker reading `periodic` and is **not** the editorial description.

| | of 9,734 records |
|---|---|
| `teaser` non-empty | 9,734 |
| `summary` non-empty | 9,734 |
| `workPerformed` non-empty | 9,729 |
| `finalResults` non-empty | 9,721 |
| at least one of the four non-empty | 9,734 |
| records that failed to parse | 0 |

**The CSV serialisation drops every one of those fields**, which is why the JSON
is in the snapshot and the CSV is kept beside it.

**Project coverage, measured on the JSON itself and not inherited.** Each record
links to exactly **one** project, through `relations.associations[]` where the
association's categories include the code `/project`. No record has zero links and
none has more than one. That yields **9,734 distinct projects, of which 9,654 are
in the projects snapshot and 80 are not** — the same 80 the CSV shows, and a
consequence of the eight-day upstream gap between the two extracts. **Coverage of
the snapshot is 41.51%**, which is what the CSV-derived figure predicted, so
section 3.4's "about 41%" holds on the JSON's own evidence.

**Two corrections to what this file said before.** It reported "9,735 records
against the CSV's 9,734 rows". **There are 9,734 records**; the 9,735th archive
entry is `information.zip`, and counting archive entries as records was the error.
The two serialisations carry the same 9,734 reports. And the narrative fill rates
above are now counted over all 9,734 records rather than the first 1,500.

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

Registration v9 section 2 fixes the fields this entry reads: **id, acronym,
title, objective, description (editorial content), EuroSciVoc classification,
keywords, topic, programme part, start and end dates, participating
organisations, countries and deliverable descriptions.**

Two of those are defined by v9 rather than named, because the measurement above
showed the obvious reading did not exist in the data. **The editorial description
is the reports JSON's `teaser`, `summary`, `workPerformed` and `finalResults`,
read in that order.** And because the deliverables distribution has no title
column, **what is read is each deliverable's `description`**, not its title.

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
forbade precisely what section 2 requires. v9 carries that rule unchanged.

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

Registration v9 is ratified and this repository is anchored to its hash. The
competition page was re-read against the registration's own reading of it before
any of this was written, and the differences found were reported to the project
room first, as the registration requires. This repository follows the
registration exactly as ratified; changing it takes an amendment and a new hash.

**The gap this file reported at the previous commit is closed.** Section 3.4's
editorial description had no source in the snapshot; it now has one, defined by
v9 and hashed here, and its coverage is measured rather than inferred. Everything
section 8 puts on ratification day is done.

Nothing beyond it is built. There is still no crosswalk, no key-term extraction
rule, no synonym list, no stop-list, no negation rule, no sample draw, no
labelling and no model call.
