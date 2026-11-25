from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """A follow-up message sent into an existing trip conversation."""

    thread_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class AgentResponse(BaseModel):
    thread_id: str
    answer: str


class TripRequest(BaseModel):
    """Details collected from the trip form. Required fields come first."""

    # Required
    origin: str = Field(..., description="City the trip starts from")
    destination: str = Field(..., description="Place the user wants to visit")
    days: int = Field(..., ge=1, le=30, description="Number of days of the trip")
    people: int = Field(..., ge=1, le=50, description="Number of travelers")

    # Optional
    budget: Optional[float] = Field(None, gt=0, description="Total trip budget")
    currency: str = Field("INR", description="Currency of the budget")
    interests: List[str] = Field(default_factory=list)
    pace: Optional[Literal["relaxed", "balanced", "packed"]] = None
    stay_type: Optional[Literal["budget", "mid-range", "luxury"]] = None

    @field_validator("origin", "destination")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v
