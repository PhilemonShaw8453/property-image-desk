from datetime import date, timedelta
from pathlib import Path

from property_images.workflow import (
    AssetKind,
    InfraiImageGenerator,
    PropertyImageRequest,
    PropertyImageWorkflow,
)


request = PropertyImageRequest(
    property_id="cedar-12",
    kind=AssetKind.INSPECTION_REMINDER,
    summary="Annual smoke alarm and balcony inspection",
    due_date=date.today() + timedelta(days=14),
    request_id="inspection-cedar-12-annual",
)
result = PropertyImageWorkflow(
    InfraiImageGenerator(),
    Path("var/property-images"),
).run(request)
print(result.model_dump_json(indent=2))
