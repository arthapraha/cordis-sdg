# CORDIS → SDG

Entry for the **Mapping CORDIS projects to SDGs** competition, organised by CORDIS
via the European Data Portal.

Everything in this repository is built under a registration that was fixed and
ratified by hash **before any pipeline code was written**, so that results cannot
move the method.

| | |
|---|---|
| registration | `cordis-sdg-registration-v2.md`, sha256 `951e3e281b51bade85b778cd2c30955cad6837a1001fda6d6c9196fbb64afcee` (13,986 bytes) |
| ratified | 2026-09-10, by the owner, by hash |
| supersedes | v1 `c19d7d8339f43ee1b069f3c24cd21481f8c5cfed1a1c848c4b05a7f7ef5b48f7`, never ratified |
| this commit covers | registration section 8, ratification-day line only: repository, rules re-read, both snapshots hashed, licence lines captured |

Nothing beyond that line is in this repository yet. There is no crosswalk, no
key-term extraction rule, no synonym list, no stop-list, no sample draw, no
labelling and no model call, because none of those are authorised until the
first review pass and the owner's next word.

## Snapshots

Two snapshots, taken once, hashed, and recorded in `data/manifest.json`.

**CORDIS — EU research projects under HORIZON EUROPE (2021-2027)**

| | |
|---|---|
| downloaded | 2026-09-10T22:37:17Z |
| from | `https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip` |
| archive sha256 | `f91d5b6d7f952a4eeb725f4917576ffba652b6b03739d2ba763fa67b5dee6d22` |
| archive size | 36,672,015 bytes |
| upstream Last-Modified | Thu, 06 Aug 2026 14:02:10 GMT |
| projects in `project.csv` | 23,451 |

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
are, one per file including every member of the CORDIS archive. To reproduce,
re-download and compare against `data/manifest.json`.

## Licences

Copied verbatim from the pages named, each with the moment it was retrieved and
the sha256 of the bytes retrieved. The captured pages are committed under
`sources/`, so every quotation below can be checked against the bytes it came
from rather than taken on trust.

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
It appears on the dataset and on each of its distributions.

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

Registration section 2 fixes the fields this entry reads: id, acronym, title,
objective, EuroSciVoc classification, keywords, topic and programme part. **No
participant or person fields are read.** `organization.csv` arrives inside the
CORDIS archive and is hashed for completeness of the snapshot record; it is not
read by anything in this repository.

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

The competition page was re-read against the registration's own reading of it
before any of this was written, and the differences found were reported to the
project room first, as the registration requires. Those differences are **not**
applied here. This repository follows the registration exactly as ratified;
changing it takes an amendment and a new hash.
