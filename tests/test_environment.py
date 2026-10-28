import unittest
from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from unittest.mock import patch

from training import environment


class RuntimeMetadataTests(unittest.TestCase):
    def test_records_platform_and_installed_package_versions(self):
        def package_version(name):
            if name == "bitsandbytes":
                raise PackageNotFoundError(name)
            return f"{name}-version"

        with patch.object(environment.platform, "python_version", return_value="3.12.1"), \
             patch.object(environment.platform, "platform", return_value="macOS-test"), \
             patch.object(environment.platform, "machine", return_value="arm64"), \
             patch.object(environment.importlib.metadata, "version", side_effect=package_version), \
             patch.object(environment, "_source_state", return_value=("a" * 40, False)):
            details = environment.runtime_metadata("mps")

        self.assertEqual(details["python_version"], "3.12.1")
        self.assertEqual(details["platform"], "macOS-test")
        self.assertEqual(details["machine"], "arm64")
        self.assertEqual(details["device"], "mps")
        self.assertEqual(details["source_revision"], "a" * 40)
        self.assertFalse(details["source_dirty"])
        self.assertEqual(details["packages"]["transformers"], "transformers-version")
        self.assertIsNone(details["packages"]["bitsandbytes"])

    def test_source_state_reads_commit_and_dirty_status_without_exposing_paths(self):
        output = "# branch.oid " + "b" * 40 + "\n# branch.head feature\n1 .M N... 100644 100644 100644 abc def file.py\n"
        with patch.object(environment.subprocess, "run", return_value=SimpleNamespace(stdout=output)) as run:
            state = environment._source_state()

        self.assertEqual(state, ("b" * 40, True))
        self.assertEqual(run.call_count, 1)
        self.assertIn("--porcelain=v2", run.call_args.args[0])

    def test_source_state_is_unknown_when_git_is_unavailable(self):
        with patch.object(environment.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(environment._source_state(), (None, None))


if __name__ == "__main__":
    unittest.main()
