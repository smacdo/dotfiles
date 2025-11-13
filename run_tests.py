#!/usr/bin/env python3
"""
This script performs testing for the dotfiles repository.

TODO: Run unit tests for python scripts in bin/
TODO: Run integration tests after I figure out how to write them using Docker.
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
                "-it",
                container_name,
                "bash",
                "-c",
                "cd /home/testuser/.dotfiles && python3 bootstrap.py -v --git-name 'Testy McTestFace' --git-email 'testy@test.com' < /dev/null",
            ],
            timeout=10,
        )

        # TODO: Verify bootstrap.py ran OK.
        # TODO: Verify bash starts without error.
        # TODO: Verify zsh starts without error.
        # TODO: Verify vim starts without error.
        # TODO: Verify neovim starts without error.
        # TODO: Verify tmux starts without error.
        return True
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


def run_pydotlib_tests() -> bool:
    # TODO: Search for them without having to hardcode the names.
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

    args = args_parser.parse_args()

    # Set up more verbose logging if the user requested it.
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(ColoredLogFormatter())

    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Run unit tests.
    if not run_pydotlib_tests():
        logging.fatal("pydotlib unit tests failed - aborting")
        return 1

    # Run integration tests using Docker.
    if not check_docker():
        return 1

    run_docker_test("bootstrap", "debian")

    logging.info("All tests passed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())