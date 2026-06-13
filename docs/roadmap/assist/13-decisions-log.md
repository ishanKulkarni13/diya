# Assist Decisions Log

This file is the canonical decision record for the Assist roadmap package. It captures the architecture choices that should remain stable as implementation begins. A legacy unnumbered log exists in this folder, but this numbered file is the one to keep current.

## ADR-001: Assist Is A Dedicated Domain

Status: Accepted

Assist will be implemented as its own domain and feature.

It will not be merged into:

- Safety
- Home
- Hardware
- Session

Reason:

Assist has its own state machine, memory model, API contracts, triggers, and future roadmap.

## ADR-002: Backend Owns Memory

Status: Accepted

Long-term memory is owned by FastAPI.

Flutter only stores:

- current runtime state
- current session state
- temporary caches
- recent response data needed for local interaction

Reason:

Supports:

- new devices
- reinstalls
- multi-device usage
- future web clients

## ADR-003: Gemini Runs Only In Backend

Status: Accepted

Flutter never communicates directly with Gemini.

Flutter communicates only with Assist APIs.

Reason:

- provider independence
- security
- prompt control
- easier model replacement

## ADR-004: All Triggers Are Normalized

Status: Accepted

All trigger sources become `AssistTrigger` values and flow through one `AssistIntent`.

Examples:

- UI Button
- Hardware Button
- Voice Command
- Wake Word
- Foreground Service

Reason:

Avoid duplicated Assist logic.

## ADR-005: Images Are Ephemeral

Status: Accepted

Images captured for Assist are ephemeral by default.

Reason:

- privacy
- lower storage requirements
- simpler compliance

## ADR-006: Streaming Is Not MVP

Status: Accepted

The architecture should remain compatible with streaming.

Streaming is not part of the first implementation phase.

Reason:

Reduce complexity while validating the Assist pipeline.

## ADR-007: V1 Uses Multipart Image Uploads

Status: Accepted

The first Assist turn contract should use `multipart/form-data` for the image and request metadata.

Reason:

- one request, one response
- simpler Flutter and FastAPI integration
- avoids base64 overhead
- keeps upload-first media contracts for a later phase

## ADR-008: Phase 1 Uses A Mock Response

Status: Accepted

The first end-to-end Assist slice should prove capture, request routing, and speech output before Gemini integration.

Reason:

- reduces risk
- keeps the first slice small
- validates the contract before provider work

## ADR-009: Flutter To Backend Boundary Is AssistApi

Status: Accepted

The Flutter-side network boundary should be named `AssistApi`.

Reason:

- more accurate than repository naming
- consistent with the other network APIs
- keeps domain persistence repositories separate from HTTP access
