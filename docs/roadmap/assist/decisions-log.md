# Architecture Decisions Log

This document records important architectural decisions for the Assist domain.

The goal is to preserve design reasoning and prevent future contributors from revisiting already-resolved decisions.

---

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

---

## ADR-002: Backend Owns Memory

Status: Accepted

Long-term memory is owned by FastAPI.

Flutter only stores:

- Current runtime state
- Current session state
- Temporary caches

Reason:

Supports:

- New devices
- Reinstalls
- Multi-device usage
- Future web clients

---

## ADR-003: Gemini Runs Only In Backend

Status: Accepted

Flutter never communicates directly with Gemini.

Flutter communicates only with Assist APIs.

Reason:

- Provider independence
- Security
- Prompt control
- Easier model replacement

---

## ADR-004: All Triggers Are Normalized

Status: Accepted

All trigger sources become AssistTriggers.

Examples:

- UI Button
- Hardware Button
- Voice Command
- Wake Word
- Foreground Service

Reason:

Avoid duplicated Assist logic.

---

## ADR-005: Images Are Ephemeral

Status: Accepted

Images captured for Assist are not stored permanently during MVP.

Reason:

- Privacy
- Lower storage requirements
- Simpler compliance

---

## ADR-006: Streaming Is Not MVP

Status: Accepted

The architecture should remain compatible with streaming.

Streaming is not part of the first implementation phase.

Reason:

Reduce complexity while validating the Assist pipeline.