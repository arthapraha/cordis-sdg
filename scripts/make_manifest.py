#!/usr/bin/env python3
"""Build data/manifest.json from files actually on disk.

Every sha256 in the manifest is computed here from the bytes, so no hash in the
repository is hand-transcribed. Retrieval timestamps are recorded constants: they
are the UTC clock readings taken at the moment each fetch ran, and cannot be
recovered from the filesystem afterwards.

Registration v7 7eed47e43897f8bd1df673088564ffcad1a80e76d52424577f4d77a61ff82824,
section 2. Ratified by the owner in cordis-sdg at seq 69.
"""

import csv
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRATION = "7eed47e43897f8bd1df673088564ffcad1a80e76d52424577f4d77a61ff82824"

# UTC clock readings taken at fetch time. See README for how each was obtained.
# The projects extract and the four licence captures were fetched on 2026-09-10;
# the deliverables and reports extracts on 2026-09-11, at one moment, once v7
# admitted the fields they carry. Two retrieval moments, stated rather than
# implied.
RETRIEVED = {
    "competition_page": "2026-09-10T22:34:00Z",
    "cordis_legal_notice": "2026-09-10T22:36:51Z",
    "cordis_dcat": "2026-09-10T22:40:26Z",
    "op_copyright_notice": "2026-09-10T22:39:04Z",
    "cordis_projects_archive": "2026-09-10T22:37:17Z",
    "sdg_taxonomy": "2026-09-10T22:37:51Z",
    "cordis_deliverables_archive": "2026-09-11T20:31:11Z",
    "cordis_reports_archive": "2026-09-11T20:31:11Z",
}

# Upstream Last-Modified as served, verbatim. The three CORDIS extracts do not
# share one, which is the whole reason this is a named constant and not a
# comment: a reader must be able to see that the snapshot spans two upstream
# dates without going back to the headers.
UPSTREAM_LAST_MODIFIED = {
    "projects": "Thu, 06 Aug 2026 14:02:10 GMT",
    "project_deliverables": "Wed, 29 Jul 2026 16:59:50 GMT",
    "reports": "Wed, 29 Jul 2026 16:22:44 GMT",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def entry(relpath, **extra):
    p = ROOT / relpath
    if not p.is_file():
        sys.exit("missing file, refusing to write a manifest that claims it: %s" % relpath)
    return dict(path=relpath, bytes=p.stat().st_size, sha256=sha256(p), **extra)


def read_csv(relpath, id_column=None):
    """Measure a CORDIS CSV: header, row count, and distinct ids if asked.

    `rows` counts what the reader yields. `rows_at_header_width` counts those
    that parse to exactly the header's field count; the gap is rows carrying an
    unescaped delimiter, and it is reported rather than silently dropped,
    because a naive read of this file misaligns exactly those rows.
    """
    csv.field_size_limit(1 << 30)
    p = ROOT / relpath
    if not p.is_file():
        sys.exit("missing file, refusing to measure what is not there: %s" % relpath)
    with open(p, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader)
        rows = 0
        clean = 0
        ids = set()
        idx = header.index(id_column) if id_column else None
        for row in reader:
            rows += 1
            if len(row) == len(header):
                clean += 1
                if idx is not None and row[idx]:
                    ids.add(row[idx])
    out = {"columns": header, "rows": rows, "rows_at_header_width": clean}
    if id_column:
        out["distinct_" + id_column] = len(ids)
    return out, ids


def members_of(archive_relpath, extract_dir):
    with zipfile.ZipFile(ROOT / archive_relpath) as zf:
        names = sorted(zf.namelist())
    return [entry(extract_dir + "/" + m) for m in names]


def sdg_concept_counts():
    """Count goals and targets in the SKOS file by identifier shape."""
    import re
    p = ROOT / "data/raw/sdg-skos-ap-eu.rdf"
    ids = set(re.findall(rb'rdf:about="http://data\.europa\.eu/sdg/([^"]*)"', p.read_bytes()))
    goals = {i for i in ids if re.fullmatch(rb"[0-9]+", i)}
    targets = {i for i in ids if re.fullmatch(rb"[0-9]+\.[0-9a-z]+", i)}
    return dict(
        distinct_sdg_uris=len(ids),
        goals=len(goals),
        targets=len(targets),
        other_concepts=len(ids) - len(goals) - len(targets),
    )


def main():
    projects, project_ids = read_csv(
        "data/raw/cordis-horizon-projects/project.csv", id_column="id")
    deliverables, deliverable_ids = read_csv(
        "data/raw/cordis-horizon-deliverables/projectDeliverables.csv", id_column="projectID")
    reports, report_ids = read_csv(
        "data/raw/cordis-horizon-reports/reportSummaries.csv", id_column="projectID")

    deliverables["projects_covered"] = len(deliverable_ids & project_ids)
    reports["projects_covered"] = len(report_ids & project_ids)

    manifest = {
        "manifest_version": 2,
        "built_under_registration_sha256": REGISTRATION,
        "note": (
            "Snapshot record for the CORDIS-to-SDG entry. Payload files are not "
            "committed; these hashes let anyone verify a re-download byte for byte."
        ),
        "snapshot": {
            "upstream_last_modified": UPSTREAM_LAST_MODIFIED,
            "retrieved_utc": {
                "projects": RETRIEVED["cordis_projects_archive"],
                "project_deliverables": RETRIEVED["cordis_deliverables_archive"],
                "reports": RETRIEVED["cordis_reports_archive"],
                "sdg_taxonomy": RETRIEVED["sdg_taxonomy"],
            },
            "note": (
                "This snapshot is not one upstream moment and does not claim to be. "
                "The projects extract was last modified upstream on 6 August 2026; "
                "the deliverables and reports extracts on 29 July 2026, both eight "
                "days earlier. They were also retrieved at two different local "
                "moments: the projects extract and the taxonomy on 2026-09-10, the "
                "other two on 2026-09-11, after registration v7 admitted the fields "
                "they carry. Stated as a fact here rather than left to be inferred "
                "from two hashes sitting side by side."
            ),
        },
        "sources": {
            "competition_page": {
                "url": "https://data.europa.eu/dashboard/en/competition/cordis-sdg",
                "retrieved_utc": RETRIEVED["competition_page"],
                "http_status": 200,
                "server_rendered": True,
                "capture": entry("sources/competition-page.html"),
            },
            "cordis_dataset_metadata": {
                "url": (
                    "https://data.europa.eu/api/hub/repo/datasets/"
                    "cordis-eu-research-projects-under-horizon-europe-2021-2027.ttl"
                    "?useNormalizedId=true&locale=en"
                ),
                "dataset_page": (
                    "https://data.europa.eu/data/datasets/"
                    "cordis-eu-research-projects-under-horizon-europe-2021-2027"
                ),
                "retrieved_utc": RETRIEVED["cordis_dcat"],
                "http_status": 200,
                "server_rendered": True,
                "licence_assertion": "http://data.europa.eu/eli/dec/2011/833/oj",
                "capture": entry("sources/cordis-dcat.ttl"),
            },
            "cordis_legal_notice": {
                "url": "https://cordis.europa.eu/about/legal",
                "retrieved_utc": RETRIEVED["cordis_legal_notice"],
                "http_status": 200,
                "server_rendered": True,
                "capture": entry("sources/cordis-legal-notice.html"),
            },
            "op_copyright_notice": {
                "url": (
                    "https://op.europa.eu/en/web/about-us/legal-notices/"
                    "publications-office-of-the-european-union-copyright"
                ),
                "retrieved_utc": RETRIEVED["op_copyright_notice"],
                "http_status": 200,
                "server_rendered": True,
                "capture": entry("sources/op-copyright-notice.html"),
            },
        },
        "datasets": {
            "cordis_horizon_europe_projects": {
                "title": "CORDIS - EU research projects under HORIZON EUROPE (2021-2027)",
                "publisher": "Publications Office of the European Union",
                "dataset_page": (
                    "https://data.europa.eu/data/datasets/"
                    "cordis-eu-research-projects-under-horizon-europe-2021-2027"
                ),
                "licence": {
                    "statement": "Commission Decision 2011/833/EU on the reuse of Commission documents",
                    "uri": "http://data.europa.eu/eli/dec/2011/833/oj",
                    "source": "cordis_dataset_metadata",
                    "note": (
                        "Machine-readable dct:license on the dataset and on each of its "
                        "distributions, in the captured DCAT metadata. The prose statement "
                        "naming the same instrument, and CC BY 4.0 for editorial content, "
                        "is in the captured CORDIS legal notice and quoted in the README."
                    ),
                },
                "note": (
                    "One dataset, three CSV distributions. Registration v7 section 2 "
                    "names one snapshot of this dataset; the projects extract alone "
                    "carries neither the editorial description nor the deliverables "
                    "that section 2 admits and section 3.4 matches on, so the other "
                    "two distributions are part of the same snapshot."
                ),
                "distributions": {
                    "projects": {
                        "download_url": "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip",
                        "retrieved_utc": RETRIEVED["cordis_projects_archive"],
                        "http_status": 200,
                        "upstream_last_modified": UPSTREAM_LAST_MODIFIED["projects"],
                        "portal_distribution_updated": "2026-08-07",
                        "archive": entry("data/raw/cordis-HORIZONprojects-csv.zip"),
                        "members": members_of(
                            "data/raw/cordis-HORIZONprojects-csv.zip",
                            "data/raw/cordis-horizon-projects"),
                        "measured": {"project_csv": projects},
                    },
                    "project_deliverables": {
                        "download_url": (
                            "https://cordis.europa.eu/data/"
                            "cordis-HORIZONprojectDeliverables-csv.zip"
                        ),
                        "retrieved_utc": RETRIEVED["cordis_deliverables_archive"],
                        "http_status": 200,
                        "upstream_last_modified": UPSTREAM_LAST_MODIFIED["project_deliverables"],
                        "archive": entry("data/raw/cordis-HORIZONprojectDeliverables-csv.zip"),
                        "members": members_of(
                            "data/raw/cordis-HORIZONprojectDeliverables-csv.zip",
                            "data/raw/cordis-horizon-deliverables"),
                        "measured": {"project_deliverables_csv": deliverables},
                        "carries": (
                            "A per-deliverable 'description' column of real prose. This is "
                            "the deliverable's own text, not the project's editorial "
                            "description. There is no 'title' column, so registration v7 "
                            "section 3.4's phrase 'the deliverable titles' has no field to "
                            "match; 'description' is what this distribution provides."
                        ),
                    },
                    "reports": {
                        "download_url": "https://cordis.europa.eu/data/cordis-HORIZONreports-csv.zip",
                        "retrieved_utc": RETRIEVED["cordis_reports_archive"],
                        "http_status": 200,
                        "upstream_last_modified": UPSTREAM_LAST_MODIFIED["reports"],
                        "archive": entry("data/raw/cordis-HORIZONreports-csv.zip"),
                        "members": members_of(
                            "data/raw/cordis-HORIZONreports-csv.zip",
                            "data/raw/cordis-horizon-reports"),
                        "measured": {"report_summaries_csv": reports},
                        "carries": (
                            "No narrative text. The seven columns are attachment, id, title, "
                            "projectID, projectAcronym, contentUpdateDate and rcn; 'title' is "
                            "the boilerplate 'Periodic Reporting for period N - ACRONYM' and "
                            "'attachment' holds image paths. The editorial content the "
                            "competition page defines as the project description is NOT in "
                            "this CSV distribution. See the README for where it is and what "
                            "that costs."
                        ),
                    },
                },
            },
            "eu_vocabularies_sdg_taxonomy": {
                "title": "Sustainable Development Goals (SDG) — EU Vocabularies",
                "publisher": "Publications Office of the European Union",
                "concept_scheme": "http://data.europa.eu/sdg",
                "distribution_version": "20200930-0",
                "download_url": (
                    "https://op.europa.eu/o/opportal-service/euvoc-download-handler"
                    "?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2F"
                    "distribution%2Fsdg%2F20200930-0%2Frdf%2Fskos_ap_eu%2F"
                    "sdg-skos-ap-eu.rdf&fileName=sdg-skos-ap-eu.rdf"
                ),
                "dataset_page": (
                    "https://op.europa.eu/en/web/eu-vocabularies/dataset/-/resource"
                    "?uri=http://publications.europa.eu/resource/dataset/sdg"
                ),
                "retrieved_utc": RETRIEVED["sdg_taxonomy"],
                "http_status": 200,
                "licence": {
                    "statement": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                    "uri": "https://creativecommons.org/licenses/by/4.0/",
                    "source": "op_copyright_notice",
                    "note": (
                        "The SDG distribution carries no licence statement inside the RDF "
                        "and the taxonomy has no data.europa.eu DCAT record of its own, so "
                        "the governing statement is the Publications Office copyright "
                        "notice captured under sources and quoted verbatim in the README. "
                        "Recorded here so both datasets in this manifest carry a licence "
                        "field rather than one carrying it and one leaving it to prose."
                    ),
                },
                "file": entry("data/raw/sdg-skos-ap-eu.rdf"),
                "measured": sdg_concept_counts(),
            },
        },
    }

    # newline="" so the file is written with LF on every platform. Without it,
    # Windows writes CRLF, git stores LF, and every rebuild shows a whole-file
    # diff that means nothing.
    out = ROOT / "data/manifest.json"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("wrote", out.relative_to(ROOT))
    print("project.csv:", projects["rows"], "rows,",
          projects["rows_at_header_width"], "at header width,",
          projects["distinct_id"], "distinct ids")
    print("projectDeliverables.csv:", deliverables["rows"], "rows,",
          deliverables["projects_covered"], "projects covered")
    print("reportSummaries.csv:", reports["rows"], "rows,",
          reports["projects_covered"], "projects covered")
    print("sdg:", manifest["datasets"]["eu_vocabularies_sdg_taxonomy"]["measured"])


if __name__ == "__main__":
    main()
