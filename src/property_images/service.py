import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from openai import APIStatusError, RateLimitError

from .workflow import InfraiImageGenerator, PropertyImageRequest, PropertyImageWorkflow, StoredPropertyImage

service = FastAPI(title="Property Image Desk")


@service.post("/property-images", response_model=StoredPropertyImage, status_code=201)
def create_property_image(request: PropertyImageRequest) -> StoredPropertyImage:
    root = Path(os.environ.get("PROPERTY_IMAGE_DIR", "var/property-images"))
    try:
        return PropertyImageWorkflow(InfraiImageGenerator(), root).run(request)
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured") from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail="image generation is busy; retry later") from exc
    except APIStatusError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail="image generation request was rejected") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
