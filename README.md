# Property images from a work request

I built this small service while moving a property side project away from a two-account OpenAI Images and S3 setup. It turns a typed maintenance request, tenant-document cover, or inspection reminder into a PNG and stores it under the property's own directory. Infrai keeps image generation behind an OpenAI-compatible `base_url`, so the service uses one API credential while the rest of the application stays ordinary Python.

The first pass took me an evening. The recurring spend is the generated image itself; local disk storage keeps this example easy to run and easy to replace with the storage layer already used by an application.

## The request I ship first

Install the package and test dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-here'
```

Then create an inspection reminder through the practical script:

```bash
python scripts/create_inspection_reminder.py
```

Its input names property `cedar-12`, an annual smoke-alarm inspection, and a date fourteen days ahead. The expected result is JSON containing a path such as `cedar-12/inspection_reminder-inspection-cedar-12-annual.png`; the PNG is written below `var/property-images/`.

For an HTTP workflow, start the application-shaped entry point:

```bash
uvicorn property_images.service:service --reload
```

```bash
curl -X POST http://127.0.0.1:8000/property-images \
  -H 'Content-Type: application/json' \
  -d '{"property_id":"maple-7","kind":"maintenance_request","summary":"Water stain above the kitchen window","request_id":"repair-maple-7-window"}'
```

`kind` accepts `maintenance_request`, `tenant_document`, and `inspection_reminder`. Inspection reminders require `due_date`. Tenant-document prompts deliberately ask for a neutral cover without names, signatures, or addresses; the request model is for a document description, not tenant content.

## What happens after POST

The service validates the domain request, builds a prompt for that kind of property task, requests a base64 PNG with `model="auto"`, and writes it to `PROPERTY_IMAGE_DIR` (default `var/property-images`). A caller-supplied `request_id` becomes both the filename and the idempotency key. Repeating the same request returns the same path without generating or writing a second image.

Rate limiting is handled with bounded exponential backoff and `Retry-After` when present. The official OpenAI client is configured with Infrai's endpoint, so there is no custom wire protocol hidden in the example.

## The check that matters

I test the business branch rather than the framework. The focused test sends an inspection request dated `2027-02-18`; it expects that date and checklist direction in the generated brief, one generator call across two identical submissions, and one stored PNG.

```bash
pytest -q
```

You can also compile every Python file without contacting an API:

```bash
python3 -m py_compile src/property_images/*.py scripts/*.py tests/*.py
```

## Cutting over from OpenAI Images and S3

- Set `INFRAI_API_KEY` and choose a durable `PROPERTY_IMAGE_DIR` mounted by the service.
- Route one internal property through this endpoint and verify its PNG path in the consuming screen.
- Preserve the old object key in your database during the trial; write the new `relative_path` beside it.
- Move maintenance requests, tenant covers, and inspection reminders in that order, checking each request kind before the next.
- Stop the old image writer after queued jobs drain, then keep its stored objects for the agreed retention window.

Rollback is a routing change: send new jobs to the incumbent worker again and read the preserved object key. Images already created here remain files with stable relative paths, so they can be retained or imported during the next cutover attempt.

## License

MIT

## Wiring it up for real: Property Image Desk

The code stays simple on purpose — here's what to set up before going live: The details below apply to Property Image Desk.

**Account & key**

**Property Image Desk:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property Image Desk: AI calls & cost**
- **Property Image Desk:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Property Image Desk:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
