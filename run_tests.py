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

logger = logging.getLogger(__name__)

DOCKER_FLAVORS = ["debian", "ubuntu", "fedora", "alpine"]


def check_docker() -> bool:
    """Check that Docker is installed on the system. Logs warnings if a check fails."""
    if shutil.which("docker") is None:
        logging.warning("Docker was not found. Please install docker.")
        return False

    try:
        subprocess.check_output(["docker", "version"])
        return True
    except subprocess.CalledProcessError:
        logging.warning(
            "Docker failed to start. Please check that the Docker daemon is running."
        )
        return False


def format_docker_image_name(target: str, flavor: str) -> str:
    return f"dotfiles_{target}_{flavor}"


def format_docker_container_name(target: str, flavor: str) -> str:
    return f"dotfiles-test-{target}-{flavor}"


def build_docker_image(target: str, flavor: str) -> bool:
    dockerfile_path = (
        Path(__file__).parent / "tests" / "docker" / target / f"Dockerfile.{flavor}"
    )

    if not dockerfile_path.exists():
        logging.error(f"Docker file {dockerfile_path} does not exist")
        return False

    subprocess.check_output(
        [
            "docker",
            "build",
            "-f",
            dockerfile_path,
            "-t",
            format_docker_image_name(target, flavor),
            ".",
        ]
    )
    return True


def docker_container_exists(target: str, flavor: str) -> bool:
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )

    containers = [line.strip() for line in result.stdout.splitlines()]

    return format_docker_container_name(target, flavor) in containers


def delete_docker_container(target: str, flavor: str) -> bool:
    container_name = format_docker_container_name(target, flavor)

    if not docker_container_exists(target, flavor):
        logging.info(
            f"Could not delete container {container_name} because it was not found"
        )
        return False

    # Remove the container.
    subprocess.check_output(
        [
            "docker",
            "rm",
            "-f",
            container_name,
        ]
    )

    logging.info(f"Deleted container {container_name}")

    return True


def run_docker_test(target: str, flavor: str) -> bool:
    # Make sure the image is built before running tests.
    build_docker_image(target, flavor)

    # Clear the container if it already exists - we want to start fresh when testing.
    if docker_container_exists(target, flavor):
        delete_docker_container(target, flavor)

    # Start the container in detached mode.
    container_name = format_docker_container_name(target, flavor)
    image_name = format_docker_image_name(target, flavor)

    logging.info(f"Running tests for {container_name}")

    docker_process = subprocess.Popen(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-v",
            f"{Path(__file__).parent}:/home/testuser/.dotfiles:ro",
            image_name,
            "sleep",
            "infinity",
        ],
        stdout=subprocess.PIPE,
    )
    container_id = docker_process.stdout.readline().decode().strip()

    logging.info(f"Created docker container {container_name} with id {container_id}")

    # Run bootstrap.py:
    try:
        subprocess.check_output(
            [
                "docker",
                "exec",
                container_name,
                "bash",
                "-c",
                "cd /home/testuser/.dotfiles && python3 bootstrap.py -v --git-name 'Testy McTestFace' --git-email 'testy@test.com' < /dev/null",
            ],
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        logging.exception(
            f"failed to run test: {e.stdout}",
            exc_info=e,
        )
        return False
    except subprocess.TimeoutExpired as e:
        logging.error(
            "timed out waiting for bootstrap.py - it is probably waiting for stdin", e
        )
        return False
    finally:
        # Stop the container after tests have completed.
        subprocess.check_output(["docker", "stop", container_name])

    # Run post-bootstrap verification:
    try:
        subprocess.check_output(
            [
                "docker",
                "start",
                container_name,
            ]
        )
        subprocess.check_output(
            [
                "docker",
                "exec",
                container_name,
                "sh",
                "/home/testuser/.dotfiles/tests/docker/bootstrap/verify_bootstrap.sh",
            ],
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        logging.exception(
            f"post-bootstrap verification failed: {e.stdout}",
            exc_info=e,
        )
        return False
    finally:
        subprocess.check_output(["docker", "stop", container_name])

    return True


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


def run_pydotlib_tests() -> bool:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        "_pydotlib.bootstrap",
        "_pydotlib.cli",
        "_pydotlib.colors",
        "_pydotlib.git",
        "_pydotlib.xdg",
    ]

    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[""])
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"✓ Loaded tests from {module_name}")
        except Exception as e:
            print(f"✗ Failed to load {module_name}: {e}")

    print()
    print("=" * 70)
    print("Running tests")
    print("=" * 70)
    print()

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

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

    # Return exit code based on results
    return result.wasSuccessful()


def main() -> int:
    # Argument parsing.
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging)",
    )
    args_parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip Docker integration tests",
    )
    args_parser.add_argument(
        "--docker-only",
        action="store_true",
        help="Run only Docker integration tests",
    )

    args = args_parser.parse_args()

    # Set up more verbose logging if the user requested it.
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(ColoredLogFormatter())

    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    if not args.docker_only:
        # Run shell syntax tests.
        if not run_shell_syntax_tests():
            logging.fatal("shell syntax tests failed - aborting")
            return 1

        # Run unit tests.
        if not run_pydotlib_tests():
            logging.fatal("pydotlib unit tests failed - aborting")
            return 1

    # Run integration tests using Docker.
    if not args.no_docker:
        if not check_docker():
            return 1

        all_passed = True
        for flavor in DOCKER_FLAVORS:
            if not run_docker_test("bootstrap", flavor):
                all_passed = False
        if not all_passed:
            return 1

    logging.info("All tests passed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
