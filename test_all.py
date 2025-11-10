#!/usr/bin/env python3
"""
This script performs testing for the dotfiles repository.
"""

# TODO: Run unit tests for python scripts in bin/
# TODO: Run integration tests after I figure out how to write them using Docker.

import sys
import unittest
from pathlib import Path


def run_pydotlib_tests():
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
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_pydotlib_tests())