# Memory Architecture

Assist should feel persistent without making Flutter the source of truth for memory. Memory must be reliable, inspectable, privacy-aware, and independent of the current mobile runtime.

## Memory Types

### Conversation

Purpose: durable container for user-assistant turns.

Owner: FastAPI and PostgreSQL.

Flutter role: cache the active conversation/session id and optionally recent visible messages for responsiveness.

Persistence: durable until retention policy closes, expires, or deletes it.

### ConversationMessage

Purpose: stores user transcript, assistant response, structured metadata, and references to media used for a turn.

Owner: FastAPI.

Flutter role: send final transcript and media reference; render/speak response.

Persistence: durable text and metadata. Raw media is not durable by default.

### UserProfileMemory

Purpose: stores user-specific stable facts and preferences that improve assistance.

Examples:

```txt
preferred_language
response_verbosity
navigation_priority
uses_smart_cane
uses_smart_goggles
memory_enabled
known_mobility_aids
home_work_context
frequent_routes
object_person_labels
accessibility_preferences
```

Owner: FastAPI.

Flutter role: collect explicit user preferences and consent decisions.

Persistence: durable, user-editable, and deletable.

UserProfileMemory is different from conversation history and memory summaries:

- Conversation history records what happened turn by turn.
- Memory summaries compress older conversation history into a bounded recall layer.
- UserProfileMemory stores stable user preferences and long-lived settings that should influence future turns even when the original conversation is gone.

### MemorySummary

Purpose: compact long conversation history into a bounded context representation.

Owner: FastAPI.

Flutter role: none beyond displaying history or deletion controls if product scope includes them.

Persistence: durable summary linked to conversation/user and model version.

### AssistSession

Purpose: runtime-oriented grouping of active Assist turns.

Owner: FastAPI as durable source of truth; Flutter as active runtime holder.

Persistence: persist status and timestamps. Flutter active session id is cacheable and recoverable.

## What Belongs In Flutter

- active Assist session id
- active turn state
- most recent assistant response for repeat/stop speaking
- recent conversation cache for UI responsiveness
- local speech/capture state
- explicit user preference inputs before sync
- media handles and upload references
- transient consent capture before backend sync

Flutter should not store long-term user memory, full prompt history, provider secrets, or durable memory summaries.

## What Belongs In FastAPI

- conversation records
- conversation messages
- user profile memory
- memory summaries
- prompt assembly
- retrieval policy
- summarization jobs
- provider run metadata
- retention and deletion policy enforcement

## What Belongs In PostgreSQL

Recommended tables:

```txt
assist_sessions
assist_turns
conversation_messages
memory_summaries
user_memory_facts
media_attachments
ai_runs
```

PostgreSQL should store metadata, transcripts, responses, summaries, policy state, and references. Raw images/audio should use temporary encrypted object storage when needed, not database blobs.

## Ephemeral Data

Keep ephemeral by default:

- raw microphone audio
- partial STT transcripts
- raw camera frames
- full provider prompt text
- provider streaming deltas after final response is assembled
- failed capture buffers

Ephemeral data may be retained temporarily only for retry, async processing, or opted-in diagnostics.

## Long Conversations

Long conversations should use layered context:

```txt
recent turns window
conversation summary
relevant user memory facts
current turn transcript and image
current device/location-safe metadata
policy instructions
```

The recent window should be bounded by token and latency budgets. Summaries should be refreshed after meaningful turn count or token thresholds, not on every request.

## Summarization

Summaries should include:

- stable facts learned during conversation
- unresolved user goals
- recent environmental context only when still useful
- assistant commitments
- safety-relevant preferences

Summaries should avoid:

- speculative facts
- raw sensitive content not needed for future help
- stale scene details
- private information inferred without user consent

Summaries need metadata:

```txt
summary_id
conversation_id
user_id
source_turn_range
model
created_at
expires_at
confidence
privacy_class
```

## Gemini Context Assembly

FastAPI should assemble Gemini context in this order:

1. system and safety instructions
2. user accessibility preferences
3. relevant user memory facts
4. current conversation summary
5. recent turns
6. current user question or inferred intent
7. current image/media reference
8. response shaping instructions

Flutter should never build provider-specific prompts. It should send structured context inputs and let FastAPI own provider formatting.

## Privacy Requirements

- Ask for explicit consent before durable user memory.
- Support user-visible deletion of conversation and memory.
- Separate raw media retention from transcript retention.
- Encrypt media at rest whenever retained.
- Keep provider inputs auditable by metadata without exposing secrets.
- Avoid storing location unless product and consent requirements are clear.
