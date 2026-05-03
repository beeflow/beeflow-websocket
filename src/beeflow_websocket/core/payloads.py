"""copyright (c) 2014 - 2026 Beeflow Ltd.

Author Rafal Przetakowski <rafal.p@beeflow.co.uk>"""

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorPayload(BaseModel):
    """Represent an RFC 9457 Problem Details response body."""

    model_config = ConfigDict(frozen=True)

    msg_id: UUID | None = None
    req_id: UUID | None = None
    type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: int = Field(ge=400, le=599)
    detail: str = Field(min_length=1)
    code: str = Field(min_length=1)
    instance: str | None = Field(default=None, min_length=1)

    media_type: ClassVar[str] = "application/problem+json"

    @field_validator("type", "title", "detail", "code", "instance")
    @classmethod
    def validate_text_member(cls, value: str | None) -> str | None:
        """Reject blank Problem Details text members."""
        if value is None:
            return None

        normalised_value = value.strip()
        if normalised_value == "":
            raise ValueError("Problem Details text members must not be blank.")

        return normalised_value

    def with_message_id(self, msg_id: UUID) -> "ErrorPayload":
        """Return the same Problem Details payload enriched with server message metadata."""
        return ErrorPayload(
            msg_id=msg_id,
            req_id=self.req_id,
            type=self.type,
            title=self.title,
            status=self.status,
            detail=self.detail,
            code=self.code,
            instance=self.instance,
        )

    def to_dict(self) -> dict[str, object]:
        """Return the JSON object used as the API error response body."""
        return self.model_dump(mode="json", exclude_none=True)


class WebSocketRequestIdentifier(BaseModel):
    """Extract the client request identifier from a raw WebSocket message."""

    model_config = ConfigDict(frozen=True)

    req_id: UUID


class WebSocketActionPayload(BaseModel):
    """Represent a WebSocket action envelope received from the client."""

    model_config = ConfigDict(frozen=True)

    msg_id: UUID
    req_id: UUID
    action: str = Field(min_length=1)
    payload: dict[str, object]

    @field_validator("action")
    @classmethod
    def validate_text_member(cls, value: str) -> str:
        """Reject blank WebSocket action envelope text members."""
        normalised_value = value.strip()
        if normalised_value == "":
            raise ValueError("WebSocket action envelope text members must not be blank.")

        return normalised_value


class WebSocketEventPayload(BaseModel):
    """Represent the common WebSocket event envelope sent to the client."""

    model_config = ConfigDict(frozen=True)

    msg_id: UUID | None = None
    req_id: UUID | None = None
    seq: int | None = Field(default=None, ge=1)
    event: str = Field(min_length=1)
    recipient: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    payload: dict[str, object]

    @field_validator("event", "recipient", "recipient_id")
    @classmethod
    def validate_text_member(cls, value: str) -> str:
        """Reject blank WebSocket event text members."""
        normalised_value = value.strip()
        if normalised_value == "":
            raise ValueError("WebSocket event text members must not be blank.")

        return normalised_value

    def with_dispatch_metadata(self, *, msg_id: UUID, seq: int) -> "WebSocketEventPayload":
        """Return the event envelope enriched with server delivery metadata."""
        return WebSocketEventPayload(
            msg_id=msg_id,
            req_id=self.req_id,
            seq=seq,
            event=self.event,
            recipient=self.recipient,
            recipient_id=self.recipient_id,
            payload=self.payload,
        )

    def to_dict(self) -> dict[str, object]:
        """Return the JSON object used as the WebSocket event response body."""
        return self.model_dump(mode="json", exclude_none=True)
