"""Uploading a real document with typed ground truth: the comparison logic, and the
endpoint's file handling, role gate and persistence into data/real/ - the same shape
eval/evaluate.py --split real expects (data/real/README.md)."""
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.routes import admin

VALID_PNG = cv2.imencode(".png", np.zeros((20, 20, 3), np.uint8))[1].tobytes()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client, user, pw):
    r = client.post("/api/auth/login", data={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_compare_to_ground_truth_matches_eval_evaluates_own_rule():
    extraction = {"fields": {
        "owner_name": {"value": "Ram Prasad Sharma", "confidence": 0.9},
        "khata_number": {"value": "00245", "confidence": 0.95},
        "plot_area": {"value": "0.412 hectare", "confidence": 0.8, "normalized": {"value": 0.412, "unit": "hectare"}},
        "village": {"value": "Wrong Village", "confidence": 0.7},
    }}
    gt = {"owner_name": "ram prasad sharma",  # case differs - still a match via label_key
          "khata_number": "00245",
          "plot_area": {"value": 0.412, "unit": "hectare"},
          "village": "Rampur",
          "district": "Lucknow"}  # not extracted at all -> None, not correct

    out = {c["field"]: c for c in admin._compare_to_ground_truth(extraction, gt)}
    assert out["owner_name"]["correct"] is True
    assert out["khata_number"]["correct"] is True
    assert out["plot_area"]["correct"] is True
    assert out["village"]["correct"] is False and out["village"]["extracted"] == "Wrong Village"
    assert out["district"]["correct"] is False and out["district"]["extracted"] is None


def test_only_admin_can_add_a_real_sample(client):
    ver = _login(client, "verifier", "verify@123")
    r = client.post("/api/admin/real-samples", headers=ver,
                    files={"file": ("x.png", VALID_PNG, "image/png")},
                    data={"ground_truth": json.dumps({"fields": {"owner_name": "X"}})})
    assert r.status_code == 403


def test_add_real_sample_persists_and_reports_accuracy(client, monkeypatch, tmp_path):
    admin_hdr = _login(client, "admin", "admin@123")
    monkeypatch.setattr(admin, "REAL_DIR", tmp_path)
    monkeypatch.setattr(admin, "run_ocr", lambda data, filename: {"pages": []})
    monkeypatch.setattr(admin, "extract", lambda ocr: {
        "document_type": "khatauni", "overall_confidence": 0.88, "route": "needs_review",
        "fields": {"owner_name": {"value": "Ram Prasad Sharma", "confidence": 0.9},
                  "khata_number": {"value": "00111", "confidence": 0.9}},
    })
    gt = {"fields": {"owner_name": "Ram Prasad Sharma", "khata_number": "00245"}}
    r = client.post("/api/admin/real-samples", headers=admin_hdr,
                    files={"file": ("sample.png", VALID_PNG, "image/png")},
                    data={"ground_truth": json.dumps(gt)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["document_type"] == "khatauni"
    by_field = {c["field"]: c["correct"] for c in body["fields"]}
    assert by_field == {"owner_name": True, "khata_number": False}
    assert body["field_accuracy"] == 0.5

    # persisted next to each other, same stem, in data/real/README.md's format
    saved = list(tmp_path.glob(f"{body['sample_id']}.*"))
    assert {p.suffix for p in saved} == {".png", ".json"}
    saved_json = json.loads((tmp_path / f"{body['sample_id']}.json").read_text(encoding="utf-8"))
    assert saved_json == gt

    listed = client.get("/api/admin/real-samples", headers=admin_hdr).json()
    assert any(s["sample_id"] == body["sample_id"] and s["has_file"] for s in listed)

    trail = client.get("/api/admin/audit", headers=admin_hdr, params={"action": "real_sample.added"}).json()
    assert any(e["details"]["sample_id"] == body["sample_id"] for e in trail["items"])


def test_add_real_sample_rejects_bad_input(client, monkeypatch, tmp_path):
    admin_hdr = _login(client, "admin", "admin@123")
    monkeypatch.setattr(admin, "REAL_DIR", tmp_path)
    assert client.post("/api/admin/real-samples", headers=admin_hdr,
                       files={"file": ("x.txt", b"hi", "text/plain")},
                       data={"ground_truth": "{}"}).status_code == 415
    assert client.post("/api/admin/real-samples", headers=admin_hdr,
                       files={"file": ("x.png", b"", "image/png")},
                       data={"ground_truth": "{}"}).status_code == 400
    assert client.post("/api/admin/real-samples", headers=admin_hdr,
                       files={"file": ("x.png", b"not really a png", "image/png")},
                       data={"ground_truth": "{}"}).status_code == 415
    # a valid image but broken JSON, and a valid image with no fields, are both refused too
    assert client.post("/api/admin/real-samples", headers=admin_hdr,
                       files={"file": ("x.png", VALID_PNG, "image/png")},
                       data={"ground_truth": "not json"}).status_code == 400
    assert client.post("/api/admin/real-samples", headers=admin_hdr,
                       files={"file": ("x.png", VALID_PNG, "image/png")},
                       data={"ground_truth": json.dumps({"fields": {}})}).status_code == 400
