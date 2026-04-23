"""
Pydantic data models for the enrollment agent system.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class LeadInput(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    education: str
    experience: str  # e.g. "2 years"
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    program_interest: Optional[str] = ""


class ChatMessage(BaseModel):
    role: str  # "user" | "agent" | "human"
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatInput(BaseModel):
    message: str
    role: str = "user"  # "user" or "human" (sales rep)


class CloseInput(BaseModel):
    outcome: str  # "closed_won" | "closed_lost"
    notes: Optional[str] = ""


class FollowUpInput(BaseModel):
    message: Optional[str] = None
