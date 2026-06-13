# Assist Architecture Overview

Assist is the multimodal guidance flow for Diya. It should let a visually impaired user ask for immediate environmental help through a tap, long press, hardware button, wake word, or future background trigger.

## Product Flows

```txt
Single tap
Capture -> Analyze -> Speak

Long press
STT -> Capture -> Analyze with question -> Speak

Future hardware / wake word / foreground service
Normalize trigger -> Same Assist pipeline
```

## Current System Fit

The current Flutter app already has production-oriented building blocks:

- Riverpod provider composition
- GoRouter session-aware routing
- secure session repository and token refresh flow
- safety controller and SOS ingress service
- local safety queueing
- hardware device manager, registry, adapter factory, event bus, event router, and event arbitrator
- debug tooling for devices and safety

The current FastAPI backend has:

- versioned `/api/v1` router
- auth module
- safety module
- SQLAlchemy models and Alembic migrations
- idempotent safety event persistence
- standard error handling foundation

Assist should extend these patterns instead of replacing them.

## High-Level Architecture

```txt
Flutter trigger sources
-> AssistTriggerNormalizer
-> AssistPolicyEngine
-> AssistPipeline
-> capture / STT / repository / TTS ports
-> FastAPI Assist module
-> memory context
-> prompt builder
-> AI provider adapter
-> response shaper
-> Flutter speech output
```

## Flutter Ownership

Flutter owns:

- trigger collection
- gesture handling
- hardware event subscription after arbitration
- camera capture
- local STT
- local TTS
- active runtime state
- cancellation and speech interruption
- accessibility feedback
- short-lived cache

## FastAPI Ownership

FastAPI owns:

- Assist sessions
- Assist turns
- conversation history
- user memory
- memory summaries
- prompt assembly
- Gemini/provider integration
- provider routing
- response shaping
- durable audit metadata
- media retention policy

## Hardware Ownership

Hardware remains a source of events and media. It should not own Assist business logic.

Smart Cane and Smart Goggles should continue to flow through:

```txt
adapter -> event bus -> event router -> arbitrator -> resolved event
```

Assist should consume resolved events and normalize them to `AssistTrigger`.

## Safety Ownership

Safety workflows outrank Assist. SOS should preempt Assist in every active state. Assist must not delay safety event routing, safety queue writes, or emergency UX.

## Architectural Quality Target

The desired architecture should be:

- maintainable: small ports, clear ownership, no provider-specific Flutter logic
- scalable: multiple trigger sources and AI providers without new pipelines
- testable: fake capture, fake STT/TTS, fake repository, fake trigger sources
- reliable: idempotency, cancellation, timeouts, preemption, trace ids
- future-proof: foreground service host can reuse the same runtime contracts

## Main Recommendation

Build Assist as a dedicated feature and backend module, but keep the runtime pipeline lifecycle-neutral. That means the pipeline can be invoked from a widget today and from a foreground service tomorrow without changing domain or API contracts.
