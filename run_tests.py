#!/usr/bin/env python3
"""
This script performs testing for the dotfiles repository.
"""

import argparse
import logging
import shutil
import subprocess
import sys
import unittest

from pathlib import Path

from _pydotlib.cli import ColoredLogFormatter
from _pydotlib.integration_checks import BOOTSTRAP_CHECKS

RUNTIME_AUTO = "auto"
RUNTIME_CHOICES = (RUNTIME_AUTO, "podman", "docker")


def detect_runtime(preferred: str | None = None) -> str:
    """Resolve a usable container runtime.

    If `preferred` is given (and is not "auto"), require that exact runtime
    to be on PATH or raise. Otherwise probe "podman" then "docker" in order.
    Podman is preferred in auto-detect because it is rootless by default.
    """
    if preferred and preferred != RUNTIME_AUTO:
        if shutil.which(preferred):
            return preferred
        raise SystemExit(f"requested runtime {preferred!r} not on PATH")

    for name in ("podman", "docker"):
        if shutil.which(name):
            return name
    raise SystemExit("no container runtime found (need podman or docker on PATH)")


def check_runtime(runtime: str) -> bool:
    """Verify the runtime can actually talk to its backend."""
    result = subprocess.run(
        [runtime, "version"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        logging.error(
            f"{runtime} version failed (exit {result.returncode}): {result.stderr.strip()}"
        )
        return False
    return True


def format_image_name(flavor: str) -> str:
    return f"dotfiles_{flavor}"


def format_container_name(flavor: str) -> str:
    return f"dotfiles-test-{flavor}"


def discover_flavors(repo_root: Path) -> list[str]:
    """Return distro flavors discovered from tests/docker/Dockerfile.<flavor>."""
    flavors: list[str] = []
    tests_root = repo_root / "tests" / "docker"
    if not tests_root.is_dir():
        return flavors
    for df in sorted(tests_root.glob("Dockerfile.*")):
        flavor = df.suffix.lstrip(".")
        if flavor:
            flavors.append(flavor)
    return flavors


def _log_subprocess_failure(
    header: str, stdout: str | None, stderr: str | None
) -> None:
    """Log a single ERROR record with header and any stdout/stderr collated together."""
    parts = [header]
    if stdout:
        parts.append(f"stdout:\n{stdout.rstrip()}")
    if stderr:
        parts.append(f"stderr:\n{stderr.rstrip()}")
    logging.error("\n".join(parts))


def build_image(runtime: str, repo_root: Path, flavor: str) -> bool:
    """Build the container image for `flavor`. Returns False on failure."""
    dockerfile_path = repo_root / "tests" / "docker" / f"Dockerfile.{flavor}"
    if not dockerfile_path.exists():
        logging.error(f"Dockerfile {dockerfile_path} does not exist")
        return False

    image_name = format_image_name(flavor)
    result = subprocess.run(
        [runtime, "build", "-f", str(dockerfile_path), "-t", image_name, str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _log_subprocess_failure(
            f"{runtime} build failed for {image_name} (exit {result.returncode})",
            result.stdout,
            result.stderr,
        )
        return False
    return True


def remove_container(runtime: str, container_name: str) -> None:
    """Force-remove a container if it exists. Never raises."""
    subprocess.run(
        [runtime, "rm", "-f", container_name],
        capture_output=True,
        text=True,
        check=False,
    )


def run_exec(
    runtime: str,
    container_name: str,
    cmd: list[str],
    *,
    timeout: float,
    label: str,
) -> bool:
    """Run `<runtime> exec` and log output on failure. Returns False on failure/timeout."""
    full_cmd = [runtime, "exec", container_name, *cmd]
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as e:
        # With text=True, e.stdout/e.stderr are str | None — no bytes decode needed.
        _log_subprocess_failure(
            f"{label} timed out after {timeout}s in {container_name}",
            e.stdout,
            e.stderr,
        )
        return False

    if result.returncode != 0:
        _log_subprocess_failure(
            f"{label} failed (exit {result.returncode}) in {container_name}",
            result.stdout,
            result.stderr,
        )
        return False
    return True


def run_container_test(runtime: str, repo_root: Path, flavor: str) -> bool:
    """Build the image, start a container, run bootstrap then verify; always clean up."""
    if not build_image(runtime, repo_root, flavor):
        return False

    container_name = format_container_name(flavor)
    image_name = format_image_name(flavor)
    logging.info(f"Running {flavor} in {container_name} via {runtime}")

    # Defensive: nuke any stale container from a previous crashed run before starting.
    remove_container(runtime, container_name)

    create = subprocess.run(
        [
            runtime,
            "run",
            "-d",
            "--name",
            container_name,
            "-v",
            f"{repo_root}:/home/testuser/.dotfiles:ro",
            image_name,
            "sleep",
            "infinity",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0:
        _log_subprocess_failure(
            f"{runtime} run failed for {container_name} (exit {create.returncode})",
            create.stdout,
            create.stderr,
        )
        return False

    try:
        bootstrap_cmd = [
            "bash",
            "-c",
            (
                "cd /home/testuser/.dotfiles && "
                "python3 bootstrap.py -v "
                "--git-name 'Testy McTestFace' "
                "--git-email 'testy@test.com' "
                "< /dev/null"
            ),
        ]
        if not run_exec(
            runtime, container_name, bootstrap_cmd, timeout=30, label="bootstrap.py"
        ):
            return False

        return run_integration_checks(runtime, container_name)
    finally:
        remove_container(runtime, container_name)


def run_integration_checks(runtime: str, container_name: str) -> bool:
    """Run the BOOTSTRAP_CHECKS suite inside `container_name`, log each, return overall pass."""

    def exec_in_container(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [runtime, "exec", container_name, *cmd],
            capture_output=True,
            text=True,
            check=False,
        )

    all_passed = True
    for check in BOOTSTRAP_CHECKS:
        result = check(exec_in_container)
        if result.passed:
            logging.info(f"  ✓ {result.name}")
        else:
            logging.error(f"  ✗ {result.name}: {result.detail}")
            all_passed = False
    return all_passed


def run_shell_syntax_tests() -> bool:
    repo_root = Path(__file__).parent
    all_passed = True

    def check_syntax(shell: str, filepath: Path) -> bool:
        result = subprocess.run(
            [shell, "-n", str(filepath)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logging.error(f"{shell} -n {filepath} failed:\n{result.stderr}")
            return False
        logging.debug(f"{shell} -n {filepath}: OK")
        return True

    # POSIX syntax check on shell_profile/*.sh
    shell_profile_dir = repo_root / "shell_profile"
    if shell_profile_dir.is_dir():
        for sh_file in sorted(shell_profile_dir.glob("*.sh")):
            if not check_syntax("sh", sh_file):
                all_passed = False

    # bash -n on .bash_profile and .bashrc
    for name in [".bash_profile", ".bashrc"]:
        filepath = repo_root / name
        if filepath.exists() and not check_syntax("bash", filepath):
            all_passed = False

    # zsh -n on .zshrc and .zshenv (skip if zsh not installed)
    if shutil.which("zsh"):
        for name in [".zshrc", ".zshenv"]:
            filepath = repo_root / name
            if filepath.exists() and not check_syntax("zsh", filepath):
                all_passed = False
    else:
        logging.info("zsh not found, skipping zsh syntax checks")

    # sh -n on bin/ scripts with #!/bin/sh shebang
    bin_dir = repo_root / "bin"
    if bin_dir.is_dir():
        for entry in sorted(bin_dir.iterdir()):
            if not entry.is_file():
                continue
            try:
                first_line = entry.read_text().split("\n", 1)[0].strip()
            except (UnicodeDecodeError, PermissionError):
                continue
            if first_line == "#!/bin/sh" and not check_syntax("sh", entry):
                all_passed = False

    return all_passed


def run_pydotlib_tests(verbose: bool = False) -> bool:
    loader = unittest.TestLoader()
    repo_root = Path(__file__).parent
    suite = loader.discover(
        start_dir=str(repo_root / "_pydotlib" / "tests"),
        pattern="test_*.py",
        top_level_dir=str(repo_root),
    )

    print()
    print("=" * 70)
    print("Running tests")
    print("=" * 70)
    print()

    # Detach our log handler so that INFO/ERROR records from code under
    # test don't bypass unittest's stdout/stderr capture. assertLogs adds its
    # own handler so tests that exercise log assertions still work.
    root_logger = logging.getLogger()
    saved_handlers = root_logger.handlers[:]
    if not verbose:
        root_logger.handlers = []

    try:
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1, buffer=not verbose
        )
        result = runner.run(suite)
    finally:
        root_logger.handlers = saved_handlers

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)

    return result.wasSuccessful()


def main() -> int:
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging)",
    )
    args_parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=RUNTIME_AUTO,
        help="Container runtime for integration tests (default: auto-detect, podman preferred)",
    )
    docker = args_parser.add_mutually_exclusive_group()
    docker.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip container integration tests",
    )
    docker.add_argument(
        "--docker-only",
        action="store_true",
        help="Run only container integration tests",
    )

    args = args_parser.parse_args()

    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(ColoredLogFormatter())

    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    if not args.docker_only:
        if not run_shell_syntax_tests():
            logging.critical("shell syntax tests failed - aborting")
            return 1

        if not run_pydotlib_tests(verbose=args.verbose):
            logging.critical("pydotlib unit tests failed - aborting")
            return 1

    if not args.no_docker:
        runtime = detect_runtime(args.runtime)
        logging.info(f"using container runtime: {runtime}")
        if not check_runtime(runtime):
            return 1

        repo_root = Path(__file__).parent
        flavors = discover_flavors(repo_root)
        if not flavors:
            logging.warning(f"no Dockerfiles found under {repo_root / 'tests' / 'docker'}")

        all_passed = True
        for flavor in flavors:
            if not run_container_test(runtime, repo_root, flavor):
                all_passed = False
        if not all_passed:
            return 1

    logging.info("All tests passed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
