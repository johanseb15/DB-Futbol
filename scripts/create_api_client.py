"""Create API clients for premium endpoints.

Usage:
  python scripts/create_api_client.py --name "Editorial Team" --plan pro --rate-limit 300
"""
from __future__ import annotations

import argparse
import hashlib
import secrets
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.models import APIClient
from db.session import get_sync_session


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create API client")
    parser.add_argument("--name", required=True, help="Client name")
    parser.add_argument("--plan", default="free", help="Plan name, e.g. free/pro/enterprise")
    parser.add_argument("--rate-limit", type=int, default=120, help="Requests per minute")
    args = parser.parse_args()

    raw_key = f"fi_{secrets.token_urlsafe(24)}"
    key_hash = hash_key(raw_key)

    with get_sync_session() as session:
        exists = session.execute(select(APIClient).where(APIClient.key_hash == key_hash)).scalars().first()
        if exists:
            raise RuntimeError("Unexpected key hash collision. Retry.")

        client = APIClient(
            name=args.name,
            plan=args.plan,
            key_hash=key_hash,
            rate_limit_per_minute=args.rate_limit,
            is_active=True,
        )
        session.add(client)
        session.flush()
        print("API client created")
        print(f"id={client.id}")
        print(f"name={client.name}")
        print(f"plan={client.plan}")
        print(f"rate_limit_per_minute={client.rate_limit_per_minute}")
        print(f"api_key={raw_key}")
        print("Store the api_key securely now. It cannot be recovered later.")


if __name__ == "__main__":
    main()

