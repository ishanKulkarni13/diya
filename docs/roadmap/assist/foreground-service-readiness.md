# Foreground Service Readiness

Assist should be designed now so future foreground service support does not require a rewrite. This document does not propose implementing an Android foreground service immediately; it defines the boundaries needed before that work starts.

## What Is Already Ready

The Flutter codebase already has useful foundations:

- hardware orchestration is separated from UI screens
- device manager and event bus live under core hardware
- event arbitration has a resolved event stream
- safety ingress listens to hardware events outside normal button widgets
- session state is centralized
- queueing exists for safety writes
- backend contracts use versioned API routing

These patterns are compatible with foreground/background execution if Assist follows them.

## What Is Not Ready Yet

Missing pieces:

- lifecycle-neutral Assist runtime
- explicit bootstrap sequence for Assist dependencies
- capture ports that can run without screen route ownership
- speech ports with audio focus and interruption semantics
- foreground notification state model
- background-safe trigger source abstraction
- service-to-Flutter communication contract
- durable recovery model for in-flight turns
- battery/network policy for background work

## UI Dependencies To Avoid

Assist application and domain layers should not depend on:

- `BuildContext`
- route location
- widget lifecycle
- visible home screen state
- direct button callbacks as business logic
- plugin objects created only inside a widget

The presentation layer can bind to the runtime, but the runtime should not bind to presentation.

## Future Service Host

A future foreground service host should be able to:

- subscribe to hardware triggers
- keep selected device connections alive
- start Assist from a normalized trigger
- update a persistent notification with state
- cancel active Assist
- stop speech
- handle SOS preemption
- recover state after process death where platform allows

This suggests a host boundary:

```txt
AssistRuntimeHost
  start()
  stop()
  submitTrigger(trigger)
  cancelTurn(turnId)
  observeState()
```

Flutter UI and Android foreground service can both become hosts.

## Background Execution Constraints

Background Assist should be treated as a constrained mode:

- camera access may require foreground visibility or explicit platform handling
- microphone/wake word behavior has OS policy constraints
- long-running AI calls need visible user value and cancellation
- battery optimization can disrupt connectivity
- network loss is common
- privacy expectations are stricter when UI is not visible

Design now for clear failure and deferral instead of assuming every foreground flow can run in the background.

## Recovery Model

On app restart or service restart, Flutter should recover:

- active session id
- last known turn status from FastAPI
- whether speech was completed locally
- pending cancellation status
- recent response for repeat/stop controls

Do not depend on local memory as the only record of completed analysis. Backend turn state is the source of truth.

## Service-Compatible Ports

Ports should be usable from UI or service contexts:

```txt
ImageCapturePort
SpeechInputPort
SpeechOutputPort
AssistRepository
AssistTriggerSource
AssistRuntimeStore
ConnectivityPolicyPort
AudioFocusPort
NotificationStatusPort
```

Some implementations may be UI-only at first, but the port should not assume that.

## Design Decisions That Reduce Future Refactoring

- Keep Assist pipeline independent from routes.
- Keep TTS/STT behind ports from the first phase.
- Normalize hardware events before Assist execution.
- Put Gemini and prompt assembly in FastAPI.
- Use idempotency keys for every turn.
- Persist durable turn status in FastAPI.
- Model cancellation, interruption, and preemption explicitly.
- Treat foreground service as another runtime host, not another Assist implementation.

## Readiness Checklist

- One Assist runtime can be called by UI and non-UI trigger sources.
- Every active state can be cancelled or preempted.
- Runtime state can be observed without a widget.
- Backend can answer "what happened to this turn?"
- Media retention policy is explicit.
- Provider calls are idempotent at backend boundaries.
- Hardware trigger mapping does not bypass arbitration.
