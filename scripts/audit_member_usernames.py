#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.db.runtime_migrations import audit_member_username_state  # noqa: E402
from app.db.session import engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="optional path to write the audit JSON")
    parser.add_argument(
        "--require-global-unique",
        action="store_true",
        help="fail if members.username is not protected by a global unique constraint or index",
    )
    args = parser.parse_args()

    audit = audit_member_username_state(engine)
    issues: list[str] = []
    if audit["duplicate_usernames"]:
        issues.append("duplicate_usernames")
    if args.require_global_unique and not audit["has_global_unique_username_constraint"]:
        issues.append("missing_global_unique_username_constraint")

    report = {
        "database_backend": engine.dialect.name,
        "passed": not issues,
        "issues": issues,
        **audit,
    }

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
