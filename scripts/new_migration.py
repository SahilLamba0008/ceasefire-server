#!/usr/bin/env python3
# Usage: python scripts/new_migration.py (run from repo root)

import os
import re
import sys

MIGRATION_DIR = os.path.join("services", "api", "src", "main", "resources", "db", "migration")

def get_next_version():
    if not os.path.exists(MIGRATION_DIR):
        print(f"Error: migration directory not found: {MIGRATION_DIR}")
        sys.exit(1)

    versions = []
    for f in os.listdir(MIGRATION_DIR):
        match = re.match(r"V(\d+)__", f)
        if match:
            versions.append(int(match.group(1)))

    return max(versions, default=0) + 1

def main():
    next_version = get_next_version()

    print(f"Next version : V{next_version}")
    print("Description  : snake_case only (e.g. add_users_table)")

    desc = input("Migration description: ").strip()

    if not desc:
        print("Error: description cannot be empty")
        sys.exit(1)

    if not re.match(r"^[a-zA-Z0-9_]+$", desc):
        print("Error: description must be snake_case (letters, numbers, underscores only — no spaces or hyphens)")
        sys.exit(1)

    filename = f"V{next_version}__{desc}.sql"
    filepath = os.path.join(MIGRATION_DIR, filename)

    open(filepath, "w").close()
    print(f"Created: {filepath}")

if __name__ == "__main__":
    main()
