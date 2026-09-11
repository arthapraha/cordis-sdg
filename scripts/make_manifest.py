#!/usr/bin/env python3
"""Build data/manifest.json from files actually on disk.

Every sha256 in the manifest is computed here from the bytes, so no hash in the
repository is hand-transcribed. Retrieval timestamps are recorded constants: they
are the UTC clock readings taken at the moment each fetch ran, and cannot be
recovered from the filesystem afterwards.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c,
section 2. Ratified by the owner in cordis-sdg at seq 86.
"""

import csv
import hashlib
import json
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import read_projects

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRATION = "72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c"

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
    "cordis_reports_json_archive": "2026-09-11T20:59:32Z",
}

# Upstream Last-Modified as served, verbatim. The three CORDIS extracts do not
# share one, which is the whole reason this is a named constant and not a
# comment: a reader must be able to see that the snapshot spans two upstream
# dates without going back to the headers.
UPSTREAM_LAST_MODIFIED = {
    "projects": "Thu, 06 Aug 2026 14:02:10 GMT",
    "project_deliverables": "Wed, 29 Jul 2026 16:59:50 GMT",
    "reports": "Wed, 29 Jul 2026 16:22:44 GMT",
    "reports_json": "Wed, 29 Jul 2026 16:22:46 GMT",
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


def zip_member_entry(archive_relpath, member):
    """Hash one member from inside the archive, without extracting it."""
    with zipfile.ZipFile(ROOT / archive_relpath) as zf:
        data = zf.read(member)
    return dict(path=member, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def reports_json_measure(archive_relpath, project_ids):
    """Measure the reports JSON distribution, and digest its members.

    WHY A DIGEST RATHER THAN A HASH PER MEMBER. Every other distribution here
    lists one sha256 per member, because each has fewer than ten. This archive
    has 9,735 entries, and 9,735 lines of hash would bury the manifest for no
    gain. Instead every record is hashed, and those hashes are reduced to ONE
    value over "<name> <sha256> <bytes>\\n" lines sorted by name. A re-download
    recomputes it in the same loop and compares one value, which is the same
    guarantee in a readable file. The algorithm is written out below so the
    check is reproducible from the manifest alone, and information.zip is still
    listed individually because it is the one member that is not a record.

    The narrative fields are counted over EVERY record, not a sample, and the
    project link is read from each record's own relations rather than inferred
    from the CSV serialisation's projectID column.
    """
    fields = ["teaser", "summary", "workPerformed", "finalResults"]
    non_empty = {f: 0 for f in fields}
    lines = []
    records = 0
    unparsable = 0
    any_narrative = 0
    no_link = 0
    multi_link = 0
    linked = set()

    with zipfile.ZipFile(ROOT / archive_relpath) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            if not info.filename.endswith(".json"):
                continue
            data = zf.read(info.filename)
            lines.append("%s %s %d\n" % (
                info.filename, hashlib.sha256(data).hexdigest(), len(data)))
            try:
                rec = json.loads(data)
            except Exception:
                unparsable += 1
                continue
            records += 1
            if any(isinstance(rec.get(f), str) and rec[f].strip() for f in fields):
                any_narrative += 1
            for f in fields:
                v = rec.get(f)
                if isinstance(v, str) and v.strip():
                    non_empty[f] += 1
            ids = set()
            for a in (rec.get("relations") or {}).get("associations") or []:
                cats = (a.get("relations") or {}).get("categories") or []
                if "/project" in {c.get("code") for c in cats} and a.get("id"):
                    ids.add(a["id"])
            if not ids:
                no_link += 1
            elif len(ids) > 1:
                multi_link += 1
            linked |= ids

    digest = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    covered = len(linked & project_ids)
    return {
        "record_files": records + unparsable,
        "records_parsed": records,
        "records_unparsable": unparsable,
        "records_with_any_narrative_field": any_narrative,
        "narrative_fields_non_empty": non_empty,
        "records_with_no_project_link": no_link,
        "records_with_more_than_one_project_link": multi_link,
        "distinct_projects_linked": len(linked),
        "projects_covered": covered,
        "linked_projects_absent_from_snapshot": len(linked - project_ids),
        "coverage_percent_of_snapshot": round(100.0 * covered / len(project_ids), 2),
        "records_digest": {
            "value": digest,
            "algorithm": (
                "sha256 over the concatenation of '<member name> <member sha256> "
                "<member bytes>\\n' for every member whose name ends in .json, "
                "sorted by member name, UTF-8 encoded. information.zip is excluded "
                "and listed separately."
            ),
        },
    }


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
    # project.csv is read through read_projects, NOT through read_csv. A standard
    # CSV reader breaks 193 of its rows and silently drops a character from 774
    # more, because the export under-escapes any field whose content begins with
    # a quotation mark. Counting distinct ids at header width gave 23,258, which
    # this manifest reported and which three coverage figures were divided by
    # before anyone asked the data what the number meant. The corpus is 23,451.
    header, project_rows = read_projects.load()
    project_ids = {r[0] for r in project_rows}
    at_header_width, _ = read_csv(
        "data/raw/cordis-horizon-projects/project.csv", id_column="id")
    projects = {
        "columns": header,
        "rows": len(project_rows),
        "distinct_id": len(project_ids),
        "rows_a_standard_csv_reader_breaks":
            len(read_projects.csv_module_disagreements()),
        "rows_at_header_width_under_a_standard_reader":
            at_header_width["rows_at_header_width"],
        "note": ("Read through scripts/read_projects.py. The two counts differ "
                 "because CORDIS under-escapes a field whose content starts with "
                 "a quote; the reader parses on the literal separator the file "
                 "actually uses and needs no repair heuristic."),
    }
    deliverables, deliverable_ids = read_csv(
        "data/raw/cordis-horizon-deliverables/projectDeliverables.csv", id_column="projectID")
    reports, report_ids = read_csv(
        "data/raw/cordis-horizon-reports/reportSummaries.csv", id_column="projectID")

    deliverables["projects_covered"] = len(deliverable_ids & project_ids)
    reports["projects_covered"] = len(report_ids & project_ids)
    reports_json = reports_json_measure(
        "data/raw/cordis-HORIZONreports-json.zip", project_ids)

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
                "reports_json": RETRIEVED["cordis_reports_json_archive"],
                "sdg_taxonomy": RETRIEVED["sdg_taxonomy"],
            },
            "note": (
                "This snapshot is not one upstream moment and does not claim to be. "
                "The projects extract was last modified upstream on 6 August 2026; "
                "the deliverables and both reports extracts on 29 July 2026, eight "
                "days earlier. They were also retrieved at three local moments, not "
                "one: the projects extract and the taxonomy on 2026-09-10, the "
                "deliverables and reports CSV on 2026-09-11 at 20:31:11Z once "
                "registration v7 admitted the fields they carry, and the reports "
                "JSON on 2026-09-11 at 20:59:32Z once v9 defined the editorial "
                "description as its four narrative fields. Stated as a fact here "
                "rather than left to be inferred from four hashes sitting side by "
                "side. The reports JSON was fetched twice, 28 minutes apart, and "
                "both fetches returned identical bytes."
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
                    "One dataset, four distributions. Registration v9 section 2 names "
                    "one snapshot of this dataset in four distributions: the projects "
                    "CSV, the deliverables CSV, the reports CSV and the reports JSON. "
                    "The projects extract alone carries neither of the two prose fields "
                    "section 2 admits, and no CSV distribution carries the editorial "
                    "description at all, which is why the JSON is in the snapshot."
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
                            "this CSV distribution; it is in the reports_json distribution "
                            "below, which is the same 9,734 reports serialised differently."
                        ),
                    },
                    "reports_json": {
                        "download_url": "https://cordis.europa.eu/data/cordis-HORIZONreports-json.zip",
                        "retrieved_utc": RETRIEVED["cordis_reports_json_archive"],
                        "http_status": 200,
                        "upstream_last_modified": UPSTREAM_LAST_MODIFIED["reports_json"],
                        "archive": entry("data/raw/cordis-HORIZONreports-json.zip"),
                        "members": {
                            "note": (
                                "9,735 entries: 9,734 one-record JSON files plus "
                                "information.zip. The records are covered by one digest "
                                "rather than 9,734 lines of hash; see records_digest.algorithm "
                                "under measured, which any re-download can recompute."
                            ),
                            "information_zip": zip_member_entry(
                                "data/raw/cordis-HORIZONreports-json.zip", "information.zip"),
                        },
                        "measured": {"reports_json": reports_json},
                        "carries": (
                            "The project editorial description, which no CSV distribution of "
                            "this dataset carries. Registration v9 section 2 defines it as this "
                            "distribution's teaser, summary, workPerformed and finalResults, "
                            "read in that order. Its own 'description' field is a type marker "
                            "reading 'periodic' and is NOT the editorial description. Each "
                            "record links to exactly one project through "
                            "relations.associations[] where the association's categories "
                            "include the code '/project'."
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
          projects["distinct_id"], "distinct ids;",
          projects["rows_a_standard_csv_reader_breaks"],
          "rows a standard csv reader breaks")
    print("projectDeliverables.csv:", deliverables["rows"], "rows,",
          deliverables["projects_covered"], "projects covered")
    print("reportSummaries.csv:", reports["rows"], "rows,",
          reports["projects_covered"], "projects covered")
    print("reports JSON:", reports_json["records_parsed"], "records,",
          reports_json["projects_covered"], "projects covered",
          "(%.2f%%)" % reports_json["coverage_percent_of_snapshot"],
          "digest", reports_json["records_digest"]["value"][:12] + "…")
    print("sdg:", manifest["datasets"]["eu_vocabularies_sdg_taxonomy"]["measured"])


if __name__ == "__main__":
    main()
