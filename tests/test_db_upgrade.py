"""An older database (created before a model gained a column) must still start."""
from sqlalchemy import create_engine, inspect, text

from backend.api import models  # noqa: F401  (registers all tables on Base)
from backend.api.db import Base, upgrade_schema


def test_missing_nullable_columns_are_added_once(tmp_path):
    eng = create_engine(f"sqlite:///{(tmp_path / 'old.sqlite3').as_posix()}")
    Base.metadata.create_all(eng)
    with eng.begin() as conn:  # simulate a database from before owners/parcels existed
        conn.execute(text("ALTER TABLE documents DROP COLUMN owners"))
        conn.execute(text("ALTER TABLE land_records DROP COLUMN parcels"))
    assert "owners" not in {c["name"] for c in inspect(eng).get_columns("documents")}

    assert sorted(upgrade_schema(eng)) == ["documents.owners", "land_records.parcels"]
    assert "owners" in {c["name"] for c in inspect(eng).get_columns("documents")}
    with eng.connect() as conn:
        conn.execute(text("SELECT owners, parcels FROM documents")).fetchall()
    assert upgrade_schema(eng) == []  # idempotent
