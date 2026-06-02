import httpx
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import DeliveryAttempt


def deliver_webhook(event_id: str, target_url: str, payload: str):
    db = SessionLocal()
    attempt_number = 1

    try:
        existing = db.query(DeliveryAttempt).filter(
            DeliveryAttempt.event_id == event_id
        ).count()
        attempt_number = existing + 1

        response = httpx.post(
            target_url,
            content=payload or "{}",
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )

        status = "success" if response.status_code < 400 else "failed"

        attempt = DeliveryAttempt(
            event_id=event_id,
            status=status,
            attempt_number=attempt_number,
            response_code=response.status_code,
            attempted_at=datetime.now(timezone.utc)
        )
        db.add(attempt)
        db.commit()

        if status == "failed":
            raise Exception(f"Delivery failed with status {response.status_code}")

    except httpx.RequestError as e:
        attempt = DeliveryAttempt(
            event_id=event_id,
            status="failed",
            attempt_number=attempt_number,
            error_message=str(e),
            attempted_at=datetime.now(timezone.utc)
        )
        db.add(attempt)
        db.commit()
        raise

    finally:
        db.close()  