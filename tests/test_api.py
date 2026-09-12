"""End-to-end API test: upload -> process -> review -> record -> integrations.

Uses a born-digital PDF, which the pipeline reads from its text layer, so the whole
flow runs in seconds without loading the OCR model.
"""
import time

import fitz
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

RECORD = ["RECORD OF RIGHTS - EXTRACT (Khatauni)",
          "Village : Nigohan    Tehsil : Mohanlalganj",
          "District : Lucknow    State : Uttar Pradesh",
          "Name of Landowner : Ram Prasad Sharma",
          "Father's Name : Mohan Lal Sharma",
          "Khata No. : 00245",
          "Khasra No. : 123/2",
          "Area : 0.412 Hectare",
          "Land Classification : Agricultural (Irrigated)",
          "Mutation No. : 4521",
          "Mutation Date : 12/03/2019"]


def _pdf(lines: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for i, text in enumerate(lines):
        page.insert_text((50, 80 + 28 * i), text, fontsize=12)
    return doc.tobytes()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, user, pw):
    r = client.post("/api/auth/login", data={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _wait(client, doc_id, headers, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = client.get(f"/api/documents/{doc_id}", headers=headers).json()
        if d["status"] not in ("queued", "processing"):
            return d
        time.sleep(0.2)
    raise AssertionError("document was not processed in time")


def test_full_flow(client):
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")
    admin = _login(client, "admin", "admin@123")
    assert client.post("/api/auth/login", data={"username": "admin", "password": "nope"}).status_code == 401
    assert client.get("/api/documents").status_code == 401

    pdf = _pdf(RECORD)
    r = client.post("/api/documents", headers=op, files={"file": ("khatauni.pdf", pdf, "application/pdf")})
    assert r.status_code == 202, r.text
    doc = _wait(client, r.json()["id"], op)
    assert doc["status"] in ("auto_accepted", "needs_review")
    assert doc["pages"][0]["preprocess"]["steps"] == ["pdf_text_layer"]
    assert doc["pages"][0]["quality"]["verdict"] == "good"
    f = {x["name"]: x["value"] for x in doc["fields"]}
    assert f["owner_name"] == "Ram Prasad Sharma" and f["khata_number"] == "00245" and f["khasra_number"] == "123/2"
    assert (f["village"], f["tehsil"], f["district"], f["state"]) == ("Nigohan", "Mohanlalganj", "Lucknow", "Uttar Pradesh")

    # the review queue says how many fields each waiting document needs checked
    queue = client.get("/api/review/queue", headers=ver).json()
    assert all(isinstance(q["flagged"], int) and q["flagged"] >= 0 for q in queue)
    assert (doc["status"] == "needs_review") == any(q["id"] == doc["id"] for q in queue)

    listing = client.get("/api/documents", headers=op).json()
    assert sum(listing["counts"].values()) == listing["total"] >= 1 and doc["status"] in listing["counts"]
    assert all(isinstance(x["flagged"], int) for x in listing["items"])  # fields left to check, per document
    filtered = client.get("/api/documents", headers=op, params={"status": "failed"}).json()
    assert filtered["total"] == 0 and filtered["counts"] == listing["counts"]  # counts ignore the status filter

    # same file again is refused; wrong type is refused
    assert client.post("/api/documents", headers=op, files={"file": ("again.pdf", pdf, "application/pdf")}).status_code == 409
    assert client.post("/api/documents", headers=op, files={"file": ("a.txt", b"hi", "text/plain")}).status_code == 415

    # roles
    assert client.post(f"/api/documents/{doc['id']}/verify", headers=op, json={"decision": "approve"}).status_code == 403
    assert client.get("/api/admin/users", headers=ver).status_code == 403

    # verifier corrects a field and approves -> record + learning + audit
    r = client.post(f"/api/documents/{doc['id']}/verify", headers=ver,
                    json={"decision": "approve", "fields": {"plot_area": {"action": "correct", "value": "0.5 hectare"}}})
    assert r.status_code == 200 and r.json()["status"] == "verified"
    d = client.get(f"/api/documents/{doc['id']}", headers=ver).json()
    area = next(x for x in d["fields"] if x["name"] == "plot_area")
    assert area["status"] == "corrected" and area["normalized"]["hectares"] == 0.5
    assert d["record_id"] is not None

    stats = client.get("/api/admin/stats", headers=admin).json()
    assert stats["totals"]["land_records"] >= 1 and stats["learning"]["corrections"] >= 1
    people = client.get("/api/admin/users", headers=admin).json()
    assert {u["username"] for u in people} >= {"admin", "verifier", "operator"}
    assert next(u for u in people if u["username"] == "verifier")["last_login"]  # signed in above
    mine = client.get("/api/admin/audit", headers=admin, params={"username": "verifier"}).json()
    assert mine["items"] and {a["user"] for a in mine["items"]} == {"verifier"}  # audit filtered by person
    actions = {a["action"] for a in client.get("/api/admin/audit", headers=admin).json()["items"]}
    assert {"document.uploaded", "document.processed", "document.verified", "auth.login"} <= actions

    # integrations
    recs = client.get("/api/integration/lrms/records", headers=ver).json()["records"]  # verifier and above
    rec = next(x for x in recs if x["provenance"]["source_document_id"] == doc["id"])
    assert rec["account"]["owners"][0]["name"] == "Ram Prasad Sharma"
    push = client.post(f"/api/integration/lrms/push/{rec['record_id']}", headers=ver).json()
    assert push["mock"] is True and push["lrms_ref"].startswith("LRMS-UP-")
    gis = client.get("/api/integration/gis/parcels", headers=ver).json()
    assert gis["type"] == "FeatureCollection" and gis["features"]
    assert client.get("/api/integration/dilrmp/progress", headers=ver).json()["states"]


def test_verified_extract_detects_tampering(client):
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")
    lines = [ln.replace("00245", "00777").replace("123/2", "456/1") for ln in RECORD]  # a different record
    r = client.post("/api/documents", headers=op, files={"file": ("second.pdf", _pdf(lines), "application/pdf")})
    doc = _wait(client, r.json()["id"], op)
    client.post(f"/api/documents/{doc['id']}/verify", headers=ver, json={"decision": "approve"})
    rec_id = client.get(f"/api/documents/{doc['id']}", headers=ver).json()["record_id"]

    ex = client.get(f"/api/records/{rec_id}/extract", headers=ver).json()
    assert ex["record"]["khata_number"] == "00777" and len(ex["fingerprint"]) == 64
    assert ex["verify_path"] == f"/verify/{rec_id}?fp={ex['fingerprint']}"

    # the public check needs no login
    ok = client.get(f"/api/public/records/{rec_id}/verify", params={"fp": ex["fingerprint"]}).json()
    assert ok["valid"] and ok["khata_number"] == "00777" and ok["owners"] == ["Ram Prasad Sharma"]
    assert not client.get(f"/api/public/records/{rec_id}/verify", params={"fp": "0" * 64}).json()["valid"]

    # someone changes the record after the extract was printed -> the old extract no longer verifies
    from backend.api.db import SessionLocal
    from backend.api.models import LandRecord
    with SessionLocal() as db:
        db.get(LandRecord, rec_id).khasra_number = "999/9"
        db.commit()
    changed = client.get(f"/api/public/records/{rec_id}/verify", params={"fp": ex["fingerprint"]}).json()
    assert changed["valid"] is False and "changed" in changed["reason"]
    assert client.get(f"/api/records/{rec_id}/extract").status_code == 401  # issuing needs a login


def test_a_correction_is_carried_over_to_the_next_document(client):
    """The learning loop, end to end. The demo says "the same misreading is fixed automatically
    next time", so prove it: correct one owner's name, then send in another document that was
    misread the same way and expect the correction to have been applied without a person."""
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")

    # "rn" read as "m" is the classic scanning confusion
    misread = [l.replace("Ram Prasad Sharma", "Ram Prasad Sharrna").replace("00245", "00811").replace("123/2", "451/7")
               for l in RECORD]
    first = _wait(client, client.post("/api/documents", headers=op,
                                      files={"file": ("learn-1.pdf", _pdf(misread), "application/pdf")}).json()["id"], op)
    assert {x["name"]: x["value"] for x in first["fields"]}["owner_name"] == "Ram Prasad Sharrna"

    r = client.post(f"/api/documents/{first['id']}/verify", headers=ver,
                    json={"decision": "approve",
                          "fields": {"owner_name": {"action": "correct", "value": "Ram Prasad Sharma"}}})
    assert r.status_code == 200, r.text

    # the same misreading, on a different khata so it is not held as a duplicate record
    again = [l.replace("00811", "00907").replace("451/7", "12/3") for l in misread]
    second = _wait(client, client.post("/api/documents", headers=op,
                                       files={"file": ("learn-2.pdf", _pdf(again), "application/pdf")}).json()["id"], op)
    owner = next(x for x in second["fields"] if x["name"] == "owner_name")
    assert owner["value"] == "Ram Prasad Sharma", f"correction not carried over: {owner['value']!r}"
    assert owner["source"] == "learned"
    assert owner["raw_value"] == "Ram Prasad Sharrna"  # what the page actually said is still on the record


def test_a_page_that_is_not_a_land_record_invents_nothing(client):
    """Somebody will upload the wrong page. It must come back empty and honest: no fields
    guessed, no record created, and a human asked to look.

    This one goes through real OCR (an invoice has no land-record words, so the PDF text
    layer is refused), which is what a photographed wrong page would do. That costs about
    30 seconds of model load on a cold run - the only test here that does.
    """
    op = _login(client, "operator", "upload@123")
    invoice = ["INVOICE", "Acme Traders Pvt Ltd", "GSTIN: 07AABCU9603R1ZM",
               "Steel pipes      12    450.00   5400.00", "Cement bags      30    380.00  11400.00",
               "Total due: Rs 16,800.00", "Payment terms: 30 days", "Thank you for your business"]
    doc = _wait(client, client.post("/api/documents", headers=op,
                                    files={"file": ("invoice.pdf", _pdf(invoice), "application/pdf")}).json()["id"],
                op, timeout=180)
    assert doc["status"] == "needs_review"
    assert doc["fields"] == []          # nothing was recognised, so nothing is offered as fact
    assert doc["record_id"] is None     # and nothing reached the register
    assert doc["overall_confidence"] in (None, 0.0)


def test_an_operator_cannot_read_the_register_or_other_peoples_trails(client):
    """Least privilege. An operator uploads pages and sees their own uploads; they do not get
    every district's owner names through the integration APIs, GraphQL, or the audit trail."""
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")

    for path in ("/api/integration/lrms/records", "/api/integration/gis/parcels",
                 "/api/integration/dilrmp/progress"):
        assert client.get(path, headers=op).status_code == 403, path
        assert client.get(path, headers=ver).status_code == 200, path

    q = {"query": "{ landRecords { recordId khataNumber } }"}
    assert client.post("/api/graphql", headers=op, json=q).status_code == 403
    assert client.post("/api/graphql", headers=ver, json=q).status_code == 200

    # the audit trail of somebody else's document is not browsable by id
    admin = _login(client, "admin", "admin@123")
    others = client.get("/api/documents", headers=admin).json()["items"]
    mine = {d["id"] for d in client.get("/api/documents", headers=op).json()["items"]}
    not_mine = next((d["id"] for d in others if d["id"] not in mine), None)
    if not_mine is not None:
        r = client.get("/api/admin/audit", headers=op, params={"entity_type": "document", "entity_id": not_mine})
        assert r.status_code == 403, r.text
    own = next(iter(mine))
    assert client.get("/api/admin/audit", headers=op,
                      params={"entity_type": "document", "entity_id": own}).status_code == 200


def test_an_upload_that_would_blow_up_memory_is_refused(client):
    """A small file can decode to an enormous image. OCR runs in one shared worker thread, so
    that would take every other document down with it."""
    import io as _io

    from PIL import Image as _Image

    op = _login(client, "operator", "upload@123")
    buf = _io.BytesIO()
    _Image.new("L", (9000, 9000), 255).save(buf, format="PNG", optimize=True)  # ~90 KB, 81 megapixels
    bomb = buf.getvalue()
    assert len(bomb) < 1_000_000
    r = client.post("/api/documents", headers=op, files={"file": ("huge.png", bomb, "image/png")})
    assert r.status_code == 413 and "megapixel" in r.json()["detail"]

    # and a file that is not the thing its name claims
    r = client.post("/api/documents", headers=op, files={"file": ("fake.jpg", b"I am text", "image/jpeg")})
    assert r.status_code == 415
    r = client.post("/api/documents", headers=op, files={"file": ("fake.pdf", b"I am text", "application/pdf")})
    assert r.status_code == 415


def test_only_one_live_document_per_file(client):
    """The duplicate check is a lookup followed by an insert, so the database has to be the one
    that decides - otherwise two uploads landing together both get through."""
    from sqlalchemy import text as _text

    from backend.api.db import engine

    with engine.connect() as conn:
        names = {r[1] for r in conn.execute(_text("PRAGMA index_list('documents')"))}
    assert "ux_documents_sha256_active" in names, "the unique index was not created at startup"


def test_verifying_a_document_twice_is_refused_politely(client):
    """The second verifier to press Approve must get a clear 409, never a 500."""
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")
    lines = [l.replace("00245", "00733").replace("123/2", "88/1") for l in RECORD]
    doc = _wait(client, client.post("/api/documents", headers=op,
                                    files={"file": ("twice.pdf", _pdf(lines), "application/pdf")}).json()["id"], op)
    first = client.post(f"/api/documents/{doc['id']}/verify", headers=ver, json={"decision": "approve"})
    assert first.status_code == 200, first.text
    again = client.post(f"/api/documents/{doc['id']}/verify", headers=ver, json={"decision": "approve"})
    assert again.status_code == 409 and "cannot be verified" in again.json()["detail"]


def test_an_admin_can_check_the_audit_trail_has_not_been_rewritten(client):
    admin = _login(client, "admin", "admin@123")
    ver = _login(client, "verifier", "verify@123")
    r = client.get("/api/admin/audit/verify", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["checked"] > 0, body
    assert client.get("/api/admin/audit/verify", headers=ver).status_code == 403


def test_issuing_an_extract_is_a_verifiers_job(client):
    """An extract carries the owner's name and the fingerprint a bank checks. The public
    check that reads that fingerprint back still needs no login at all."""
    op = _login(client, "operator", "upload@123")
    ver = _login(client, "verifier", "verify@123")
    records = client.get("/api/integration/lrms/records", headers=ver).json()["records"]
    assert records, "no verified record to issue an extract for"
    rid = records[0]["record_id"]
    assert client.get(f"/api/records/{rid}/extract", headers=op).status_code == 403
    r = client.get(f"/api/records/{rid}/extract", headers=ver)
    assert r.status_code == 200
    fp = r.json()["fingerprint"]
    public = client.get(f"/api/public/records/{rid}/verify", params={"fp": fp})   # no headers at all
    assert public.status_code == 200 and public.json()["valid"] is True
    tampered = client.get(f"/api/public/records/{rid}/verify", params={"fp": "0" * len(fp)})
    assert tampered.status_code == 200 and tampered.json()["valid"] is False
