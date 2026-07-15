import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_tests import (
    detect_runtime,
    discover_bin_test_scripts,
    discover_flavors,
)


class DetectRuntimeTests(unittest.TestCase):
    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n in {"podman", "docker"} else None)
    def test_auto_prefers_podman_when_both_present(self, _):
        self.assertEqual(detect_runtime(), "podman")

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "docker" else None)
    def test_auto_falls_back_to_docker(self, _):
        self.assertEqual(detect_runtime(), "docker")

    @patch("run_tests.shutil.which", return_value=None)
    def test_auto_raises_when_none_present(self, _):
        with self.assertRaises(SystemExit) as cm:
            detect_runtime()
        self.assertIn("no container runtime", str(cm.exception))

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "podman" else None)
    def test_explicit_podman_succeeds(self, _):
        self.assertEqual(detect_runtime("podman"), "podman")

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "podman" else None)
    def test_explicit_docker_raises_when_missing(self, _):
        with self.assertRaises(SystemExit) as cm:
            detect_runtime("docker")
        self.assertIn("'docker'", str(cm.exception))
        self.assertIn("not on PATH", str(cm.exception))

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "docker" else None)
    def test_auto_string_is_treated_as_auto_detect(self, _):
        # Passing the literal "auto" sentinel should not be treated as a runtime name.
        self.assertEqual(detect_runtime("auto"), "docker")


class DiscoverFlavorsTests(unittest.TestCase):
    def _make_repo(self, root: Path, dockerfiles: list[str]) -> None:
        docker_dir = root / "tests" / "docker"
        docker_dir.mkdir(parents=True)
        for name in dockerfiles:
            (docker_dir / name).touch()

    def test_returns_sorted_flavors_from_dockerfiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile.ubuntu", "Dockerfile.alpine", "Dockerfile.fedora"])
            self.assertEqual(discover_flavors(root), ["alpine", "fedora", "ubuntu"])

    def test_ignores_plain_dockerfile_without_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile", "Dockerfile.debian"])
            self.assertEqual(discover_flavors(root), ["debian"])

    def test_returns_empty_when_docker_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(discover_flavors(Path(tmpdir)), [])

    def test_returns_empty_when_no_dockerfiles_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests" / "docker").mkdir(parents=True)
            self.assertEqual(discover_flavors(root), [])

    def test_picks_up_suffixed_variants(self):
        # Sanity: discoverer uses glob("Dockerfile.*"), so an unusual suffix like
        # `.bak` would also match. That's by design — it's the author's job to
        # only commit real dockerfiles. Lock in current behavior.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile.alpine", "Dockerfile.bak"])
            self.assertEqual(discover_flavors(root), ["alpine", "bak"])


class DiscoverBinTestScriptsTests(unittest.TestCase):
    def _make_bin(self, root: Path, files: dict[str, str]) -> None:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, content in files.items():
            (bin_dir / name).write_text(content)

    def test_finds_python_script_with_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root,
                {
                    "withtests": '#!/usr/bin/env python3\nif "--run-tests" in sys.argv:\n    pass\n',
                    "notests": "#!/usr/bin/env python3\nprint('hi')\n",
                },
            )
            found = [p.name for p in discover_bin_test_scripts(root)]
            self.assertEqual(found, ["withtests"])

    def test_ignores_non_python_shebang(self):
        # A shell script that only mentions the marker in a comment is skipped.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root, {"shscript": "#!/bin/sh\n# --run-tests unsupported\necho hi\n"}
            )
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_skips_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(root, {})
            (root / "bin" / "__pycache__").mkdir()
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_returns_empty_when_bin_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(discover_bin_test_scripts(Path(tmpdir)), [])

    def test_results_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root,
                {
                    "bbb": '#!/usr/bin/env python3\n"--run-tests"\n',
                    "aaa": '#!/usr/bin/env python3\n"--run-tests"\n',
                },
            )
            found = [p.name for p in discover_bin_test_scripts(root)]
            self.assertEqual(found, ["aaa", "bbb"])
