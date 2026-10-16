import unittest

from tools.prepare_package import package_metadata, validate_version


class ReleaseTest(unittest.TestCase):
    def test_wrong_tag_or_package_version_rejected(self):
        for version, package_version, tag in (
            ('0.6.0', '0.6.0', 'v0.5.0'),
            ('0.6.0', '0.5.0', 'v0.6.0'),
            ('0.6.0', '0.6.0', 'v0.6.0-rc1'),
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_version(version, package_version, tag)

    def test_matching_tag_and_branch_build_accepted(self):
        validate_version('0.6.0', '0.6.0', 'v0.6.0')
        validate_version('0.6.0', '0.6.0')

    def test_generated_metadata_uses_exact_asset_checksum(self):
        template = "pkgver=0.6.0\nsource=('fixed-version-url')\nsha256sums=('old')\n"
        result = package_metadata(template, '0.6.0', 'a' * 64, 'v0.6.0')
        self.assertIn("sha256sums=('" + 'a' * 64 + "')", result)
        self.assertIn("source=('fixed-version-url')", result)
        with self.assertRaises(ValueError):
            package_metadata(template.replace('sha256sums', 'other'), '0.6.0', 'a' * 64)
