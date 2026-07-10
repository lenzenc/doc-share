"""CLI entry point: verify the audit event hash chain is intact.

Usage: uv run python -m app.audit_verify   (or `make audit-verify`)

Exits 0 and prints "OK" if the chain verifies; exits 1 and prints where the
chain broke otherwise (tampering, deletion, or reordering of a row).
"""

import sys

from app.audit import verify_chain
from app.database import SessionLocal


def main() -> int:
    db = SessionLocal()
    try:
        result = verify_chain(db)
    finally:
        db.close()

    if result.ok:
        print(f"OK — {result.count} events, chain intact")
        return 0

    print(
        f"TAMPER DETECTED at seq {result.first_bad_seq}: {result.reason} "
        f"({result.count} events examined)"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
