"""Upload -> scan -> pipeline persists a contract-shaped scorecard.

TestClient runs BackgroundTasks synchronously once the request returns, so by the time
we poll, the mocked pipeline has already finished.
"""

import io

from fastapi.testclient import TestClient


def _upload(client: TestClient) -> str:
    res = client.post(
        "/models",
        data={"name": "phishing-url-rf", "model_type": "sklearn", "version": "1"},
        files={"file": ("model.pkl", io.BytesIO(b"not-a-real-pickle"), "application/octet-stream")},
    )
    assert res.status_code == 201, res.text
    assert len(res.json()["checksum_sha256"]) == 64
    return res.json()["id"]


def test_rejects_unsupported_file_type(auth_client: TestClient) -> None:
    res = auth_client.post(
        "/models",
        data={"name": "bad", "model_type": "sklearn"},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res.status_code == 400


def test_scan_runs_end_to_end(auth_client: TestClient) -> None:
    model_id = _upload(auth_client)

    created = auth_client.post(
        "/scans",
        json={"model_id": model_id, "threat_model": "white_box", "attacks": ["fgsm", "pgd"]},
    )
    assert created.status_code == 202
    scan_id = created.json()["id"]
    assert created.json()["status"] == "queued"

    scan = auth_client.get(f"/scans/{scan_id}").json()
    assert scan["status"] == "done"
    assert scan["score"]["grade"] in {"A", "B", "C", "D", "F"}
    assert 0 <= scan["score"]["final_score_0_100"] <= 100
    assert {f["attack"] for f in scan["findings"]} == {"fgsm", "pgd"}
    assert scan["raw_results"]["scan_id"] == scan_id

    history = auth_client.get(f"/models/{model_id}/scans").json()
    assert len(history) == 1 and history[0]["grade"] == scan["score"]["grade"]


def test_scan_requires_auth_and_ownership(client: TestClient, auth_client: TestClient) -> None:
    model_id = _upload(auth_client)
    anon = TestClient(auth_client.app)
    assert anon.post("/scans", json={"model_id": model_id, "attacks": ["fgsm"]}).status_code == 401


def test_score_and_findings_endpoints(auth_client: TestClient) -> None:
    model_id = _upload(auth_client)
    scan_id = auth_client.post(
        "/scans", json={"model_id": model_id, "attacks": ["fgsm", "hopskipjump", "poisoning"]}
    ).json()["id"]

    score = auth_client.get(f"/scans/{scan_id}/score").json()
    assert set(score["component_scores"]) == {"evasion", "black_box", "poisoning"}

    findings = auth_client.get(f"/scans/{scan_id}/findings").json()
    order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    severities = [order[f["severity"]] for f in findings]
    assert severities == sorted(severities, reverse=True)  # ranked, most severe first


def test_failed_scan_surfaces_its_error(auth_client: TestClient, monkeypatch) -> None:
    from app.services import sandbox_client

    def boom(_job_config):
        raise RuntimeError("sandbox container exited 137")

    monkeypatch.setattr(sandbox_client, "run_scan", boom)
    model_id = _upload(auth_client)
    scan_id = auth_client.post("/scans", json={"model_id": model_id, "attacks": ["fgsm"]}).json()["id"]

    scan = auth_client.get(f"/scans/{scan_id}").json()
    assert scan["status"] == "failed"
    assert "137" in scan["error"]
    assert auth_client.get(f"/scans/{scan_id}/score").status_code == 409
