import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from training import review_packets


class ReviewPacketTests(unittest.TestCase):
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
