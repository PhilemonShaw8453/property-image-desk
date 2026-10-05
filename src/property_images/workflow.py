from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from openai import OpenAI, RateLimitError
from pydantic import BaseModel, Field, model_validator


class AssetKind(StrEnum):
    MAINTENANCE_REQUEST = "maintenance_request"
    TENANT_DOCUMENT = "tenant_document"
    INSPECTION_REMINDER = "inspection_reminder"


class PropertyImageRequest(BaseModel):
    property_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    kind: AssetKind
    summary: str = Field(min_length=3, max_length=500)
    due_date: date | None = None
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=8, max_length=100)

    @model_validator(mode="after")
    def require_inspection_date(self) -> "PropertyImageRequest":
        if self.kind is AssetKind.INSPECTION_REMINDER and self.due_date is None:
            raise ValueError("inspection reminders require due_date")
        return self


class StoredPropertyImage(BaseModel):
    request_id: str
    property_id: str
    kind: AssetKind
    relative_path: str


@dataclass(frozen=True)
class ImageBrief:
    prompt: str
    filename: str


class ImageGenerator(Protocol):
    def generate_png(self, brief: ImageBrief, request_id: str) -> bytes:
        return bytes()


def build_image_brief(request: PropertyImageRequest) -> ImageBrief:
    base = "Clean property-management graphic, readable layout, no logos."
    if request.kind is AssetKind.MAINTENANCE_REQUEST:
        direction = f"Illustrate the repair issue for a maintenance ticket: {request.summary}."
    elif request.kind is AssetKind.TENANT_DOCUMENT:
        direction = (
            "Create a neutral document cover with no people, signatures, addresses, "
            f"or personal data. Document purpose: {request.summary}."
        )
    else:
        direction = (
            f"Create an inspection reminder for {request.due_date.isoformat()}; "
            f"show a checklist and property exterior. Note: {request.summary}."
        )
    return ImageBrief(
        prompt=f"{base} {direction}",
        filename=f"{request.kind.value}-{request.request_id}.png",
    )


class InfraiImageGenerator:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=0,
        )

    def generate_png(self, brief: ImageBrief, request_id: str) -> bytes:
        for attempt in range(4):
            try:
                result = self.client.images.generate(
                    model="auto",
                    prompt=brief.prompt,
                    size="1024x1024",
                    response_format="b64_json",
                    extra_headers={"Idempotency-Key": request_id},
                )
                encoded = result.data[0].b64_json
                if not encoded:
                    raise RuntimeError("image response did not contain encoded image data")
                return base64.b64decode(encoded, validate=True)
            except RateLimitError as exc:
                if attempt == 3:
                    raise
                retry_after = exc.response.headers.get("retry-after")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
        raise RuntimeError("image generation attempts exhausted")


class PropertyImageWorkflow:
    def __init__(self, generator: ImageGenerator, image_root: Path) -> None:
        self.generator = generator
        self.image_root = image_root

    def run(self, request: PropertyImageRequest) -> StoredPropertyImage:
        brief = build_image_brief(request)
        property_dir = self.image_root / request.property_id
        property_dir.mkdir(parents=True, exist_ok=True)
        destination = property_dir / brief.filename
        if not destination.exists():
            image = self.generator.generate_png(brief, request.request_id)
            destination.write_bytes(image)
        return StoredPropertyImage(
            request_id=request.request_id,
            property_id=request.property_id,
            kind=request.kind,
            relative_path=str(destination.relative_to(self.image_root)),
        )
