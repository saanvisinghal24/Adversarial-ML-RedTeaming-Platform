"""Report export — the M5 deliverable the demo actually gets judged on."""

import io

from fastapi.testclient import TestClient


def _finished_scan(client: TestClient) -> str:
    model_id = client.post(
        "/models",
        data={"name": "phishing-url-rf", "model_type": "sklearn"},
        files={"file": ("model.pkl", io.BytesIO(b"artefact"), "application/octet-stream")},
    ).json()["id"]
    return client.post("/scans", json={"model_id": model_id, "attacks": ["fgsm", "pgd"]}).json()["id"]


def _token(client: TestClient) -> str:
    return client.headers["Authorization"].split(" ", 1)[1]


def test_pdf_and_html_report(auth_client: TestClient) -> None:
    scan_id = _finished_scan(auth_client)
    token = _token(auth_client)

    pdf = auth_client.get(f"/scans/{scan_id}/report", params={"token": token, "format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")
    assert "attachment" in pdf.headers["content-disposition"]

    html = auth_client.get(f"/scans/{scan_id}/report", params={"token": token, "format": "html"})
    assert html.status_code == 200
    assert "ROBUSTNESS" in html.text.upper()
    assert "AML.T" in html.text  # ATLAS technique made it into the report


def test_report_rejects_bad_token(auth_client: TestClient) -> None:
    scan_id = _finished_scan(auth_client)
    res = auth_client.get(f"/scans/{scan_id}/report", params={"token": "not.a.jwt"})
    assert res.status_code == 401
