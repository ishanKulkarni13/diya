# Assist API Contracts

These contracts are proposed planning artifacts. They should follow the existing FastAPI versioning style under `/api/v1` and use the project's standard authentication, error handling, and idempotency patterns.

## Principles

- Flutter sends structured intent and media references.
- FastAPI assembles prompts and calls AI providers.
- Every turn request should support idempotency.
- API responses should be provider-neutral.
- Streaming should be additive later, not part of the MVP contract.

## Endpoints

```txt
POST /api/v1/assist/sessions
GET /api/v1/assist/sessions/{session_id}
POST /api/v1/assist/sessions/{session_id}/turns
GET /api/v1/assist/sessions/{session_id}/turns/{turn_id}
POST /api/v1/assist/sessions/{session_id}/cancel
```

## Create Session

```txt
POST /api/v1/assist/sessions
Idempotency-Key: <key>
Authorization: Bearer <token>
```

Request:

```json
{
  "source": "ui",
  "locale": "en-IN",
  "timezone": "Asia/Calcutta",
  "client_context": {
    "app_version": "string",
    "device_platform": "android",
    "accessibility_mode": true
  }
}
```

Response:

```json
{
  "data": {
    "session_id": "uuid",
    "status": "active",
    "created_at": "2026-06-14T00:00:00Z",
    "expires_at": "2026-06-14T01:00:00Z"
  },
  "trace_id": "string"
}
```

## Create Turn

```txt
POST /api/v1/assist/sessions/{session_id}/turns
Content-Type: multipart/form-data
Idempotency-Key: <key>
Authorization: Bearer <token>
```

Preferred V1 request shape:

```txt
intent_json: {"type":"describe_scene"}
trigger_json: {"source_type":"ui_button","press_type":"tap","occurred_at":"2026-06-14T00:00:00Z"}
client_context_json: {"locale":"en-IN","timezone":"Asia/Calcutta","device_state":{"smart_cane_connected":true,"smart_goggles_connected":false}}
image_file: <binary jpeg/png>
```

Response:

```json
{
  "data": {
    "turn_id": "uuid",
    "session_id": "uuid",
    "status": "completed",
    "response": {
      "spoken_text": "There is a chair directly ahead and a doorway to your left.",
      "display_text": "Chair ahead. Doorway left.",
      "confidence": 0.84,
      "follow_up_mode": "available",
      "hazards": [],
      "detected_objects": ["chair", "doorway"]
    },
    "provider": {
      "name": "gemini",
      "model": "configured-backend-model",
      "latency_ms": 1200
    }
  },
  "trace_id": "string"
}
```

## V1 Media Recommendation

Use `multipart/form-data` for the first implementation.

Why this is the best V1 choice:

- It keeps the first vertical slice to one request and one response.
- It is easy to implement in Flutter and FastAPI.
- It avoids base64 expansion, which wastes bandwidth and memory.
- It avoids an upload-first contract before we know whether Assist needs durable media or resumable uploads.

Why not base64:

- It inflates payload size.
- It is easier to log accidentally.
- It creates unnecessary memory pressure on mobile and backend sides.

Why not upload-first for V1:

- It adds a second API exchange before we have proven the end-to-end flow.
- It is useful later for retained media, background retries, and large uploads, but it is extra surface area for the first slice.

Upload-first remains a future option if retained media, background processing, or replayable analysis becomes a product requirement.

## Error Model

Errors should use stable domain codes:

```json
{
  "error": {
    "code": "assist.analysis_timeout",
    "message": "Assist analysis timed out.",
    "retryable": true,
    "details": {
      "turn_id": "uuid",
      "timeout_ms": 15000
    }
  },
  "trace_id": "string"
}
```

Recommended codes:

```txt
assist.session_not_found
assist.session_expired
assist.duplicate_turn
assist.invalid_intent
assist.media_missing
assist.media_expired
assist.transcript_required
assist.analysis_timeout
assist.provider_unavailable
assist.provider_rejected
assist.cancelled
assist.preempted_by_sos
assist.memory_unavailable
```

## Media Upload

If a general media API does not exist yet, Assist can defer it until a later phase:

```txt
POST /api/v1/media/uploads
PUT signed upload URL
```

That model is a strong future fit for retained media, resumable upload, and background processing. It is not the preferred V1 turn contract.

## Streaming Compatibility

Streaming stays compatible with the turn/session model but is not part of the MVP contract.

Events:

```txt
turn.accepted
analysis.started
analysis.delta
analysis.completed
speech.hint
turn.failed
turn.cancelled
```

Streaming must not change the durable turn model. Final response persistence still happens on the backend.

## Idempotency

Use `Idempotency-Key` for session creation and turn creation. FastAPI should store the key with user id, route, request hash, and response summary. Duplicate requests should not call Gemini again.

## Versioning

Keep endpoint paths under `/api/v1`. Breaking shape changes should use additive fields first. A future `/api/v2/assist` should only be needed if the turn/session model changes materially.
