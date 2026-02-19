import os
import uuid

import pytest
from sqlalchemy import delete

from db.models import ScrapeRaw
from db.session import get_async_session
from pipeline.runner import _store_raw_payload


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_store_raw_payload_deduplicates_latest():
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("Set RUN_DB_TESTS=1 to run integration tests against PostgreSQL.")

    entity_id = f"pytest:{uuid.uuid4()}"
    source = "pytest_source"
    payload = {"matches": [{"match": {"id": 1}}]}

    # ensure clean
    async with get_async_session() as session:
        await session.execute(delete(ScrapeRaw).where(ScrapeRaw.entity_id == entity_id))

    inserted_first = await _store_raw_payload(uuid.uuid4(), source, entity_id, payload)
    inserted_second = await _store_raw_payload(uuid.uuid4(), source, entity_id, payload)

    assert inserted_first is True
    assert inserted_second is False

