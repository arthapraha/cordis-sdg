#!/usr/bin/env python3
"""Build static data assets for the §6 item 7 web prototype.

Reads the four confirmed inputs, verifies their SHA-256 hashes against the
input contract, validates all header columns and render bindings, and outputs
compact, self-contained JSON assets into prototype/data/ for zero-backend
browser execution.

Never writes to scripts/, data/, notebooks/, or docs/.
"""

import csv
from collections import defaultdict
import hashlib
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Confirmed input hashes (registration v10 §7 & room seq 266/272)
EXPECTED_HASHES = {
    "mapping_table": (
        REPO_ROOT / "data" / "corpus" / "mapping-table-0246412.csv",
        "181d378a3078014193f3ae4f684b00b375ed62f3d24b2b34c060f6457b4a00d3",
    ),
    "figures_document": (
        REPO_ROOT / "data" / "corpus" / "figures.json",
        "03d79580081ca40bf0d1d25b5279a57880ddf09d750490553593387126d92f6f",
    ),
    "metrics_artefact": (
        REPO_ROOT / "data" / "pipeline" / "evaluation-100-metrics.json",
        "babd37415581ce82ecb09c4501052ce811e834e57dad7c6735389ce321dd8a2e",
    ),
    "fig_recall_ceiling": (
        REPO_ROOT / "figures" / "recall-ceiling.svg",
        "2877c3ac441ffbb0485b712abda4cff057c8efa93e904c7ca494fcd6f8427ed1",
    ),
    "fig_disagreement_shape": (
        REPO_ROOT / "figures" / "disagreement-shape.svg",
        "d9c6a91a11481c3265be6d4747b69352790fa7e4536ff98ff19ea831ea3f9e61",
    ),
    "fig_goals_by_project": (
        REPO_ROOT / "figures" / "goals-by-project-count.svg",
        "7db6eae48b966e1fa73c3e928f21958171cad4a8536f49f3fe1e816701f02d23",
    ),
    "fig_most_linked_targets": (
        REPO_ROOT / "figures" / "most-linked-targets.svg",
        "8f2caf29f882ebf6148ffd73485308fb02a7e682e0bfaace837de532c1d644d6",
    ),
    "fig_relevance_by_field": (
        REPO_ROOT / "figures" / "relevance-by-field.svg",
        "46baad33a8d40a4cba2b0ee220df564d01b4bc61308ff102374da95ace6f4d6f",
    ),
    "fig_confidence_bands": (
        REPO_ROOT / "figures" / "confidence-bands.svg",
        "7d55aa97458541589e569986b3be7a8abb14e7a5da12ccef06030469fe160761",
    ),
}

EXPECTED_COLUMNS = [
    "project_id",
    "acronym",
    "title",
    "sdg_target_uri",
    "sdg_target_label",
    "sdg_goal_uri",
    "sdg_goal_label",
    "assignment_level",
    "confidence_band",
    "score",
    "explanation",
    "matched_phrases_and_source_fields",
    "sources_present",
    "sources_absent",
    "overflow_beyond_cap",
    "snapshot_sha256",
    "pipeline_commit",
    "prompt_sha256",
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs():
    print("Verifying four inputs against confirmed SHA-256 contract...")
    for name, (path, expected) in EXPECTED_HASHES.items():
        if not path.is_file():
            sys.exit(f"REFUSED: input file missing: {path}")
        actual = sha256_file(path)
        if actual != expected:
            sys.exit(
                f"REFUSED: hash mismatch on {name} ({path}):\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual}"
            )
        print(f"  OK {name}: {actual} (matches)")


def write_target_labels(data_dir: pathlib.Path) -> pathlib.Path:
    """The 169 UN target labels, keyed by target id, from the frozen taxonomy file.

    The SDG page names targets by number ("12.5"); this gives each its label so a
    visitor can read what the number means. Source: data/terms/sdg-targets.csv,
    the taxonomy the pipeline itself loads (its sha256 is recorded in the file)."""
    src = REPO_ROOT / "data" / "terms" / "sdg-targets.csv"
    labels = {}
    goals = {}
    with open(src, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            labels[row["target_id"]] = row["target_label"]
            goals[row["goal_id"]] = row["goal_label"]
    assert len(labels) == 169, f"expected 169 targets, read {len(labels)}"
    assert len(goals) == 17, f"expected 17 goals, read {len(goals)}"
    out = {
        "_what_this_is": "UN SDG goal statements and target labels keyed by id, copied from "
                         "data/terms/sdg-targets.csv so the SDG page can say what a goal or target number means.",
        "_source_sha256": sha256_file(src),
        "goals": goals,
        "targets": labels,
    }
    path = data_dir / "sdg_targets.json"
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    return path


def build_prototype_data():
    verify_inputs()

    data_dir = REPO_ROOT / "prototype" / "data"
    labels_path = write_target_labels(data_dir)
    print(f"  Wrote target labels: {labels_path.relative_to(REPO_ROOT)}")
    projects_dir = data_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    table_path = EXPECTED_HASHES["mapping_table"][0]
    figures_path = EXPECTED_HASHES["figures_document"][0]
    metrics_path = EXPECTED_HASHES["metrics_artefact"][0]

    with open(figures_path, encoding="utf-8") as f:
        figures_doc = json.load(f)

    with open(metrics_path, encoding="utf-8") as f:
        metrics_doc = json.load(f)

    print("\nProcessing mapping table...")
    projects = {}
    total_rows = 0
    hyphen_titles_seen = set()

    with open(table_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED_COLUMNS:
            sys.exit(
                f"REFUSED: mapping table columns do not match contract.\n"
                f"Expected: {EXPECTED_COLUMNS}\n"
                f"Actual:   {reader.fieldnames}"
            )

        for r in reader:
            total_rows += 1
            pid = r["project_id"]
            title = r["title"]
            level = r["assignment_level"]

            if title.startswith("-"):
                hyphen_titles_seen.add(pid)

            if pid not in projects:
                projects[pid] = {
                    "id": pid,
                    "acronym": r["acronym"],
                    "title": title,
                    "sources_present": [
                        s.strip() for s in r["sources_present"].split(",") if s.strip()
                    ],
                    "sources_absent": (
                        []
                        if r["sources_absent"] == "(none absent)"
                        else [s.strip() for s in r["sources_absent"].split(",") if s.strip()]
                    ),
                    "overflow": int(r["overflow_beyond_cap"]),
                    "snapshot_sha256": r["snapshot_sha256"],
                    "pipeline_commit": r["pipeline_commit"],
                    "explanation_marker": r["explanation"],
                    "prompt_marker": r["prompt_sha256"],
                    "assignments": [],
                }

            if level in ("target", "goal_only"):
                projects[pid]["assignments"].append({
                    "target_uri": r["sdg_target_uri"],
                    "target_label": r["sdg_target_label"],
                    "goal_uri": r["sdg_goal_uri"],
                    "goal_label": r["sdg_goal_label"],
                    "level": level,
                    "confidence_band": r["confidence_band"],
                    "score": float(r["score"]) if r["score"] else 0.0,
                    "evidence": r["matched_phrases_and_source_fields"],
                })

    print(f"  Parsed {total_rows} rows across {len(projects)} unique projects.")
    print(f"  Preserved unescaped hyphen-leading titles for projects: {sorted(hyphen_titles_seen)}")

    assert len(projects) == 23451, f"Expected 23,451 projects, got {len(projects)}"
    assert total_rows == 28833, f"Expected 28,833 rows, got {total_rows}"
    assert hyphen_titles_seen == {"101073045", "101275778"}, "Hyphen titles missing"

    # Build compact search index
    print("\nBuilding search index...")
    search_index = []
    projects_with_target = 0
    projects_goal_only = 0
    projects_unassigned = 0

    for pid in sorted(projects.keys()):
        p = projects[pid]
        goals = sorted(list(set(
            a["goal_uri"].split("/")[-1]
            for a in p["assignments"]
            if a.get("goal_uri") and a["goal_uri"].startswith("http")
        )))
        targets = sorted(list(set(
            a["target_uri"].split("/")[-1]
            for a in p["assignments"]
            if a.get("target_uri") and a["target_uri"].startswith("http")
        )))
        has_targets = any(a["level"] == "target" for a in p["assignments"])
        has_goals = any(a["level"] == "goal_only" for a in p["assignments"])

        if has_targets:
            level_tag = "target"
            projects_with_target += 1
        elif has_goals:
            level_tag = "goal_only"
            projects_goal_only += 1
        else:
            level_tag = "none"
            projects_unassigned += 1

        bands = [a["confidence_band"] for a in p["assignments"] if a.get("confidence_band") in ("high", "medium", "low")]
        if "high" in bands:
            top_band = "high"
        elif "medium" in bands:
            top_band = "medium"
        elif "low" in bands:
            top_band = "low"
        else:
            top_band = "none"

        prefix = pid[:5]
        search_index.append({
            "id": pid,
            "acronym": p["acronym"],
            "title": p["title"],
            "goals": goals,
            "targets": targets,
            "level": level_tag,
            "band": top_band,
            "shard": prefix,
        })

    print(f"  Projects with target: {projects_with_target} (expected 9,394)")
    print(f"  Projects goal only:   {projects_goal_only} (expected 6,882)")
    print(f"  Projects unassigned:  {projects_unassigned} (expected 7,175)")

    assert projects_with_target == 9394, f"Mismatch on projects_with_target: {projects_with_target}"
    assert projects_goal_only == 6882, f"Mismatch on projects_goal_only: {projects_goal_only}"
    assert projects_unassigned == 7175, f"Mismatch on projects_unassigned: {projects_unassigned}"

    # Build sharded project details
    print("\nWriting sharded project details...")
    shards = defaultdict(dict)
    for pid in sorted(projects.keys()):
        prefix = pid[:5]
        shards[prefix][pid] = projects[pid]

    for prefix in sorted(shards.keys()):
        shard_path = projects_dir / f"{prefix}.json"
        with open(shard_path, "w", encoding="utf-8", newline="") as f:
            json.dump(shards[prefix], f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"  Wrote {len(shards)} project shard files into {projects_dir.relative_to(REPO_ROOT)}")

    # Write search index
    index_path = data_dir / "projects_index.json"
    with open(index_path, "w", encoding="utf-8", newline="") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=1)
    print(f"  Wrote search index: {index_path.relative_to(REPO_ROOT)}")

    # Build corpus summary
    print("\nWriting corpus summary...")
    summary = {
        "_what_this_is": "Static data manifest & aggregated metrics for §6 item 7 web prototype.",
        "provenance": {
            "registration_v10_sha256": "c5f2a26ce6049e801a7e757efc2cbe4253689987fad761f1d97cfb5b0ad68fb2",
            "pipeline_commit": figures_doc.get("pipeline_commit"),
            "snapshot_sha256": figures_doc.get("snapshot_sha256"),
            "mapping_table_sha256": EXPECTED_HASHES["mapping_table"][1],
            "figures_doc_sha256": EXPECTED_HASHES["figures_document"][1],
            "metrics_artefact_sha256": EXPECTED_HASHES["metrics_artefact"][1],
        },
        "figures_svgs": {
            "recall_ceiling": {
                "file": "figures/recall-ceiling.svg",
                "sha256": EXPECTED_HASHES["fig_recall_ceiling"][1],
                "title": "Recall Ceiling on Reference Set",
            },
            "disagreement_shape": {
                "file": "figures/disagreement-shape.svg",
                "sha256": EXPECTED_HASHES["fig_disagreement_shape"][1],
                "title": "Disagreement Shape on Evaluation 100",
            },
            "goals_by_project_count": {
                "file": "figures/goals-by-project-count.svg",
                "sha256": EXPECTED_HASHES["fig_goals_by_project"][1],
                "title": "SDG Goals by Project Count",
            },
            "most_linked_targets": {
                "file": "figures/most-linked-targets.svg",
                "sha256": EXPECTED_HASHES["fig_most_linked_targets"][1],
                "title": "Most Linked SDG Targets Across Horizon Europe",
            },
            "relevance_by_field": {
                "file": "figures/relevance-by-field.svg",
                "sha256": EXPECTED_HASHES["fig_relevance_by_field"][1],
                "title": "SDG Relevance by Scientific Field (EuroSciVoc)",
            },
            "confidence_bands": {
                "file": "figures/confidence-bands.svg",
                "sha256": EXPECTED_HASHES["fig_confidence_bands"][1],
                "title": "Confidence Bands Across Mappings",
            },
        },
        "corpus_shape": {
            "total_projects": len(projects),
            "total_rows": total_rows,
            "projects_with_target": projects_with_target,
            "projects_goal_level_only": projects_goal_only,
            "projects_unassigned": projects_unassigned,
        },
        "validation_metrics": {
            "evaluation_100": {
                "target_level": metrics_doc.get("target_level"),
                "goal_level_secondary": metrics_doc.get("goal_level_secondary"),
                "recall_ceiling": metrics_doc.get("recall_ceiling"),
                "reference_note": metrics_doc.get("reference", {}).get("_sole_reference"),
                "human_anchor_status": metrics_doc.get("human_anchor", {}).get("why"),
            },
            "development_50": {
                "cohens_kappa": metrics_doc.get("self_proof_against_seq_129", {})
                .get("target_level", {})
                .get("cohens_kappa"),
                "agreement_rate": metrics_doc.get("self_proof_against_seq_129", {})
                .get("target_level", {})
                .get("agreement_rate"),
            },
        },
        "distributions": {
            "goals": figures_doc.get("goals_by_project_count", []),
            "most_linked_targets": figures_doc.get("most_linked_targets", []),
            "least_linked_targets": figures_doc.get("least_linked_targets", {}),
            "confidence_bands": figures_doc.get("confidence_bands", []),
            "by_scientific_field": figures_doc.get("by_scientific_field", []),
            "by_organisation_type": figures_doc.get("by_organisation_type", []),
            "by_duration": figures_doc.get("by_duration", []),
            "by_country_top10": figures_doc.get("by_country", [])[:10],
            "by_programme_top10": figures_doc.get("by_programme_master_call", [])[:10],
        },
    }

    summary_path = data_dir / "corpus_summary.json"
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"  Wrote summary: {summary_path.relative_to(REPO_ROOT)}")

    # Condition 2 Guard (seq 289/291/300): Compare before copy; refuse if any copy differs from original
    print("  Checking figure copies against originals for drift...")
    proto_fig_dir = REPO_ROOT / "prototype" / "figures"
    proto_fig_dir.mkdir(parents=True, exist_ok=True)
    for key, (src_path, expected_hash) in EXPECTED_HASHES.items():
        if key.startswith("fig_"):
            dest_path = proto_fig_dir / src_path.name
            src_bytes = src_path.read_bytes()
            src_hash = hashlib.sha256(src_bytes).hexdigest()
            if src_hash != expected_hash:
                raise AssertionError(
                    f"Original figure corrupted: {src_path} has hash {src_hash}, expected {expected_hash}"
                )
            if dest_path.exists():
                dest_bytes = dest_path.read_bytes()
                dest_hash = hashlib.sha256(dest_bytes).hexdigest()
                if dest_hash != src_hash:
                    raise AssertionError(
                        f"Figure drift detected: {dest_path.name} in prototype/figures ({dest_hash}) "
                        f"differs from original {src_path} ({src_hash})"
                    )
            else:
                dest_path.write_bytes(src_bytes)
    print(f"  Verified 6 notebook SVGs in {proto_fig_dir.relative_to(REPO_ROOT)}: zero drift against originals.")

    # Condition 1 Guard (seq 291/300): Refuse if evaluation metrics diverge from artefact
    print("  Checking evaluation metrics contract against metrics artefact...")
    t_prec = round(float(metrics_doc["target_level"]["precision"]), 3)
    t_rec = round(float(metrics_doc["target_level"]["recall"]), 3)
    c_ceil = round(float(metrics_doc["recall_ceiling"]["ceiling"]), 3)
    c_unreach = metrics_doc["recall_ceiling"]["with_no_evidence_at_any_threshold"]
    c_pairs = metrics_doc["recall_ceiling"]["reference_pairs"]
    d_kappa = round(float(metrics_doc["self_proof_against_seq_129"]["target_level"]["cohens_kappa"]), 3)

    if (t_prec, t_rec, c_ceil, c_unreach, c_pairs, d_kappa) != (0.447, 0.221, 0.442, 53, 95, 0.677):
        raise AssertionError(
            f"Evaluation metrics drift in {EXPECTED_HASHES['metrics_artefact'][0]}: "
            f"got P={t_prec}, R={t_rec}, Ceiling={c_ceil} ({c_unreach}/{c_pairs}), Kappa={d_kappa}; "
            f"expected P=0.447, R=0.221, Ceiling=0.442 (53/95), Kappa=0.677"
        )
    print(f"  Verified evaluation metrics: P={t_prec}, R={t_rec}, Ceiling={c_ceil} ({c_unreach}/{c_pairs}), Kappa={d_kappa}")

    # Verification pass over generated assets
    print("\nVerifying generated prototype assets...")
    assert summary_path.is_file()
    assert index_path.is_file()

    with open(index_path, encoding="utf-8") as f:
        read_index = json.load(f)
    assert len(read_index) == 23451

    total_sharded_projects = 0
    for shard_file in sorted(projects_dir.glob("*.json")):
        with open(shard_file, encoding="utf-8") as f:
            shard_data = json.load(f)
            total_sharded_projects += len(shard_data)

    assert total_sharded_projects == 23451
    print(f"  All 23,451 projects verified across {len(shards)} shards.")
    print("SUCCESS: Prototype static data generated and verified with all guards active.")


if __name__ == "__main__":
    build_prototype_data()
