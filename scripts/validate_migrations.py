#!/usr/bin/env python3
"""
Validates Flyway migration files for:
  1. Naming convention  — V{n}__{snake_case}.sql
  2. Duplicate versions — no two files share the same version number
  3. SQL security       — privilege escalation, destructive ops, hardcoded secrets, SQL injection
"""

import os
import re
import sys

MIGRATION_DIR = os.path.join("services", "api", "src", "main", "resources", "db", "migration")

VALID_NAME = re.compile(r"^V(\d+)__([a-zA-Z0-9_]+)\.sql$")

SECURITY_RULES = [
    (
        re.compile(r"\bGRANT\s+ALL\b", re.IGNORECASE),
        "ERROR",
        "GRANT ALL detected — avoid overly broad privilege grants",
    ),
    (
        re.compile(r"\bSUPERUSER\b", re.IGNORECASE),
        "ERROR",
        "SUPERUSER detected — do not grant superuser privileges in migrations",
    ),
    (
        re.compile(r"(password|secret|token|key)\s*=\s*['\"][^'\"]{3,}['\"]", re.IGNORECASE),
        "ERROR",
        "Possible hardcoded secret detected — never store credentials in migration files",
    ),
    (
        re.compile(r"\bEXECUTE\s+(.*\|\||\bformat\b.*%[^sI])", re.IGNORECASE),
        "ERROR",
        "Possible SQL injection — EXECUTE with string concatenation or unparameterized format()",
    ),
    (
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        "WARN",
        "DROP TABLE detected — ensure this is intentional and reviewed",
    ),
    (
        re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
        "WARN",
        "TRUNCATE detected — ensure this is intentional and reviewed",
    ),
]


def get_migration_files():
    if not os.path.exists(MIGRATION_DIR):
        print(f"Migration directory not found: {MIGRATION_DIR}")
        sys.exit(1)
    return [f for f in os.listdir(MIGRATION_DIR) if f.endswith(".sql")]


def check_naming(files):
    errors = []
    for f in files:
        if not VALID_NAME.match(f):
            errors.append(f"  FAIL {f} — must match V{{n}}__{{snake_case}}.sql")
    return errors


def check_duplicates(files):
    seen = {}
    errors = []
    for f in files:
        match = VALID_NAME.match(f)
        if match:
            version = int(match.group(1))
            if version in seen:
                errors.append(f"  FAIL duplicate version V{version}: '{seen[version]}' and '{f}'")
            else:
                seen[version] = f
    return errors


def check_security(files):
    errors = []
    warnings = []
    for f in files:
        filepath = os.path.join(MIGRATION_DIR, f)
        with open(filepath, "r") as fh:
            for lineno, line in enumerate(fh, 1):
                for pattern, level, message in SECURITY_RULES:
                    if pattern.search(line):
                        entry = f"  {level} {f}:{lineno} — {message}"
                        if level == "ERROR":
                            errors.append(entry)
                        else:
                            warnings.append(entry)
    return errors, warnings


def main():
    files = get_migration_files()
    failed = False

    print(f"Validating {len(files)} migration file(s) in {MIGRATION_DIR}\n")

    # Step 1 — Naming
    print("[ Naming convention ]")
    naming_errors = check_naming(files)
    if naming_errors:
        for e in naming_errors:
            print(e)
        failed = True
    else:
        print("  OK")

    # Step 2 — Duplicates
    print("\n[ Duplicate versions ]")
    duplicate_errors = check_duplicates(files)
    if duplicate_errors:
        for e in duplicate_errors:
            print(e)
        failed = True
    else:
        print("  OK")

    # Step 3 — Security
    print("\n[ SQL security scan ]")
    sec_errors, sec_warnings = check_security(files)
    if sec_warnings:
        for w in sec_warnings:
            print(w)
    if sec_errors:
        for e in sec_errors:
            print(e)
        failed = True
    if not sec_errors and not sec_warnings:
        print("  OK")

    print()
    if failed:
        print("Validation FAILED")
        sys.exit(1)
    else:
        print("Validation PASSED")


if __name__ == "__main__":
    main()
