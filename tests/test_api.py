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
          "Village : Nigoha    Tehsil : Mohanlalganj",
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
    assert (f["village"], f["tehsil"], f["district"], f["state"]) == ("Nigoha", "Mohanlalganj", "Lucknow", "Uttar Pradesh")

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
    actions = {a["action"] for a in client.get("/api/admin/audit", headers=admin).json()["items"]}
    assert {"document.uploaded", "document.processed", "document.verified", "auth.login"} <= actions

    # integrations
    recs = client.get("/api/integration/lrms/records", headers=op).json()["records"]
    rec = next(x for x in recs if x["provenance"]["source_document_id"] == doc["id"])
    assert rec["account"]["owners"][0]["name"] == "Ram Prasad Sharma"
    push = client.post(f"/api/integration/lrms/push/{rec['record_id']}", headers=ver).json()
    assert push["mock"] is True and push["lrms_ref"].startswith("LRMS-UP-")
    gis = client.get("/api/integration/gis/parcels", headers=op).json()
    assert gis["type"] == "FeatureCollection" and gis["features"]
    assert client.get("/api/integration/dilrmp/progress", headers=op).json()["states"]
