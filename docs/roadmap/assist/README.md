# Assist Roadmap Package

This package defines the Assist architecture roadmap for Diya (2ndEye). It is planning documentation only; it does not introduce Flutter or FastAPI implementation code.

Assist is expected to become the shared pipeline for UI taps, long press question flow, hardware buttons, wake words, foreground service triggers, and future automation. The documents in this folder keep that pipeline aligned with the existing Flutter, FastAPI, safety, queueing, and hardware orchestration architecture.

## Reading Order

1. [architecture-overview.md](architecture-overview.md)
2. [domain-model.md](domain-model.md)
3. [state-machine.md](state-machine.md)
4. [trigger-architecture.md](trigger-architecture.md)
5. [memory-architecture.md](memory-architecture.md)
6. [backend-and-ai-ownership.md](backend-and-ai-ownership.md)
7. [api-contracts.md](api-contracts.md)
8. [flutter-runtime-architecture.md](flutter-runtime-architecture.md)
9. [foreground-service-readiness.md](foreground-service-readiness.md)
10. [risks-and-open-decisions.md](risks-and-open-decisions.md)
11. [implementation-roadmap.md](implementation-roadmap.md)

## Non-Goals

- Do not implement Assist feature code as part of this roadmap package.
- Do not move Gemini prompt assembly, long-term memory, or provider secrets into Flutter.
- Do not create separate Assist pipelines for UI, hardware, wake word, or background triggers.
- Do not treat foreground service support as an Android-only detail; it affects domain boundaries, cancellation, idempotency, and runtime ownership.

## Architecture Position

Assist should be a dedicated product domain, not a convenience method inside home, safety, or hardware modules. Flutter should own local interaction, capture, speech input/output, trigger normalization, and short-lived runtime state. FastAPI should own durable conversation state, user memory, prompt assembly, AI provider selection, response shaping, and audit metadata.

The central design rule is:

```txt
Many trigger sources -> one normalized AssistIntent -> one Assist pipeline -> one backend turn contract
```

This keeps the system maintainable as Diya adds Smart Goggles, Smart Cane triggers, wake words, foreground services, streaming responses, and multiple AI providers.
