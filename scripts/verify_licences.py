#!/usr/bin/env python3
"""Check every licence line quoted in README.md against the bytes it claims to
come from.

Registration v2 section 2 requires each licence line to be copied verbatim with
its retrieval timestamp and the sha256 of the page it came from. A quotation
nobody can check is worth less than no quotation, so this script re-derives the
check from the captured pages in sources/ and fails loudly on any mismatch.

Normalisation is deliberately narrow. HTML puts the punctuation that follows a
link outside the anchor element, so stripping tags leaves "documents ." where
the reader sees "documents.". Whitespace is collapsed and spaces before closing
punctuation are removed. Nothing else is touched: no case folding, no word
substitution, no fuzzy matching.

Usage:  python scripts/verify_licences.py
Exit:   0 if every quotation is found, 1 otherwise.
"""

import hashlib
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (capture file, expected sha256, quotation as it appears in README.md)
CHECKS = [
    (
        "sources/cordis-legal-notice.html",
        "bfe1abf270c3206b3eb444ea2dd6f9b1bdf8fa14c5ee6790e2d84a0be3ee023f",
        "The Commission's reuse policy is implemented by Commission Decision "
        "2011/833/EU of 12 December 2011 on the reuse of Commission documents.",
    ),
    (
        "sources/cordis-legal-notice.html",
        "bfe1abf270c3206b3eb444ea2dd6f9b1bdf8fa14c5ee6790e2d84a0be3ee023f",
        "Unless otherwise noted (e.g. in individual copyright notices), the reuse "
        "of the editorial content on this website owned by the EU is authorized "
        "under the Creative Commons Attribution 4.0 International (CC BY 4.0) "
        "licence. This means that reuse is allowed, provided appropriate credit "
        "is given and any changes are indicated.",
    ),
    (
        "sources/cordis-legal-notice.html",
        "bfe1abf270c3206b3eb444ea2dd6f9b1bdf8fa14c5ee6790e2d84a0be3ee023f",
        "You may be required to clear additional rights if a specific content "
        "depicts identifiable private individuals or includes third-party works "
        "(drawings, photos, audio, video, etc.). To use or reproduce content that "
        "is not owned by the EU, you may need to seek permission directly from the "
        "respective rightholders. Software or documents covered by industrial "
        "property rights, such as patents, trademarks, registered designs, logos "
        "and names, are excluded from the Commission's reuse policy and are not "
        "licensed to you.",
    ),
    (
        "sources/op-copyright-notice.html",
        "346494ccba6b09a04b27b3b9ee05799966390a18a52178c5a5c6eea5412e943e",
        "The editorial content of this website, which is owned by the EU, is "
        "licensed under the Creative Commons Attribution 4.0 International licence",
    ),
    (
        "sources/op-copyright-notice.html",
        "346494ccba6b09a04b27b3b9ee05799966390a18a52178c5a5c6eea5412e943e",
        "This means that you can reuse it provided you acknowledge the source and "
        "indicate any changes you have made.",
    ),
    (
        "sources/op-copyright-notice.html",
        "346494ccba6b09a04b27b3b9ee05799966390a18a52178c5a5c6eea5412e943e",
        "Most of the publications on this website are freely available, many of "
        "them under Creative Commons licences, and can be downloaded and "
        "reproduced provided the source is acknowledged. If you would like to "
        "reuse them, please check their respective copyright notices.",
    ),
    (
        "sources/cordis-dcat.ttl",
        "1021951475dc132e90eb6721e5611aa97490c705d9a2ad2116c39fbd3810e099",
        "dct:license          <http://data.europa.eu/eli/dec/2011/833/oj>;",
    ),
]

# Quotations that must also appear in the competition page capture, because the
# entry's scope decisions rest on them.
PAGE_CHECKS = [
    (
        "sources/competition-page.html",
        "b58aadc954dd6917b34a65851356b4981e9602ff7481b8c08e1e65e29b1fdfb9",
        "The mapping does not have to stop at target level.",
    ),
    (
        "sources/competition-page.html",
        "b58aadc954dd6917b34a65851356b4981e9602ff7481b8c08e1e65e29b1fdfb9",
        "Visualisations showing the main findings.",
    ),
    (
        "sources/competition-page.html",
        "b58aadc954dd6917b34a65851356b4981e9602ff7481b8c08e1e65e29b1fdfb9",
        "Participants must not process personal data.",
    ),
]

# Claims the README makes about markup rather than about prose. These are checked
# against the raw bytes, with no tag stripping.
MARKUP_CHECKS = [
    (
        "sources/op-copyright-notice.html",
        '<span class="sr-only">(external link)</span>',
        "the (external link) marker is a screen-reader label, not licence text",
    ),
]

TIDY_BEFORE_PUNCT = re.compile(r"\s+([.,;:)])")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise(text):
    text = text.replace("’", "'").replace(" ", " ")
    text = re.sub(r"\s+", " ", text)
    return TIDY_BEFORE_PUNCT.sub(r"\1", text).strip()


def page_text(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix != ".html":
        return normalise(raw)
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return normalise(html.unescape(raw))


def main():
    failures = 0
    texts = {}
    digests = {}

    for relpath, expected_sha, quote in CHECKS + PAGE_CHECKS:
        path = ROOT / relpath
        if not path.is_file():
            print("MISSING  %s" % relpath)
            failures += 1
            continue

        if relpath not in digests:
            digests[relpath] = sha256(path)
            if digests[relpath] != expected_sha:
                print("HASH     %s" % relpath)
                print("         expected %s" % expected_sha)
                print("         actual   %s" % digests[relpath])
                failures += 1
            texts[relpath] = page_text(path)

        if normalise(quote) in texts[relpath]:
            print("ok       %s | %s" % (pathlib.Path(relpath).name, quote[:58]))
        else:
            print("NOT FOUND %s | %s" % (pathlib.Path(relpath).name, quote[:58]))
            failures += 1

    for relpath, needle, claim in MARKUP_CHECKS:
        path = ROOT / relpath
        raw = path.read_text(encoding="utf-8", errors="replace")
        if needle in raw:
            print("ok       %s | markup: %s" % (pathlib.Path(relpath).name, claim))
        else:
            print("NOT FOUND %s | markup: %s" % (pathlib.Path(relpath).name, claim))
            failures += 1

    print()
    if failures:
        print("%d check(s) failed." % failures)
        return 1
    print("All %d checks verified against the captured bytes."
          % len(CHECKS + PAGE_CHECKS + MARKUP_CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
