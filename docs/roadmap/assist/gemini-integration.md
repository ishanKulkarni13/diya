# Gemini Integration Architecture

This document describes how the Gemini AI provider is integrated into the Assist backend.

---

## Provider Architecture

The Assist module follows a three-tier architecture consistent with the rest of the backend:

```
Router (HTTP parsing)
  ↓
Service (business logic + orchestration)
  ↓
Provider (external API communication)
```

### Files

```
modules/assist/
├── router.py              # Thin HTTP layer (multipart parsing, DI)
├── schemas.py             # Pydantic API response contract
├── service.py             # AssistService (orchestration + response mapping)
└── providers/
    ├── __init__.py
    └── gemini.py          # GeminiProvider (google-genai SDK wrapper)
```

---

## Configuration

Gemini is configured through environment variables loaded by `pydantic-settings`.

### Required

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |

### Optional

| Variable | Default | Description |
|---|---|---|
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | Gemini model to use |

These are defined in `app/config/settings.py` → `ProviderSettings`.

If `GEMINI_API_KEY` is not set, the endpoint returns `503 Service Unavailable` with error code `ASSIST.PROVIDER.NOT_CONFIGURED`.

---

## Prompt Strategy

The prompt is constructed in `GeminiProvider._build_prompt()`.

It prioritizes information in this order:

1. **Immediate hazards** (obstacles, stairs, vehicles, wet floors)
2. **Navigation information** (doorways, paths, intersections)
3. **Important objects** the user should know about
4. **Visible text** (signs, labels, screens)
5. **General scene description**

Target response length: **1-3 concise sentences**.

The prompt explicitly instructs the model to avoid describing colors or aesthetics unless safety-relevant.

---

## Structured Output

Gemini is configured with `response_mime_type: application/json` and a Pydantic `response_schema`. This forces the model to return structured JSON that maps directly into the existing API contract.

### Schema

```python
class GeminiAnalysisResult(BaseModel):
    spoken_text: str
    display_text: str
    hazards: list[str]
    detected_objects: list[str]
    confidence: float
```

This is parsed via `response.parsed` into a strongly-typed Python object, eliminating free-text parsing risk.

---

## Response Mapping

```
GeminiAnalysisResult
  ↓ AssistService._build_response()
AssistResponseData + ProviderInfo
  ↓
AssistTurnData
  ↓
AssistResponse (API envelope)
```

The Flutter client receives the identical JSON shape from Phase 1. No Flutter changes are required for the response contract.

---

## Error Handling

| Scenario | HTTP Status | Error Code |
|---|---|---|
| Missing API key | 503 | `ASSIST.PROVIDER.NOT_CONFIGURED` |
| Gemini API failure | 502 | `ASSIST.PROVIDER.FAILED` |
| Invalid JSON in request | 400 | (inline message) |

All Gemini SDK exceptions are caught inside `GeminiProvider` and re-raised as `GeminiProviderError`. The `AssistService` catches this and translates it to an `HTTPException`. Raw SDK exceptions never leak to clients.

---

## Image Handling

Images are ephemeral throughout the pipeline:

- **Flutter**: Captures via `image_picker`, uploads via multipart, deletes temp file in `finally` block
- **Backend**: Reads bytes from `UploadFile`, passes to Gemini, discards after response
- **No persistence**: Images are never written to disk or database on the backend

---

## Known Limitations

1. The Gemini SDK call is synchronous (`generate_content`) rather than async. For the current single-turn use case this is acceptable but may need migration to `generate_content_async` for high-concurrency deployments.
2. Session IDs are still generated client-side. Real session persistence is Phase 2.
3. No retry logic on transient Gemini failures. The client receives a 502 and can retry.
