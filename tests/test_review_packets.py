import csv
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from training import review_packets
from training import datasets


class ReviewPacketTests(unittest.TestCase):
    def test_balanced_group_selection_is_stable_across_candidate_order(self):
        candidates = {
            f"source-{year}-{index:02d}": year
            for year in datasets.YEAR_BALANCED_COHORT_YEARS
            for index in range(14)
        }

        selected = datasets.select_year_balanced_groups(candidates)
        shuffled = datasets.select_year_balanced_groups(dict(reversed(list(candidates.items()))))

        self.assertEqual(selected, shuffled)
        self.assertEqual(len(selected), 72)
        self.assertEqual(len(set(selected)), 72)

    def test_host_diverse_selection_maximizes_hosts_and_fills_repeats_round_robin(self):
        candidates = {
            f"source-{year}-{index:02d}": {
                "year": year,
                "source_host": f"host-{index % 13:02d}.example.org",
            }
            for year in datasets.YEAR_BALANCED_COHORT_YEARS
            for index in range(14)
        }
        selected = datasets.select_year_host_diverse_groups(candidates)
        shuffled = datasets.select_year_host_diverse_groups(dict(reversed(list(candidates.items()))))

        self.assertEqual(selected, shuffled)
        self.assertEqual(len(selected), 72)
        self.assertEqual(len(set(selected)), 72)
        for year in datasets.YEAR_BALANCED_COHORT_YEARS:
            year_groups = [group_id for group_id in selected if candidates[group_id]["year"] == year]
            self.assertEqual(len(year_groups), 12)
            self.assertEqual(len({candidates[group_id]["source_host"] for group_id in year_groups}), 12)

        few_hosts = {
            f"source-{year}-{index:02d}": {
                "year": year,
                "source_host": f"host-{index % 3}.example.org",
            }
            for year in datasets.YEAR_BALANCED_COHORT_YEARS
            for index in range(12)
        }
        repeated = datasets.select_year_host_diverse_groups(few_hosts)
        for year in datasets.YEAR_BALANCED_COHORT_YEARS:
            counts = {}
            for group_id in repeated:
                if few_hosts[group_id]["year"] == year:
                    host = few_hosts[group_id]["source_host"]
                    counts[host] = counts.get(host, 0) + 1
            self.assertEqual(counts, {f"host-{index}.example.org": 4 for index in range(3)})

    def test_host_diverse_selection_rejects_non_https_and_missing_host(self):
        self.assertEqual(datasets.source_host_from_url("https://www.Example.org/article"), "example.org")
        for source_url in ("http://example.org/article", "https:///article", "https://user:pass@example.org/article"):
            with self.subTest(source_url=source_url), self.assertRaisesRegex(ValueError, "HTTPS source URL"):
                datasets.source_host_from_url(source_url)

    def _write_packet(self, directory):
        packet = Path(directory) / "review.csv"
        with packet.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=review_packets.REQUIRED_COLUMNS)
            writer.writeheader()
            for index in range(3):
                writer.writerow({
                    "group_id": "source-1",
                    "input": f"Source phrasing {index}",
                    "proposed_organization": "Actor Org",
                    "proposed_year": "2024",
                    "proposed_claim": "opened a lab",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "source_title": "Official source",
                    "source_url": "https://example.org/source",
                    "source_date": "2024-01-01",
                    "reuse_status": "Public page; reuse permission/license not confirmed.",
                    "review_focus": "Check the actor and event year.",
                })
        return packet

    def _write_reviewable_packet(self, directory, group_count=80, include_pending=True):
        packet = Path(directory) / "review.csv"
        columns = [*review_packets.REQUIRED_COLUMNS, "reuse_evidence"]
        with packet.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for index in range(group_count + int(include_pending)):
                group_id = f"source-{index:03d}"
                year = 2020 + index % 6
                eligible = index < group_count
                for variant in range(3):
                    excluded = eligible and index == 0 and variant == 0
                    writer.writerow({
                        "group_id": group_id,
                        "input": f"Source {index} variant {variant} describes an announcement.",
                        "proposed_organization": "Example actor",
                        "proposed_year": str(year),
                        "proposed_claim": "announced a research project",
                        "review_status": "EXCLUDED" if excluded else "REVIEWED" if eligible else "NEEDS_HUMAN_REVIEW",
                        "reviewed_organization": "Example actor" if eligible and not excluded else "",
                        "reviewed_year": str(year) if eligible and not excluded else "",
                        "reviewed_claim": "announced a research project" if eligible and not excluded else "",
                        "review_notes": "Not supported by the source" if excluded else "Checked against the linked source" if eligible else "",
                        "source_title": f"Official source {index}",
                        "source_url": f"https://source-{index // 6}.example.org/source/{index}",
                        "source_date": f"{year}-01-01",
                        "reuse_status": "permission_confirmed" if eligible else "permission_unconfirmed",
                        "reuse_evidence": "CC BY 4.0 license notice" if eligible else "",
                        "review_focus": f"Verify actor and event year for variant {variant}.",
                    })
        return packet

    def test_packet_groups_related_phrasings_and_keeps_them_unreviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self._write_packet(directory)
            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet):
                result = review_packets.load_review_packet()

        self.assertEqual((result["total_rows"], result["total_groups"]), (3, 1))
        self.assertEqual(result["reviewed_rows"], 0)
        self.assertEqual(len(result["groups"][0]["rows"]), 3)
        self.assertFalse(result["groups"][0]["eligible"])
        self.assertFalse(result["export_preview"]["ready"])
        self.assertIn("Only 0 export-eligible groups", result["export_preview"]["reason"])

    def test_export_uses_only_reviewed_variants_with_group_rights_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self._write_reviewable_packet(root)
            data_dir = root / "datasets"
            data_dir.mkdir()
            with patch.object(review_packets, "REVIEW_PACKET_DIR", root), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet), \
                 patch.object(datasets, "DATASET_DIR", data_dir):
                preview = review_packets.load_review_packet()
                result = review_packets.export_reviewed_dataset("reviewed_sources_v1", "project author")
                rows, digest = datasets.load_dataset_snapshot("reviewed_sources_v1")
                card = datasets.load_benchmark_card("reviewed_sources_v1", rows, digest)
                status = datasets.benchmark_card_status("reviewed_sources_v1", rows, digest)
                data_path = data_dir / "reviewed_sources_v1.jsonl"
                card_path = data_dir / "reviewed_sources_v1.card.json"
                original_data = data_path.read_bytes()
                original_card = card_path.read_bytes()

                with self.assertRaisesRegex(FileExistsError, "already exists"):
                    review_packets.export_reviewed_dataset("reviewed_sources_v1", "project author")

            group_counts = {}
            for row in rows:
                group_counts[row["group_id"]] = group_counts.get(row["group_id"], 0) + 1
            self.assertTrue(preview["export_preview"]["ready"])
            self.assertEqual(result["examples"], 239)
            self.assertEqual(result["source_groups"], 80)
            self.assertEqual(group_counts["source-000"], 2, "explicitly excluded variants must not enter the dataset")
            self.assertNotIn("source-080", group_counts, "pending groups must stay out of the dataset")
            self.assertEqual(card["annotation"]["reviewer_role"], "project author")
            self.assertEqual(len(card["source"]["references"]), 80)
            self.assertEqual(card["source"]["references"][0]["reuse_evidence"], "CC BY 4.0 license notice")
            self.assertTrue(status["card_ready"] and status["validation_ready"] and status["final_test_ready"])
            self.assertEqual(stat.S_IMODE(data_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(card_path.stat().st_mode), 0o600)
            self.assertEqual(data_path.read_bytes(), original_data)
            self.assertEqual(card_path.read_bytes(), original_card)
            self.assertEqual(json.loads(original_card)["dataset_sha256"], digest)

    def test_export_refuses_a_split_below_benchmark_floors_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self._write_reviewable_packet(root, group_count=12, include_pending=False)
            data_dir = root / "datasets"
            data_dir.mkdir()
            with patch.object(review_packets, "REVIEW_PACKET_DIR", root), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet), \
                 patch.object(datasets, "DATASET_DIR", data_dir):
                preview = review_packets.load_review_packet()["export_preview"]
                with self.assertRaisesRegex(ValueError, "at least 30 examples across 10 source groups"):
                    review_packets.export_reviewed_dataset("too_small_v1", "project author")

            self.assertFalse(preview["ready"])
            self.assertFalse((data_dir / "too_small_v1.jsonl").exists())
            self.assertFalse((data_dir / "too_small_v1.card.json").exists())

    def test_balanced_preview_requires_reviewed_groups_in_each_target_year(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self._write_reviewable_packet(directory, group_count=72, include_pending=False)
            with packet.open("r", encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            for row in rows:
                if row["group_id"] == "source-005":
                    row["reviewed_year"] = "2024"
            with packet.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet):
                original = packet.read_bytes()
                preview = review_packets.load_review_packet()["balanced_export_preview"]
                after_preview = packet.read_bytes()

        self.assertFalse(preview["ready"])
        self.assertEqual(preview["candidate_groups_by_year"]["2025"], 11)
        self.assertIn("2025: 11/12", preview["reason"])
        self.assertEqual(original, after_preview, "previewing a cohort does not modify human review decisions")

    def test_balanced_export_is_deterministic_and_records_reviewed_year_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self._write_reviewable_packet(root, group_count=84, include_pending=False)
            data_dir = root / "datasets"
            data_dir.mkdir()
            with patch.object(review_packets, "REVIEW_PACKET_DIR", root), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet), \
                 patch.object(datasets, "DATASET_DIR", data_dir):
                preview = review_packets.load_review_packet()["balanced_export_preview"]
                packet_before_export = packet.read_bytes()
                result = review_packets.export_reviewed_dataset(
                    "balanced_sources_v1", "project author", "balanced_year_12"
                )
                rows, digest = datasets.load_dataset_snapshot("balanced_sources_v1")
                card = datasets.load_benchmark_card("balanced_sources_v1", rows, digest)
                status = datasets.benchmark_card_status("balanced_sources_v1", rows, digest)
                packet_after_export = packet.read_bytes()

            year_group_counts = {}
            for row in rows:
                group_year = year_group_counts.setdefault(row["group_id"], row["output"]["year"])
                self.assertEqual(group_year, row["output"]["year"])
            self.assertEqual(
                {str(year): sum(group_year == year for group_year in year_group_counts.values()) for year in range(2020, 2026)},
                {str(year): 12 for year in range(2020, 2026)},
            )
            self.assertEqual(card["schema_version"], 3)
            self.assertEqual(card["cohort"]["strategy"], datasets.YEAR_HOST_DIVERSE_COHORT)
            self.assertEqual(card["cohort"]["candidate_group_metadata"], preview["candidate_group_metadata"])
            self.assertEqual(card["cohort"]["selected_group_ids"], preview["selected_group_ids"])
            self.assertEqual({item["group_id"] for item in card["source"]["references"]}, set(preview["selected_group_ids"]))
            self.assertEqual(len(card["cohort"]["candidate_group_metadata"]), 84)
            self.assertEqual(len(card["cohort"]["selected_group_ids"]), 72)
            self.assertEqual(result["cohort"]["mode"], "balanced_year_12")
            self.assertEqual(result["cohort"]["selected_groups_by_year"], {str(year): 12 for year in range(2020, 2026)})
            self.assertEqual(result["cohort"]["selected_source_hosts_by_year"], {str(year): 12 for year in range(2020, 2026)})
            self.assertTrue(status["card_ready"] and status["validation_ready"] and status["final_test_ready"])
            self.assertEqual(packet_before_export, packet_after_export)

            card_path = data_dir / "balanced_sources_v1.card.json"
            tampered = json.loads(card_path.read_text(encoding="utf-8"))
            tampered["cohort"]["selected_group_ids"].reverse()
            card_path.write_text(json.dumps(tampered), encoding="utf-8")
            with patch.object(datasets, "DATASET_DIR", data_dir):
                with self.assertRaisesRegex(ValueError, "does not match its candidates and deterministic rule"):
                    datasets.load_benchmark_card("balanced_sources_v1", rows, digest)

            tampered = json.loads(card_path.read_text(encoding="utf-8"))
            tampered["cohort"]["selected_group_ids"] = card["cohort"]["selected_group_ids"]
            reference = tampered["source"]["references"][0]
            reference["url"] = reference["url"].rstrip("/") + "/tampered"
            card_path.write_text(json.dumps(tampered), encoding="utf-8")
            with patch.object(datasets, "DATASET_DIR", data_dir):
                with self.assertRaisesRegex(ValueError, "source URL does not match its candidate metadata"):
                    datasets.load_benchmark_card("balanced_sources_v1", rows, digest)

    def test_schema_v2_year_balanced_cards_remain_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            candidate_group_years = {
                f"legacy-{year}-{index:02d}": year
                for year in datasets.YEAR_BALANCED_COHORT_YEARS
                for index in range(14)
            }
            selected = datasets.select_year_balanced_groups(candidate_group_years)
            rows = [
                {
                    "group_id": group_id,
                    "input": f"Source {group_id} variant {variant}.",
                    "output": {
                        "organization": "Example actor",
                        "year": candidate_group_years[group_id],
                        "claim": "announced a research project",
                    },
                }
                for group_id in selected
                for variant in range(3)
            ]
            content = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows).encode()
            digest = hashlib.sha256(content).hexdigest()
            card = {
                "schema_version": 2,
                "dataset_id": "legacy_balanced",
                "dataset_sha256": digest,
                "task": "entity_extraction",
                "source": {
                    "description": "Human-reviewed public-source entity-extraction examples.",
                    "authorization_or_license": "Source-level evidence is listed in references.",
                    "references": [
                        {"group_id": group_id, "title": group_id, "url": "https://example.org/source", "reuse_evidence": "CC BY 4.0"}
                        for group_id in selected
                    ],
                },
                "grouping": {"unit": "one public source fact per group", "policy": "Legacy year-balanced cohort."},
                "annotation": {
                    "guidelines_version": "entity-extraction-v1",
                    "review_status": "human_reviewed",
                    "all_labels_human_reviewed": True,
                    "total_examples": len(rows),
                    "reviewed_examples": len(rows),
                    "total_source_groups": len(selected),
                    "reviewed_source_groups": len(selected),
                    "reviewed_at_utc": "2026-10-29T00:00:00Z",
                    "reviewer_role": "domain reviewer",
                },
                "limitations": ["Local review self-attestation."],
                "cohort": {
                    "strategy": datasets.YEAR_BALANCED_COHORT,
                    "seed": datasets.YEAR_BALANCED_COHORT_SEED,
                    "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR,
                    "years": list(datasets.YEAR_BALANCED_COHORT_YEARS),
                    "candidate_group_years": [
                        {"group_id": group_id, "year": candidate_group_years[group_id]}
                        for group_id in sorted(candidate_group_years)
                    ],
                    "selected_group_ids": selected,
                },
            }
            (data_dir / "legacy_balanced.jsonl").write_bytes(content)
            (data_dir / "legacy_balanced.card.json").write_text(json.dumps(card), encoding="utf-8")
            with patch.object(datasets, "DATASET_DIR", data_dir):
                loaded_rows, loaded_digest = datasets.load_dataset_snapshot("legacy_balanced")
                loaded_card = datasets.load_benchmark_card("legacy_balanced", loaded_rows, loaded_digest)

        self.assertEqual(loaded_card["schema_version"], 2)

    def test_export_rolls_back_dataset_if_card_creation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self._write_reviewable_packet(root, include_pending=False)
            data_dir = root / "datasets"
            data_dir.mkdir()
            original_link = os.link
            calls = 0

            def fail_second_link(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise FileExistsError("simulated card collision")
                return original_link(source, destination)

            with patch.object(review_packets, "REVIEW_PACKET_DIR", root), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet), \
                 patch.object(datasets, "DATASET_DIR", data_dir), \
                 patch.object(review_packets.os, "link", side_effect=fail_second_link):
                with self.assertRaisesRegex(FileExistsError, "simulated card collision"):
                    review_packets.export_reviewed_dataset("rollback_v1", "project author")

            self.assertFalse((data_dir / "rollback_v1.jsonl").exists())
            self.assertFalse((data_dir / "rollback_v1.card.json").exists())

    def test_review_save_records_actor_label_and_permission_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self._write_packet(directory)
            updates = [
                {
                    "row_index": index,
                    "review_status": "REVIEWED",
                    "reviewed_organization": "Actor Org",
                    "reviewed_year": 2024,
                    "reviewed_claim": "opened a lab",
                    "review_notes": "Checked against source",
                }
                for index in range(3)
            ]
            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet):
                result = review_packets.save_group_review(
                    "source-1", updates, "permission_confirmed", "CC BY 4.0 source notice"
                )
                with packet.open(encoding="utf-8", newline="") as source:
                    saved = list(csv.DictReader(source))

        self.assertEqual(result["reviewed_rows"], 3)
        self.assertEqual(result["eligible_groups"], 1)
        self.assertTrue(all(row["reviewed_organization"] == "Actor Org" for row in saved))
        self.assertTrue(all(row["reuse_evidence"] == "CC BY 4.0 source notice" for row in saved))

    def test_invalid_review_does_not_change_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self._write_packet(directory)
            original = packet.read_bytes()
            updates = [{"row_index": index} for index in range(3)]
            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", packet):
                with self.assertRaisesRegex(ValueError, "permission or license evidence"):
                    review_packets.save_group_review(
                        "source-1", updates, "permission_confirmed", ""
                    )
                with self.assertRaisesRegex(ValueError, "do not match"):
                    review_packets.save_group_review(
                        "source-1", [{**row, "row_index": 9} for row in updates],
                        "permission_unconfirmed", "",
                    )
            self.assertEqual(packet.read_bytes(), original)

    def test_packet_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "outside.csv"
            outside.write_text("group_id\nsource-1\n", encoding="utf-8")
            link = Path(directory) / "review.csv"
            link.symlink_to(outside)
            with patch.object(review_packets, "REVIEW_PACKET_DIR", Path(directory)), \
                 patch.object(review_packets, "REVIEW_PACKET_PATH", link):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    review_packets.load_review_packet()


if __name__ == "__main__":
    unittest.main()
