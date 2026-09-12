"""The audit trail is only worth something if a quiet edit shows up.

These run against their own throwaway database: the tests deliberately damage the trail, and
that must not leak into any other test.
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.api import audit
from backend.api.db import Base
from backend.api.models import AuditLog


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'audit.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        for i in range(4):
            audit.log(session, f"test.action{i}", None, "document", i + 1, {"n": i})
        session.commit()
        yield session
    engine.dispose()


def test_an_intact_trail_verifies(db):
    result = audit.verify_chain(db)
    assert result["ok"] is True and result["checked"] == 4, result


def test_an_edited_entry_is_caught(db):
    """Change what an entry says — the sort of thing done to hide a decision."""
    row = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()[2]
    row.details = {"n": 999}          # rewritten in place, hash left alone
    db.commit()
    result = audit.verify_chain(db)
    assert result["ok"] is False and result["broken_at"] == row.id
    assert "no longer match" in result["detail"]


def test_a_deleted_entry_is_caught(db):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    db.delete(rows[1])                # remove one from the middle
    db.commit()
    result = audit.verify_chain(db)
    assert result["ok"] is False and "missing" in result["detail"]


def test_entries_written_before_the_chain_existed_are_not_called_tampering(db):
    db.add(AuditLog(username="legacy", action="old.entry"))   # no hashes at all
    db.commit()
    result = audit.verify_chain(db)
    assert result["unhashed"] == 1 and result["ok"] is True


def test_the_hash_covers_who_did_what_to_which_document(db):
    row = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()[1]
    for attr, value in (("username", "someone else"), ("action", "document.deleted"), ("entity_id", 999),
                        ("ip", "10.0.0.1")):
        before = getattr(row, attr)
        setattr(row, attr, value)
        assert audit.verify_chain(db)["ok"] is False, f"editing {attr} went unnoticed"
        setattr(row, attr, before)
    assert audit.verify_chain(db)["ok"] is True   # and putting it back makes it whole again
