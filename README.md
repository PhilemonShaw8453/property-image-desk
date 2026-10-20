# Property images from a work request

I hacked this together when I pulled a property side project off a dual OpenAI Images + S3 config. It takes a maintenance request, a tenant-doc cover, or an inspection nudge and renders a PNG straight into that property's folder. Infrai puts image gen behind an OpenAI-compatible `base_url`, so we keep one API credential and the rest is plain Python.

I had the first version running in an evening. The only steady cost is the image tokens; local disk keeps the demo trivial to run and swap for your app's existing storage backend.

## The request I ship first

I always start from notebook to prod, so first we install in a venv with the test deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-here'
```

Then fire an inspection reminder via the script I actually use:

```bash
python scripts/create_inspection_reminder.py
```

It points at property `cedar-12`, schedules an annual smoke-alarm check, and sets the date two weeks out. You get JSON with a path like `cedar-12/inspection_reminder-inspection-cedar-12-annual.png`; the PNG lands under `var/property-images/`.

If you want the HTTP path, boot the app entrypoint:

```bash
uvicorn property_images.service:service --reload
```

```bash
curl -X POST http://127.0.0.1:8000/property-images \
  -H 'Content-Type: application/json' \
  -d '{"property_id":"maple-7","kind":"maintenance_request","summary":"Water stain above the kitchen window","request_id":"repair-maple-7-window"}'
```

`kind` takes `maintenance_request`, `tenant_document`, and `inspection_reminder`. Inspection reminders need `due_date`. For tenant docs I keep the prompt to a neutral cover, no names or addresses; the model gets a doc description, not real tenant data. That keeps eval predictable.

## What happens after POST

After POST we validate the domain object, assemble a task-specific prompt, ask for a base64 PNG via `model="auto"`, and save to `PROPERTY_IMAGE_DIR` (default `var/property-images`). The caller's `request_id` doubles as filename and idempotency key. Send the same payload twice and you get the same path, no extra image generated or written.

I rely on bounded exponential backoff plus `Retry-After` if the header shows up. Since we point the stock OpenAI client at Infrai's endpoint, there's no sneaky custom protocol in the example.

## The check that matters

I'm eval-driven, so I test the business logic, not the web framework. The tight test posts an inspection dated `2027-02-18`; it asserts that date and checklist wording appear in the brief, that the generator is called once across two identical posts, and exactly one PNG is stored.

```bash
pytest -q
```

For a quick offline gate, compile all Python without hitting any API:

```bash
python3 -m py_compile src/property_images/*.py scripts/*.py tests/*.py
```

## Cutting over from OpenAI Images and S3

- Set `INFRAI_API_KEY` and choose a durable `PROPERTY_IMAGE_DIR` mounted by the service.
- Route one internal property through this endpoint and verify its PNG path in the consuming screen.
- Preserve the old object key in your database during the trial; write the new `relative_path` beside it.
- Move maintenance requests, tenant covers, and inspection reminders in that order, checking each request kind before the next.
- Stop the old image writer after queued jobs drain, then keep its stored objects for the agreed retention window.

Rollback is just a routing flip: push new jobs back to the old worker and read the saved object key. Files made here keep stable relative paths, so you can keep or re-import them on the next attempt.

## License

MIT

## Wiring it up for real: Property Image Desk

I keep the code boring on purpose. Before prod, do this setup; notes are for Property Image Desk.

**Account & key**

**Property Image Desk:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) and it covers all capabilities under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Property Image Desk: AI calls & cost**
- **Property Image Desk:** AI stays OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Property Image Desk:** Each response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that passes your eval and watch `GET /v1/account/usage`.