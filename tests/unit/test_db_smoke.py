import os
import uuid
import sqlalchemy as sa

from bharatrag.core.config import get_settings
from bharatrag.db.models.collection import CollectionModel
from bharatrag.db.session import engine

def _db_enabled() -> bool:
    # Allows you to disable DB tests in CI or locally if needed
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_db_schema_and_insert_smoke():
    if not _db_enabled():
        return

    settings = get_settings()
    assert "postgresql" in settings.database_url.lower()

    with engine.begin() as conn:
        inspector = sa.inspect(conn)
        tables = set(inspector.get_table_names())

        # These must exist if alembic upgrade head has been run
        assert "collections" in tables
        assert "documents" in tables
        assert "chunks" in tables
        assert "ingestion_jobs" in tables
        assert "alembic_version" in tables

        # Insert a collection row
        new_id = uuid.uuid4()
        name = f"test-{new_id}"

        conn.execute(sa.insert(CollectionModel).values(id=new_id, name=name))

        row = conn.execute(
            sa.select(CollectionModel).where(CollectionModel.id == new_id)
        ).first()
        
        print(row)

        assert row is not None
        assert row[0] == new_id
        assert row[1] == name
