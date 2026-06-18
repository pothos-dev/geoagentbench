"""Pydantic models for the benchmark HTTP contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal["system", "text", "thinking", "tool_call", "tool_result"]
SessionStatusName = Literal["idle", "running", "failed"]


class Event(BaseModel):
    ts: str
    type: EventType
    role: Literal["user", "assistant"] | None = None
    content: Any


class UsageBlock(BaseModel):
    estimated_cost_usd: float = 0.0
    duration_s: float = 0.0
    model: str | None = None
    agent_version: str | None = None


class SessionCreatedResponse(BaseModel):
    session_id: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatusName
    created_at: str
    last_activity_at: str
    error: str | None = None
    usage: UsageBlock


class MessageRequest(BaseModel):
    instruction: str = Field(min_length=1)


class FilesListResponse(BaseModel):
    files: list[str]


class MessagesResponse(BaseModel):
    events: list[Event]


class ErrorResponse(BaseModel):
    error: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    adapter: str
    version: str
