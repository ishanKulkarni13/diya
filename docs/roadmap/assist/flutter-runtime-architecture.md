# Flutter Runtime Architecture

Flutter should provide the local Assist experience while keeping durable intelligence and memory in FastAPI. The app already uses Riverpod providers, GoRouter navigation, feature folders, hardware domain/infrastructure layers, session control, queueing, and safety workflows. Assist should fit into those patterns instead of introducing a second architecture.

## Recommended Feature Boundary

```txt
apps/flutter/lib/features/assist/
  presentation/
  application/
  domain/
  infrastructure/
```

### Presentation

Responsibilities:

- Assist button and gesture handling
- progress affordances for capture, analysis, speech, failure, and cancellation
- accessible spoken and haptic feedback
- screen-reader friendly labels and state changes
- optional conversation surface when product scope requires visible history

Presentation should dispatch trigger events or user commands. It should not call camera, Gemini, or repository methods directly.

### Application

Responsibilities:

- `AssistController`
- `AssistPipeline`
- `AssistTriggerNormalizer`
- `AssistPolicyEngine`
- use cases such as `StartAssistTurn`, `CancelAssistTurn`, `RepeatLastResponse`, `StopSpeaking`
- runtime state exposure through Riverpod

This layer owns live state transitions and coordinates ports.

### Domain

Responsibilities:

- `AssistTrigger`
- `AssistIntent`
- `AssistSession`
- `AssistTurn`
- `AssistContext`
- `AssistResponse`
- `AssistState`
- value objects for source type, media reference, follow-up mode, and failure reason

Domain objects must not depend on Flutter widgets, Dio, camera plugins, speech plugins, or platform services.

### Infrastructure

Responsibilities:

- `AssistApi`
- `HttpAssistApi`
- phone camera capture adapter
- goggle camera capture adapter
- Flutter TTS adapter
- Flutter STT adapter
- secure/local runtime cache where needed
- foreground-service bridge adapter in later phases

Infrastructure implements ports declared by application/domain layers.

## Providers

Recommended provider groups:

```txt
assistControllerProvider
assistPipelineProvider
assistPolicyEngineProvider
assistTriggerNormalizerProvider
assistApiProvider
imageCapturePortProvider
speechInputPortProvider
speechOutputPortProvider
assistRuntimeStoreProvider
hardwareAssistTriggerSourceProvider
```

Providers should be lifecycle-aware and disposable. Long-lived providers must define explicit restart semantics for future foreground service hosting.

## Camera Capture

Flutter should own capture execution because the camera is local to the device or attached hardware. It should send FastAPI an image upload or media reference, not a provider-specific AI prompt.

Camera selection should be policy-driven:

```txt
preferred source
available source
last known device health
latency budget
privacy policy
fallback source
```

Phone camera and goggle camera should both implement `ImageCapturePort`.

## TTS Placement

TTS belongs in Flutter for V1 because speech output is device-local, latency-sensitive, and tied to accessibility settings.

Best practices:

- expose TTS through `SpeechOutputPort`
- support stop/interruption
- report start, completion, and failure
- avoid storing spoken audio
- respect system accessibility volume and audio focus where possible
- make TTS callable from a foreground service host later

## STT Placement

STT belongs in Flutter for the proposed long-press UX because microphone capture is local and user-permissioned. It should still be abstracted behind `SpeechInputPort` so later phases can switch to backend transcription, streaming transcription, or hardware microphone input.

Best practices:

- require explicit consent and visible/listenable feedback
- handle no-speech, timeout, permission denied, and partial transcript states
- keep raw audio ephemeral by default
- persist final transcript only through FastAPI when it becomes part of an Assist turn

## Queueing

The existing queue repository is safety-focused and should not become a generic Assist job queue without review. Assist needs its own runtime queue semantics for duplicate triggers and active-turn serialization. Durable offline Assist queueing is a separate product decision because AI analysis may require fresh media and network access.

## Navigation

Assist should not require route changes for core execution. The home screen can host the button and state indicators, while the pipeline remains independent of GoRouter. This is important for hardware triggers and future background execution.

## Current Extension Points

- `SecondEyeApp` already performs app-level eager provider reads for safety bootstrap.
- `appRouterProvider` already reacts to session state.
- `hardware_providers.dart` already exposes device manager, event bus, event router, and arbitration.
- `SosIngressService` already listens to resolved hardware events for safety workflows.
- `ApiClient`, `AuthApi`, and `SafetyApi` establish the backend adapter pattern.
- `AssistApi` should follow the same pattern as the existing network APIs.

Assist should add parallel providers and APIs without changing safety ownership.

## Testability

Assist should be testable without camera, microphone, TTS, real devices, or Gemini by replacing ports:

- fake image capture
- fake speech input
- fake speech output
- fake Assist API
- fake trigger source
- fake policy engine clock

State-machine tests should cover every trigger source through the same pipeline.
