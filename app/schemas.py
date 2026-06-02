from pydantic import BaseModel, HttpUrl
from typing import Optional
from uuid import UUID
from datetime import datetime


class EventCreate(BaseModel):
    event_type: str
    target_url: HttpUrl
    payload: Optional[str] = None


class EventResponse(BaseModel):
    id: UUID
    event_type: str
    target_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryAttemptResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: str
    attempt_number: int
    response_code: Optional[int]
    error_message: Optional[str]
    attempted_at: datetime

    model_config = {"from_attributes": True}