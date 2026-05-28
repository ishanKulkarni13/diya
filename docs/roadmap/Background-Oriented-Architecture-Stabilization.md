# Background-Oriented Architecture Stabilization Roadmap

This roadmap is intentionally loose. It defines themes and goals to prepare the codebase for foreground/background services without prescribing strict sequencing.

## Why This Roadmap Exists

We are not implementing the Android foreground service yet. This roadmap is about making the architecture ready for it: lifecycle safety, deterministic orchestration, and observability that will survive background execution.

## Guiding Principles

- Prefer clarity over cleverness; avoid hidden coupling.
- Make device orchestration deterministic before making it always-on.
- Keep UI passive; move long-lived work into stable services.
- Measure failure modes before scaling feature breadth.

## Theme 1: Lifecycle-Safe Bootstrap

Goal: the system should recover its full device context and safety state after app restart or background resume.

Do this when ready:
- Add a bootstrap layer that explicitly sequences session validation, device registry load, and device reconnects.
- Add a single point to rehydrate device state (known devices, last known connection, safety queue state).
- Ensure that any long-lived provider has explicit disposal and restart semantics.

Signals of completion:
- App restart re-attaches to known devices without manual UI steps.
- Safety queue resumes after session refresh.

## Theme 2: Deterministic Device Orchestration

Goal: device orchestration should be stable under intermittent network, process death, and partial device availability.

Do this when ready:
- Add explicit "lost" state after bounded retry attempts.
- Make reconnect policy observable (attempt count, last reason, next retry).
- Add one orchestration loop that can be reused later by the foreground service.

Signals of completion:
- Device failures do not create infinite retry loops.
- User can see when a device is lost vs temporarily down.

## Theme 3: Observability Before Always-On

Goal: every failure path should be traceable before background services are enabled.

Do this when ready:
- Add structured logs for event arbitration (winner, suppressed, reason).
- Standardize correlation IDs across device commands and safety events.
- Make diagnostics viewable in debug UI (last error, last retry, trace ID).

Signals of completion:
- Event arbitration decisions are inspectable.
- Safety and device actions have trace IDs visible to the team.

## Theme 4: Background Service Preparation (Not Implementation)

Goal: make the Flutter code ready to be hosted by a foreground service later.

Do this when ready:
- Define the service contract (what the service owns and what Flutter owns).
- Identify all dependencies that assume UI foreground (timers, streams, controllers).
- Plan the minimal service responsibilities (keepalive, reconnect loop, BLE lifecycle).

Signals of completion:
- Background dependencies are explicitly listed and isolated.
- A clear service handoff boundary exists.

## Explicit "Not Now"

These are intentionally deferred to keep scope realistic:

- BLE transport implementation for Smart Cane (we will integrate later).
- Rate limiting and backpressure controls on device discovery server.
- WebSocket or realtime streaming for guardian notifications.
- Full foreground service implementation and OEM battery handling.

## Risks If We Skip This Roadmap

- Foreground service integration will be messy and unsafe.
- Background reconnection will be unreliable and battery-draining.
- Debugging safety failures will be slow and inconsistent.

## Exit Criteria (Loose)

We can move to foreground service implementation when:
- Device orchestration survives app restart without UI involvement.
- Safety queue and device events recover deterministically.
- Observability can trace a device action end-to-end.

## Next Steps

Pick any theme and implement one slice end-to-end. Then return to this roadmap and adjust priorities based on what you learn.
