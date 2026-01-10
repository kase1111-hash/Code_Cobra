#!/usr/bin/env python3
"""
Regression Test Suite for Autonomous Coding Ensemble System.

Runs all test suites and generates a test report.
Use this before releases to ensure no regressions.
"""

import json
import os
import sys
import unittest
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RegressionTestResult(unittest.TestResult):
    """Custom test result that tracks detailed test outcomes."""

    def __init__(self):
        super().__init__()
        self.test_results: List[Dict[str, Any]] = []
        self.start_time: datetime = datetime.now()

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._test_start = datetime.now()

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self._record_result(test, "passed")

    def addError(self, test: unittest.TestCase, err) -> None:
        super().addError(test, err)
        self._record_result(test, "error", err)

    def addFailure(self, test: unittest.TestCase, err) -> None:
        super().addFailure(test, err)
        self._record_result(test, "failed", err)

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._record_result(test, "skipped", reason=reason)

    def _record_result(
        self,
        test: unittest.TestCase,
        status: str,
        err=None,
        reason: str = None
    ) -> None:
        duration = (datetime.now() - self._test_start).total_seconds()
        result = {
            "name": str(test),
            "class": test.__class__.__name__,
            "method": test._testMethodName,
            "status": status,
            "duration_seconds": duration,
        }
        if err:
            result["error"] = str(err[1]) if len(err) > 1 else str(err)
        if reason:
            result["skip_reason"] = reason
        self.test_results.append(result)

    def get_summary(self) -> Dict[str, Any]:
        """Get test run summary."""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "timestamp": self.start_time.isoformat(),
            "total_tests": self.testsRun,
            "passed": len([r for r in self.test_results if r["status"] == "passed"]),
            "failed": len(self.failures),
            "errors": len(self.errors),
            "skipped": len(self.skipped),
            "total_duration_seconds": total_duration,
            "success": self.wasSuccessful(),
        }


def discover_tests() -> unittest.TestSuite:
    """Discover all tests in the tests directory."""
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern="test_*.py")
    return suite


def run_regression_tests(
    verbose: bool = True,
    save_report: bool = True,
    report_file: str = "regression_report.json"
) -> bool:
    """
    Run all regression tests.

    Args:
        verbose: Print verbose output
        save_report: Save JSON report
        report_file: Report file path

    Returns:
        True if all tests passed
    """
    print("=" * 70)
    print("CODE COBRA REGRESSION TEST SUITE")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Discover and run tests
    suite = discover_tests()
    result = RegressionTestResult()

    # Run tests with our custom result
    if verbose:
        print("Running tests...\n")

    suite.run(result)

    # Print test details
    if verbose:
        for test_result in result.test_results:
            status_symbol = {
                "passed": "✓",
                "failed": "✗",
                "error": "E",
                "skipped": "S"
            }.get(test_result["status"], "?")
            print(f"  {status_symbol} {test_result['name']} ({test_result['duration_seconds']:.3f}s)")

    # Get summary
    summary = result.get_summary()

    # Print summary
    print()
    print("=" * 70)
    print("REGRESSION TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests:  {summary['total_tests']}")
    print(f"Passed:       {summary['passed']}")
    print(f"Failed:       {summary['failed']}")
    print(f"Errors:       {summary['errors']}")
    print(f"Skipped:      {summary['skipped']}")
    print(f"Duration:     {summary['total_duration_seconds']:.2f}s")
    print(f"Success:      {'YES' if summary['success'] else 'NO'}")
    print("=" * 70)

    # Save report
    if save_report:
        report = {
            "summary": summary,
            "tests": result.test_results,
        }
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            report_file
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved: {report_path}")

    return summary["success"]


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Code Cobra regression tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-report", action="store_true", help="Don't save JSON report")
    parser.add_argument("--report", default="regression_report.json", help="Report file")

    args = parser.parse_args()

    success = run_regression_tests(
        verbose=args.verbose,
        save_report=not args.no_report,
        report_file=args.report
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
