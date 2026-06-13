# Assist State Machine

Assist needs one runtime state machine shared by UI, hardware, wake word, and foreground service triggers. Trigger sources may differ, but once an `AssistIntent` exists the execution path should be the same.

## States

```txt
Idle
Preflight
Queued
Transcribing
Capturing
Analyzing
Speaking
AwaitingFollowUp
Completed
Failed
Cancelled
Interrupted
Preempted
```

## State Responsibilities

`Idle`: no active turn is running.

`Preflight`: validates session, permissions, device availability, network status, battery-sensitive constraints, and safety preemption.

`Queued`: turn is accepted but waiting because another Assist turn, speech output, or higher-priority operation is active.

`Transcribing`: captures and converts user speech to text for long press, voice command, wake word follow-up, or future hands-free modes.

`Capturing`: captures image or receives an image reference from phone camera, goggle camera, or another device.

`Analyzing`: uploads required context and waits for FastAPI to assemble prompt, call the selected AI provider, persist the turn, and return the normalized response.

`Speaking`: Flutter speaks the response through the configured speech output port.

`AwaitingFollowUp`: the assistant is ready for a follow-up question within the same conversation window.

`Completed`: the turn finished and can be represented in history.

`Failed`: the turn failed with a domain error.

`Cancelled`: the user or runtime cancelled the turn before completion.

`Interrupted`: non-emergency interruption occurred, such as a newer user command replacing speech output.

`Preempted`: a higher-priority safety event, especially SOS, stopped Assist immediately.

## Core Transitions

```txt
Idle -> Preflight
Preflight -> Transcribing
Preflight -> Capturing
Preflight -> Queued
Preflight -> Failed
Queued -> Preflight
Transcribing -> Capturing
Transcribing -> Failed
Capturing -> Analyzing
Capturing -> Failed
Analyzing -> Speaking
Analyzing -> AwaitingFollowUp
Analyzing -> Failed
Speaking -> Completed
Speaking -> AwaitingFollowUp
AwaitingFollowUp -> Preflight
Any active state -> Cancelled
Any active state -> Preempted
Speaking -> Interrupted
Failed -> Preflight
```

## Cancellation

Cancellation should be explicit and idempotent. Flutter should cancel local capture, STT, TTS, upload, and pending API calls when possible. FastAPI should expose a cancellation endpoint for long-running or streaming turns, and repeated cancellation requests should return the current terminal status instead of creating new side effects.

## Retry

Retry should create a new turn attempt attached to the same session and previous turn reference. Do not mutate the original failed turn into success; that loses observability. Retry policy should distinguish:

- transient network failure
- media capture failure
- transcription failure
- provider timeout
- provider content refusal
- user cancellation
- safety preemption

## Timeouts

Recommended initial timeout classes:

```txt
preflight_timeout
stt_timeout
capture_timeout
analysis_timeout
tts_timeout
stream_idle_timeout
```

Timeouts should be centrally configured. UI, hardware, and foreground service triggers must not invent separate timeout values.

## SOS Preemption

SOS preemption is a hard rule. If a safety-critical event arrives while Assist is transcribing, capturing, analyzing, or speaking, Assist must transition to `Preempted`, release media resources, stop TTS, cancel in-flight work where possible, and allow the safety workflow to run.

The current hardware `EventRouter` already gives safety events immediate bypass behavior. Assist should consume resolved hardware events through a normalized trigger layer and preserve that priority model.

## Missing Transition Risks

- Without `Preflight`, permission and device failures spread across UI and hardware handlers.
- Without `Queued`, simultaneous triggers can create duplicate API calls.
- Without `Interrupted`, speech cancellation becomes indistinguishable from turn failure.
- Without `Preempted`, Assist can compete with SOS workflows.
- Without `AwaitingFollowUp`, follow-up questions may accidentally start unrelated sessions.

## Test Targets

- Single tap reaches `Capturing -> Analyzing -> Speaking -> Completed`.
- Long press reaches `Transcribing -> Capturing -> Analyzing -> Speaking`.
- Duplicate triggers within a dedupe window produce one turn.
- SOS preempts every active state.
- API timeout maps to a retryable failure.
- TTS interruption stops speaking without corrupting conversation history.
