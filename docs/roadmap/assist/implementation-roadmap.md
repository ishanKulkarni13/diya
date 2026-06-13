# Assist Implementation Roadmap

This roadmap is phased to minimize rewrites. Each phase should leave the system in a coherent state and preserve one shared Assist pipeline.

## Phase 1: Assist Vertical Slice

Goal: implement the smallest end-to-end Assist slice with a UI tap, image capture, a FastAPI round trip, a mock response, and TTS.

Scope:

- `features/assist` structure
- core domain models
- `AssistController`
- `AssistPipeline`
- `ImageCapturePort`
- `SpeechOutputPort`
- `AssistApi`
- FastAPI Assist session/turn endpoint
- phone camera capture
- Flutter TTS
- mocked backend response path

Dependencies:

- authenticated session
- camera permission
- FastAPI route and request/response contract
- mock response payload

Risks:

- overbuilding persistence too early
- coupling the slice to Gemini before the contract is proven
- media handling shortcuts becoming permanent

Verification strategy:

- unit-test state machine
- fake API pipeline test
- backend service tests with mock response
- manual single-tap assist on Android

Success criteria:

- single tap uses the shared pipeline
- Flutter never needs Gemini secrets
- one Assist turn can round-trip through FastAPI
- TTS can be stopped
- duplicate taps do not create duplicate turn submissions
- the request/response shape is stable enough for later Gemini wiring

## Phase 2: Conversation Persistence

Goal: preserve Assist sessions and turn history across app restarts.

Scope:

- `assist_sessions`
- `assist_turns`
- `conversation_messages`
- active session recovery
- repeat last response
- basic history retrieval API

Dependencies:

- Phase 1 turn contract
- database migrations
- retention policy draft

Risks:

- storing too much raw context
- confusing session vs conversation boundaries

Verification strategy:

- backend repository tests
- idempotency tests
- app restart recovery test

Success criteria:

- FastAPI can answer current session and turn status
- Flutter can recover active session id
- completed turns are durable without raw media retention by default

## Phase 3: Memory System

Goal: introduce user memory and conversation summaries safely.

Scope:

- user memory facts
- memory summaries
- summary refresh policy
- memory retrieval service
- prompt context assembly
- user consent model

Dependencies:

- privacy decisions
- deletion policy
- provider prompt builder

Risks:

- privacy harm
- stale or inaccurate memory
- unbounded prompt growth

Verification strategy:

- memory service tests
- prompt assembly snapshot tests
- deletion tests
- consent behavior tests

Success criteria:

- long conversations stay within context budget
- memory facts are inspectable by metadata
- memory can be deleted
- prompt assembly remains backend-owned

## Phase 4: Hardware Trigger Integration

Goal: route Smart Cane and Smart Goggles Assist triggers into the same pipeline.

Scope:

- `HardwareAssistTriggerSource`
- mapping from resolved hardware events
- trigger normalizer rules
- dedupe/idempotency keys
- SOS preemption tests
- goggle camera capture adapter if hardware is ready

Dependencies:

- existing hardware event routing
- agreed hardware button mapping
- Phase 1 pipeline

Risks:

- bypassing event arbitration
- ambiguous button semantics
- multi-device media source conflicts

Verification strategy:

- fake hardware event tests
- arbitration integration test
- duplicate hardware event test
- SOS preemption test

Success criteria:

- hardware button uses same Assist turn path as UI
- hardware adapters do not call Assist APIs
- SOS always preempts Assist

## Phase 5: STT And Long Press

Goal: implement long press `STT -> Capture -> Analyze -> Speak`.

Scope:

- `SpeechInputPort`
- long-press trigger mapping
- transcript state handling
- no-speech and timeout behavior
- transcript persistence as user message

Dependencies:

- microphone permission
- STT plugin decision
- Phase 1 and Phase 2

Risks:

- unreliable speech recognition
- accessibility feedback gaps
- accidental audio retention

Verification strategy:

- fake STT tests
- timeout and no-speech tests
- manual long-press flow
- permission denial test

Success criteria:

- long press uses same pipeline
- transcript is persisted only as text
- raw audio is ephemeral
- user receives clear feedback on STT failure

## Phase 6: Foreground Service Readiness

Goal: make Assist hostable outside visible UI without implementing every background capability.

Scope:

- lifecycle-neutral `AssistRuntimeHost`
- runtime state observer
- notification-state model
- audio focus abstraction
- connectivity policy
- restart/recovery behavior

Dependencies:

- stable state machine
- cancellation semantics
- platform service planning

Risks:

- Android lifecycle complexity
- battery and OEM restrictions
- camera/microphone policy constraints

Verification strategy:

- non-widget runtime tests
- restart recovery tests
- cancellation/preemption tests
- platform spike documentation

Success criteria:

- Assist runtime can be invoked without a route
- state can be observed without widgets
- future service host has a clear contract

## Phase 7: Advanced Assist Capabilities

Goal: expand capability while preserving the same pipeline.

Scope:

- wake word source
- streaming responses
- multi-provider routing
- hardware microphone input
- backend transcription option
- richer hazard response
- offline or degraded local modes if product-approved

Dependencies:

- privacy/legal review
- foreground service foundation
- provider abstraction
- memory system

Risks:

- scope creep
- increased privacy burden
- provider cost
- inconsistent response quality

Verification strategy:

- provider contract tests
- streaming protocol tests
- wake word false-positive tests
- cost and latency dashboards

Success criteria:

- new triggers require no new Assist pipeline
- provider can change without Flutter rewrite
- streaming is additive to existing turn model
- background and foreground flows remain consistent

## Cross-Phase Rules

- Keep SOS preemption tested in every phase.
- Keep FastAPI as the source of truth for durable memory and provider execution.
- Keep Flutter capture and speech behind ports.
- Use idempotency for every turn.
- Add observability before adding background complexity.
- Do not store raw media by default.
