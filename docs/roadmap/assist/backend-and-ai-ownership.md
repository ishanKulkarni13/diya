# Backend And AI Ownership

FastAPI should own the intelligent and durable parts of Assist. Flutter should provide local interaction and media capture, then call stable backend contracts.

## FastAPI Responsibilities

FastAPI should own:

- Assist session and turn persistence
- idempotency enforcement for turns
- conversation history
- user profile memory
- memory summaries and summarization jobs
- prompt assembly
- provider selection
- Gemini integration
- future AI provider integrations
- response shaping
- safety and content policy mapping
- audit metadata
- retention and deletion workflows

This mirrors the existing backend pattern where auth and safety are first-class modules under `backend/api/app/modules`.

## What Should Not Live In Flutter

Flutter should not own:

- Gemini API keys
- provider SDK calls
- prompt templates
- long-term memory retrieval
- memory summarization
- provider routing
- content policy transformation
- durable conversation persistence
- AI model names as business logic

Flutter may keep configuration flags for feature availability and endpoint behavior, but backend remains the source of truth for AI execution.

## Recommended Backend Module

```txt
backend/api/app/modules/assist/
  router.py
  service.py
  repository.py
  models.py
  schemas.py
  providers/
    base.py
    gemini.py
  memory/
    service.py
    repository.py
  prompts/
    builder.py
    templates.py
```

Keep this structure flexible. If memory grows into a broader platform capability, it can become `app/modules/memory` later while Assist keeps a memory port.

## Provider Abstraction

Introduce an AI provider port before calling Gemini directly:

```txt
AssistAiProvider
  analyze_turn(context) -> ProviderAssistResult
  stream_turn(context) -> AsyncIterator[ProviderAssistDelta]
```

Provider adapters should translate backend-neutral context into provider-specific calls. Application services should consume normalized results.

## Gemini V1 Recommendation

Use the official Google Gen AI SDK from the FastAPI backend. Use a Flash-class multimodal Gemini model for V1 because Assist needs image understanding, low latency, and a path to streaming. Keep the exact model name configuration-driven so upgrades do not require Flutter releases.

The backend should record:

```txt
provider
model
request_id
latency_ms
token_usage
finish_reason
safety_ratings
error_code
```

## Avoiding Vendor Lock-In

Vendor lock-in is avoided by:

- stable Assist request/response contracts
- provider-neutral domain models
- provider adapter registry
- backend-owned prompt builder
- normalized provider errors
- model configuration outside Flutter
- provider run metadata stored separately from conversation messages

Do not expose provider-specific fields to Flutter unless they are placed under an explicit diagnostic metadata object.

## Response Shaping

FastAPI should return speech-ready text and optional display text. Assistive UX requires concise responses by default, but response style should be configurable by user preference and context.

Response shape should include:

- spoken response
- optional display text
- confidence and uncertainty
- hazards or urgent observations
- follow-up eligibility
- suggested next action only when product-approved
- provider metadata for diagnostics

## Reliability Requirements

Backend Assist services should support:

- request id and trace id
- idempotency keys
- bounded provider timeouts
- retry only where safe
- structured error codes
- graceful degradation when memory retrieval fails
- provider circuit breaker in later phases
- observability for prompt assembly and provider latency

## Security Requirements

- Never return provider secrets to Flutter.
- Store media references with retention class.
- Encrypt retained media.
- Limit prompt logging.
- Apply access control by authenticated user id.
- Design deletion paths before broad memory persistence.

## Challenge To Current Direction

A single `AssistOrchestrator` can become a large object that owns everything. Prefer a thin facade over smaller services:

```txt
AssistService
AssistTurnService
MemoryContextService
PromptBuilder
AiProviderRegistry
ResponseShaper
RetentionPolicyService
```

This keeps testing and replacement easier as provider and memory behavior grows.
