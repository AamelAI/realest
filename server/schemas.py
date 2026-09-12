"""Pydantic models that cross a boundary (model <-> code, server <-> page).

Never hand-parse JSON out of a model response. Everything the model produces
lands in one of these.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class CallStatus(str, Enum):
    PENDING = "pending"
    CALLING = "calling"
    VERIFIED = "verified"
    DEAD = "dead"
    NO_ANSWER = "no_answer"
    BOOKED = "booked"


class Preferences(BaseModel):
    beds: int | None = None
    baths: int | None = None
    areas: list[str] = Field(default_factory=list)
    max_rent: int | None = None
    parking: bool | None = None
    pets: str | None = None
    priority_order: list[str] = Field(default_factory=list)
    extra_questions: list[str] = Field(default_factory=list)


class CallOutcome(BaseModel):
    """What a human actually told us. This is the whole product.

    Only populate a field if the person said it. A hallucinated value here
    destroys the claim the entire submission rests on.
    """
    available: bool | None = None
    real_rent: int | None = None
    addons: list[str] = Field(default_factory=list)
    pets_allowed: str | None = None
    viewing_slot: str | None = None
    answers: dict[str, str] = Field(default_factory=dict)
    source: str = ""
    raw_transcript: str = ""


class Listing(BaseModel):
    listing_id: str
    address: str
    rent: int                       # entry price; the REAL cost comes back from the call
    beds: int
    baths: int
    neighbourhood: str = ""         # the ranker filters on this
    property_type: str = ""
    sqft: int | None = None
    parking_included: bool = False  # what the LISTING claims - the call often disagrees
    pets: str | None = None
    amenities: list[str] = Field(default_factory=list)
    transit_note: str = ""
    photos: list[str] = Field(default_factory=list)
    photo_url: str = ""             # hero image for the card
    source_url: str = ""
    agent_name: str = ""
    # Always our own demo contacts. We never cold-call strangers, and real agents'
    # details must not land in a repo that goes public at submission.
    agent_phone: str = ""
    agent_email: str = ""


class ListingState(BaseModel):
    listing_id: str
    status: CallStatus = CallStatus.PENDING
    rank: int = 0
    outcome: CallOutcome | None = None
    email_draft: str | None = None


class SessionState(BaseModel):
    session_id: str
    preferences: Preferences = Field(default_factory=Preferences)
    listings: list[ListingState] = Field(default_factory=list)
    agent_says: str = ""
    updated_at: float = 0.0
