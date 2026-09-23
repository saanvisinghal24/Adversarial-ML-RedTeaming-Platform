"""Seed a demo account + model + finished scan so the dashboard isn't empty in a demo.

    python -m scripts.seed_demo            # from /backend, with the venv active

Idempotent-ish: re-running adds another scan to the same demo user/model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import MLModel, Scan, User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.pipeline import run_scan_pipeline  # noqa: E402

DEMO_EMAIL = "demo@redteam.local"
DEMO_PASSWORD = "demo-password-123"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)

        model = db.scalar(select(MLModel).where(MLModel.user_id == user.id))
        if model is None:
            artefact = Path("storage") / str(user.id) / "demo-model.pkl"
            artefact.parent.mkdir(parents=True, exist_ok=True)
            artefact.write_bytes(b"demo-artefact-not-a-real-model")
            model = MLModel(
                user_id=user.id,
                name="phishing-url-rf",
                file_path=str(artefact.resolve()),
                model_type="sklearn",
                version="1",
                checksum_sha256="0" * 64,
                size_bytes=artefact.stat().st_size,
            )
            db.add(model)
            db.commit()
            db.refresh(model)

        scan = Scan(
            model_id=model.id,
            status="queued",
            threat_model="white_box",
            attack_config={
                "attacks": ["fgsm", "pgd", "hopskipjump", "poisoning"],
                "params": {},
            },
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id
    finally:
        db.close()

    run_scan_pipeline(scan_id)
    print(f"seeded: login as {DEMO_EMAIL} / {DEMO_PASSWORD} — scan {scan_id}")  # noqa: T201


if __name__ == "__main__":
    main()
