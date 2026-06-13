# Assist API Contracts

These contracts are proposed planning artifacts. They should follow the existing FastAPI versioning style under `/api/v1` and use the project's standard authentication, error handling, and idempotency patterns.

## Principles

- Flutter sends structured intent and media references.
- FastAPI assembles prompts and calls AI providers.
- Every turn request should support idempotency.
- API responses should be provider-neutral.
- Streaming should be additive, not a breaking change.

## Endpoints

```txt
POST /api/v1/assist/sessions
GET /api/v1/assist/sessions/{session_id}
POST /api/v1/assist/sessions/{session_id}/turns
GET /api/v1/assist/sessions/{session_id}/turns/{turn_id}
POST /api/v1/assist/sessions/{session_id}/cancel
WS /api/v1/assist/sessions/{session_id}/stream
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
Idempotency-Key: <key>
Authorization: Bearer <token>
```

Request:

```json
{
  "intent": {
    "type": "answer_question_about_scene",
    "user_question": "What is in front of me?"
  },
  "trigger": {
    "source_type": "ui_button",
    "press_type": "long_press",
    "source_device_id": null,
    "occurred_at": "2026-06-14T00:00:00Z"
  },
  "media": [
    {
      "type": "image",
      "source": "phone_camera",
      "upload_id": "string",
      "content_type": "image/jpeg",
      "captured_at": "2026-06-14T00:00:00Z",
      "retention": "ephemeral"
    }
  ],
  "client_context": {
    "locale": "en-IN",
    "timezone": "Asia/Calcutta",
    "device_state": {
      "smart_cane_connected": true,
      "smart_goggles_connected": false
    }
  }
}
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

If a general media API does not exist yet, Assist should define one before large payload turn requests:

```txt
POST /api/v1/media/uploads
PUT signed upload URL
```

Turn creation should reference uploaded media by id. Avoid base64 image payloads in normal turn requests because they increase memory pressure, logging risk, and retry cost.

## Streaming Strategy

V1 may return a complete response. Streaming should be designed now:

```txt
WS /api/v1/assist/sessions/{session_id}/stream
```

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
