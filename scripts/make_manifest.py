#!/usr/bin/env python3
"""Build data/manifest.json from files actually on disk.

Every sha256 in the manifest is computed here from the bytes, so no hash in the
repository is hand-transcribed. Retrieval timestamps are recorded constants: they
are the UTC clock readings taken at the moment each fetch ran, and cannot be
recovered from the filesystem afterwards.

Registration v2 951e3e281b51bade85b778cd2c30955cad6837a1001fda6d6c9196fbb64afcee, section 2.
"""

import csv
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRATION = "951e3e281b51bade85b778cd2c30955cad6837a1001fda6d6c9196fbb64afcee"

# UTC clock readings taken at fetch time. See README for how each was obtained.
RETRIEVED = {
    "competition_page": "2026-09-10T22:34:00Z",
    "cordis_legal_notice": "2026-09-10T22:36:51Z",
    "cordis_dcat": "2026-09-10T22:40:26Z",
    "op_copyright_notice": "2026-09-10T22:39:04Z",
    "cordis_projects_archive": "2026-09-10T22:37:17Z",
    "sdg_taxonomy": "2026-09-10T22:37:51Z",
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


def project_rows():
    """Count data rows and capture the column list, measured not assumed."""
    csv.field_size_limit(1 << 30)
    p = ROOT / "data/raw/cordis-horizon-projects/project.csv"
    with open(p, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader)
        return header, sum(1 for _ in reader)


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
    header, rows = project_rows()

    archive = ROOT / "data/raw/cordis-HORIZONprojects-csv.zip"
    with zipfile.ZipFile(archive) as zf:
        members = sorted(zf.namelist())

    manifest = {
        "manifest_version": 1,
        "built_under_registration_sha256": REGISTRATION,
        "note": (
            "Snapshot record for the CORDIS-to-SDG entry. Payload files are not "
            "committed; these hashes let anyone verify a re-download byte for byte."
        ),
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
                "download_url": "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip",
                "retrieved_utc": RETRIEVED["cordis_projects_archive"],
                "http_status": 200,
                "upstream_last_modified": "Thu, 06 Aug 2026 14:02:10 GMT",
                "portal_distribution_updated": "2026-08-07",
                "archive": entry("data/raw/cordis-HORIZONprojects-csv.zip"),
                "members": [
                    entry("data/raw/cordis-horizon-projects/" + m) for m in members
                ],
                "measured": {
                    "project_rows": rows,
                    "project_columns": header,
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
    print("project rows:", rows)
    print("sdg:", manifest["datasets"]["eu_vocabularies_sdg_taxonomy"]["measured"])


if __name__ == "__main__":
    main()
