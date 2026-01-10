#!/usr/bin/env python3
"""
Backdoor and unauthorized access checker for Code Cobra.

Scans the codebase for suspicious patterns that might indicate:
- Hardcoded credentials
- Backdoor code
- Unauthorized network access
- Suspicious obfuscation
- Hidden execution paths
"""

import os
import re
import sys
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Finding:
    """A potential security finding."""
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


class BackdoorChecker:
    """Scans codebase for backdoor indicators."""

    # Patterns that might indicate backdoors or security issues
    PATTERNS = {
        # Hardcoded credentials
        "hardcoded_password": (
            r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            "MEDIUM",
            "Possible hardcoded password"
        ),
        "hardcoded_api_key": (
            r'(api[_-]?key|apikey|secret[_-]?key)\s*=\s*["\'][^"\']+["\']',
            "HIGH",
            "Possible hardcoded API key"
        ),
        "hardcoded_token": (
            r'(token|auth[_-]?token|bearer)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            "HIGH",
            "Possible hardcoded token"
        ),

        # Suspicious execution
        "eval_usage": (
            r'\beval\s*\(',
            "HIGH",
            "Use of eval() - potential code injection"
        ),
        "exec_usage": (
            r'\bexec\s*\(',
            "HIGH",
            "Use of exec() - potential code injection"
        ),
        "compile_usage": (
            r'\bcompile\s*\([^)]*\)\s*$',
            "MEDIUM",
            "Use of compile() - potential dynamic code"
        ),
        "import_usage": (
            r'__import__\s*\(',
            "MEDIUM",
            "Use of __import__() - potential dynamic import"
        ),

        # Network/socket
        "socket_bind": (
            r'\.bind\s*\(\s*\(["\']0\.0\.0\.0',
            "MEDIUM",
            "Binding to all interfaces"
        ),
        "reverse_shell": (
            r'(socket\.socket|subprocess).*connect.*shell|/bin/(ba)?sh',
            "CRITICAL",
            "Possible reverse shell pattern"
        ),

        # File operations
        "world_writable": (
            r'chmod.*0?777',
            "MEDIUM",
            "World-writable permissions"
        ),
        "sensitive_file_access": (
            r'/etc/(passwd|shadow|sudoers)',
            "HIGH",
            "Access to sensitive system files"
        ),

        # Obfuscation
        "base64_decode_exec": (
            r'base64.*decode.*exec|exec.*base64.*decode',
            "CRITICAL",
            "Base64 decode followed by exec"
        ),
        "hex_decode": (
            r'bytes\.fromhex|binascii\.unhexlify',
            "LOW",
            "Hex decoding (verify usage)"
        ),
        "rot13": (
            r'codecs\.(encode|decode).*rot',
            "MEDIUM",
            "ROT13 encoding (possible obfuscation)"
        ),

        # Hidden execution
        "subprocess_shell": (
            r'subprocess\.(call|run|Popen).*shell\s*=\s*True',
            "MEDIUM",
            "Shell execution via subprocess"
        ),
        "os_system": (
            r'\bos\.system\s*\(',
            "MEDIUM",
            "Use of os.system()"
        ),
        "os_popen": (
            r'\bos\.popen\s*\(',
            "MEDIUM",
            "Use of os.popen()"
        ),

        # Environment manipulation
        "env_modification": (
            r'os\.environ\[["\'][^"\']+["\']\]\s*=',
            "LOW",
            "Environment variable modification"
        ),

        # Pickle (insecure deserialization)
        "pickle_load": (
            r'pickle\.(load|loads)\s*\(',
            "HIGH",
            "Pickle deserialization (insecure)"
        ),

        # Network requests to suspicious destinations
        "ip_address_literal": (
            r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
            "MEDIUM",
            "Direct IP address in URL"
        ),

        # Debug/development code left in
        "debug_true": (
            r'debug\s*=\s*True',
            "LOW",
            "Debug mode enabled"
        ),
        "todo_security": (
            r'#\s*TODO.*security|#\s*FIXME.*security',
            "LOW",
            "Security-related TODO/FIXME"
        ),
    }

    # Files/directories to skip
    SKIP_DIRS = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules'}
    SKIP_FILES = {'.pyc', '.pyo', '.so', '.dll', '.exe'}

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.findings: List[Finding] = []

    def scan(self) -> List[Finding]:
        """Scan the codebase for suspicious patterns."""
        self.findings = []

        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for filename in files:
                # Skip binary files
                if any(filename.endswith(ext) for ext in self.SKIP_FILES):
                    continue

                # Only scan Python files and scripts
                if not (filename.endswith('.py') or filename.endswith('.sh')):
                    continue

                file_path = os.path.join(root, filename)
                self._scan_file(file_path)

        return self.findings

    def _scan_file(self, file_path: str) -> None:
        """Scan a single file for suspicious patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return

        for line_num, line in enumerate(lines, 1):
            for pattern_name, (pattern, severity, desc) in self.PATTERNS.items():
                if re.search(pattern, line, re.IGNORECASE):
                    # Filter out false positives in test files and comments
                    if self._is_false_positive(file_path, line, pattern_name):
                        continue

                    self.findings.append(Finding(
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip()[:100],
                        pattern_name=f"{pattern_name}: {desc}",
                        severity=severity
                    ))

    def _is_false_positive(self, file_path: str, line: str, pattern_name: str) -> bool:
        """Check if a finding is likely a false positive."""
        # Test files are expected to contain attack patterns
        if 'test_' in file_path or '_test.py' in file_path:
            return True

        # This scanner itself contains patterns
        if 'backdoor_check.py' in file_path:
            return True

        # Comments explaining security measures
        if line.strip().startswith('#') and pattern_name not in ['todo_security']:
            return True

        # Documentation strings
        if '"""' in line or "'''" in line:
            return True

        return False

    def print_report(self) -> int:
        """Print findings report and return exit code."""
        if not self.findings:
            print("=" * 60)
            print("BACKDOOR CHECK REPORT")
            print("=" * 60)
            print("\nNo suspicious patterns found.")
            print("\nStatus: PASSED")
            return 0

        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        self.findings.sort(key=lambda f: severity_order.get(f.severity, 4))

        print("=" * 60)
        print("BACKDOOR CHECK REPORT")
        print("=" * 60)
        print(f"\nTotal findings: {len(self.findings)}")

        # Count by severity
        counts = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        print("\nBy severity:")
        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if sev in counts:
                print(f"  {sev}: {counts[sev]}")

        print("\n" + "-" * 60)
        print("FINDINGS:")
        print("-" * 60)

        for finding in self.findings:
            print(f"\n[{finding.severity}] {finding.pattern_name}")
            print(f"  File: {finding.file_path}:{finding.line_number}")
            print(f"  Line: {finding.line_content}")

        print("\n" + "=" * 60)

        # Fail on CRITICAL or HIGH findings
        if counts.get('CRITICAL', 0) > 0 or counts.get('HIGH', 0) > 0:
            print("Status: FAILED - Critical/High severity findings require review")
            return 1
        else:
            print("Status: PASSED (with warnings)")
            return 0


def main():
    """Run the backdoor checker."""
    # Default to current directory or first argument
    root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    print(f"Scanning: {root_path}")
    print()

    checker = BackdoorChecker(root_path)
    findings = checker.scan()
    exit_code = checker.print_report()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
