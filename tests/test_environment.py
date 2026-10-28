import unittest
from importlib.metadata import PackageNotFoundError
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
             patch.object(environment.importlib.metadata, "version", side_effect=package_version):
            details = environment.runtime_metadata("mps")

        self.assertEqual(details["python_version"], "3.12.1")
        self.assertEqual(details["platform"], "macOS-test")
        self.assertEqual(details["machine"], "arm64")
        self.assertEqual(details["device"], "mps")
        self.assertEqual(details["packages"]["transformers"], "transformers-version")
        self.assertIsNone(details["packages"]["bitsandbytes"])


if __name__ == "__main__":
    unittest.main()
