import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue, Retry
from app.database import engine, Base, get_db
from app.models import Event, DeliveryAttempt
from app.schemas import EventCreate, EventResponse, DeliveryAttemptResponse
from app.jobs import deliver_webhook
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Webhook Delivery System")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Webhook Delivery System", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")



@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events", response_model=EventResponse)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue("default", connection=redis_conn)

    db_event = Event(
        event_type=event.event_type,
        target_url=str(event.target_url),
        payload=event.payload
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    queue.enqueue(
        deliver_webhook,
        str(db_event.id),
        str(db_event.target_url),
        db_event.payload,
        retry=Retry(max=3, interval=60)
    )

    return db_event


@app.get("/events/{event_id}/deliveries", response_model=list[DeliveryAttemptResponse])
def get_deliveries(event_id: str, db: Session = Depends(get_db)):
    attempts = db.query(DeliveryAttempt).filter(
        DeliveryAttempt.event_id == event_id
    ).all()

    if not attempts:
        raise HTTPException(status_code=404, detail="No delivery attempts found")

    return attempts