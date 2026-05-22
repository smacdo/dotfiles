import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_tests import detect_runtime, discover_flavors


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
