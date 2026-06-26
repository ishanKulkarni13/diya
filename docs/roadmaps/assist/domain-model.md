# Assist Domain Model

The Assist domain should describe user intent and turn lifecycle independently from UI widgets, hardware adapters, Gemini, camera packages, and Android services. The model below is intentionally stable enough to survive new trigger sources, new AI providers, and background execution.

## AssistTrigger

Purpose: records the raw source that initiated Assist.

Ownership: created by Flutter trigger sources or future foreground services, then normalized before entering the pipeline.

Lifecycle: short-lived input to an Assist turn. It should be attached to the turn metadata for traceability.

Persistence: persist sanitized metadata in FastAPI, such as source type, device id, timestamp, idempotency key, and confidence. Do not persist raw wake-word audio or button telemetry beyond observability needs.

Recommended fields:

```txt
trigger_id
source_type: ui_button | hardware_button | voice_command | wake_word | foreground_service | automation
source_device_id
press_type: tap | long_press | double_press | unknown
occurred_at
confidence
idempotency_key
raw_event_ref
```

## AssistIntent

Purpose: normalized command consumed by the Assist pipeline.

Ownership: Flutter application layer owns normalization. FastAPI receives the normalized intent as part of the turn request.

Lifecycle: starts an Assist turn and remains immutable for that turn.

Persistence: persist in FastAPI as part of `assist_turns` so behavior can be audited and replayed at the domain level.

Recommended intent types:

```txt
describe_scene
answer_question_about_scene
continue_conversation
repeat_last_response
stop_speaking
cancel_assist
```

Intent should not encode implementation details such as "call Gemini" or "use phone camera". Those are policy decisions made by the pipeline and backend.

## AssistSession

Purpose: groups related turns into a user-visible conversation.

Ownership: FastAPI is source of truth. Flutter may cache the active session id.

Lifecycle: created when the user starts Assist or resumes a recent conversation. It can remain open across multiple turns and expire after inactivity.

Persistence: persist in PostgreSQL with user id, status, timestamps, retention policy, and summary pointers.

Recommended statuses:

```txt
active
idle
closed
expired
cancelled
```

## AssistTurn

Purpose: represents one user-assistant exchange.

Ownership: Flutter owns local execution state while the turn is running. FastAPI owns durable turn records, prompt assembly, provider run metadata, and response output.

Lifecycle: created from one normalized intent. It moves through capture, optional transcription, analysis, speech output, completion, failure, or cancellation.

Persistence: persist durable metadata, transcript, response, model/provider metadata, error code, timing, and media references. Raw images and audio should be temporary by default.

## AssistContext

Purpose: describes everything needed to answer the current turn.

Ownership: split responsibility. Flutter supplies immediate context such as trigger, device, capture metadata, transcript, and location/permission-safe runtime hints. FastAPI assembles durable context from conversation history, memory summaries, user profile memory, and backend policy.

Lifecycle: built per turn and should be treated as immutable once analysis starts.

Persistence: persist selected metadata and assembled prompt references for audit. Avoid storing full prompt text unless explicitly required for debugging and protected by a retention policy.

## AssistResponse

Purpose: normalized response returned by FastAPI and consumed by Flutter.

Ownership: FastAPI shapes the response. Flutter renders and speaks it.

Lifecycle: created after analysis. May be delivered as a full response in V1 and streamed in later phases.

Persistence: persist response text, structured safety/action hints, provider metadata, and follow-up eligibility.

Recommended fields:

```txt
turn_id
session_id
spoken_text
display_text
confidence
follow_up_mode
detected_objects
hazards
provider
model
latency_ms
```

## AssistState

Purpose: exposes current runtime progress to UI, speech output, cancellation, and future foreground service notifications.

Ownership: Flutter runtime owns live state. FastAPI owns durable turn/session state.

Lifecycle: state changes during local pipeline execution and should be observable by presentation, service hosts, and tests.

Persistence: persist backend turn status transitions that matter for reliability. Flutter state itself remains ephemeral and recoverable from backend session/turn records.

## Boundary Rules

- Flutter may know what the user is trying to do; it should not know how Gemini prompts are built.
- Hardware events may start Assist; hardware adapters should not call Assist APIs directly.
- TTS and STT are ports used by Assist; they should not own conversation memory.
- Safety and SOS have preemption authority over Assist.
- Background services may host the Assist runtime later, so no domain object should depend on `BuildContext`, widgets, or foreground-only UI state.
