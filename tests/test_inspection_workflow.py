from datetime import date
from pathlib import Path

from property_images.workflow import (
    AssetKind,
    ImageBrief,
    PropertyImageRequest,
    PropertyImageWorkflow,
)


class RecordingGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[ImageBrief, str]] = []

    def generate_png(self, brief: ImageBrief, request_id: str) -> bytes:
        self.calls.append((brief, request_id))
        return b"png-for-test"


def test_inspection_request_puts_due_date_in_image_and_stores_once(tmp_path: Path) -> None:
    generator = RecordingGenerator()
    workflow = PropertyImageWorkflow(generator, tmp_path)
    request = PropertyImageRequest(
        property_id="elm-204",
        kind=AssetKind.INSPECTION_REMINDER,
        summary="Check smoke alarms",
        due_date=date(2027, 2, 18),
        request_id="inspect-elm-204-2027",
    )

    first = workflow.run(request)
    second = workflow.run(request)

    assert "2027-02-18" in generator.calls[0][0].prompt
    assert "checklist" in generator.calls[0][0].prompt
    assert len(generator.calls) == 1
    assert first == second
    assert (tmp_path / first.relative_path).read_bytes() == b"png-for-test"
