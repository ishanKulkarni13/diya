# Trigger Architecture

Assist must support many trigger sources without creating many Assist implementations. UI tap, long press, Smart Goggles button, Smart Cane button, wake word, foreground service event, and automation should all converge before capture, analysis, memory, and speech output begin.

## Design Principle

```txt
Raw trigger -> Trigger adapter -> Trigger normalizer -> AssistIntent -> Assist runtime
```

Only the trigger adapter is source-specific. Everything after normalization should be shared.

## Trigger Sources

Initial sources:

- UI single tap
- UI long press
- hardware button from resolved hardware events

Future sources:

- wake word detector
- voice command
- foreground service notification action
- background automation
- guardian or backend initiated assist request, if product-approved

## Recommended Components

### AssistTriggerSource

Port implemented by each source that can emit raw Assist triggers.

Examples:

```txt
UiAssistTriggerSource
HardwareAssistTriggerSource
WakeWordAssistTriggerSource
ForegroundServiceAssistTriggerSource
AutomationAssistTriggerSource
```

The source should not call Gemini, capture images, or write conversation memory.

### AssistTriggerNormalizer

Converts raw source events into `AssistTrigger` plus candidate `AssistIntent`.

Examples:

```txt
single tap -> describe_scene
long press -> answer_question_about_scene
hardware button tap -> describe_scene
hardware button long press -> answer_question_about_scene
wake word follow-up -> continue_conversation
```

The normalizer should attach trace metadata, source identity, and idempotency key.

### AssistPolicyEngine

Owns source-agnostic rules before a turn starts:

- dedupe window
- source priority
- SOS preemption
- whether to queue, reject, interrupt, or replace an active Assist turn
- camera selection policy
- network/offline policy
- whether follow-up mode is valid

This is preferable to spreading `if hardware`, `if voice`, and `if UI` checks across controllers.

### AssistPipeline

The single application service that runs the normalized intent through preflight, optional STT, capture, backend analysis, TTS, and completion.

The pipeline should depend on ports:

```txt
ImageCapturePort
SpeechInputPort
SpeechOutputPort
AssistApi
AssistRuntimeStore
AssistPolicyEngine
```

It should not depend on widgets or concrete hardware adapters.

## Hardware Integration

The existing hardware pipeline already separates concerns:

```txt
Device adapter -> HardwareEventBus -> EventRouter -> EventArbitrator -> resolved events
```

Assist should listen to resolved events, not raw bus events. This preserves arbitration and safety bypass behavior. Hardware adapters should remain device-specific translators and must not call Assist use cases directly.

Recommended flow:

```txt
Smart Cane / Smart Goggles
-> Adapter emits HardwareEvent
-> HardwareEventBus
-> EventRouter / EventArbitrator
-> HardwareAssistTriggerSource
-> AssistTriggerNormalizer
-> AssistPipeline
```

## Dedupe and Idempotency

Every normalized trigger should carry an idempotency key. Good inputs include:

- source type
- device id
- hardware event id if available
- timestamp bucket
- press type
- active session id

Flutter uses this to suppress duplicate local execution. FastAPI uses the same key to prevent duplicate turn persistence and duplicate provider calls.

## Preemption Rules

Priority order:

```txt
SOS / safety-critical
cancel assist
stop speaking
active user assist command
background automation
diagnostics / debug
```

SOS always wins. Assist should release camera, microphone, speech, and in-flight requests as quickly as platform APIs allow.

## What Not To Do

- Do not put Assist API calls inside button widgets.
- Do not let Smart Cane or Smart Goggles adapters know about conversation memory.
- Do not create separate state machines for tap, long press, and hardware button.
- Do not let wake word handling bypass the normal Assist policy layer.
- Do not treat foreground service triggers as a later special case; model them as another trigger source now.
