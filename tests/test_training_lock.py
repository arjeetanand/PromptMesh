import tempfile
import unittest
from pathlib import Path

from training.verify_lock import compare_pins, platform_issues, read_exact_pins


class TrainingLockTests(unittest.TestCase):
    def test_reads_exact_pins_and_normalizes_package_names(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "training.lock"
            lock.write_text("# comment\nTorch==2.14.1\npackaging==26.3\n", encoding="utf-8")

            self.assertEqual(read_exact_pins(lock), {"torch": "2.14.1", "packaging": "26.3"})

    def test_rejects_non_exact_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "training.lock"
            for content in ("torch>=2.0\n", "torch==2.0.*\n", "torch[extra]==2.0\n"):
                with self.subTest(content=content):
                    lock.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "exact version pin"):
                        read_exact_pins(lock)

    def test_rejects_duplicate_names_after_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "training.lock"
            lock.write_text("Torch==2.14.1\ntorch==2.14.1\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate normalized package"):
                read_exact_pins(lock)

    def test_reports_missing_and_mismatched_installed_versions(self):
        missing, mismatched = compare_pins(
            {"torch": "2.14.1", "peft": "0.21.2", "bitsandbytes": "0.50.0"},
            {"Torch": "2.14.1", "peft": "0.21.1"},
        )

        self.assertEqual(missing, ["bitsandbytes"])
        self.assertEqual(mismatched, [("peft", "0.21.2", "0.21.1")])

    def test_lock_platform_gate_accepts_only_python_312_macos_arm64(self):
        self.assertEqual(platform_issues((3, 12), "darwin", "arm64"), [])
        self.assertEqual(len(platform_issues((3, 11), "darwin", "arm64")), 1)
        self.assertEqual(len(platform_issues((3, 12), "linux", "x86_64")), 2)


if __name__ == "__main__":
    unittest.main()
