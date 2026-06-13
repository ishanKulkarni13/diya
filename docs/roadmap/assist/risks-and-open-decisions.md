# Risks And Open Decisions

Assist touches accessibility, hardware, AI, privacy, and background execution. The risks below should be resolved or consciously accepted before implementation expands beyond a vertical slice.

## High Risks

### Duplicated Pipelines

Risk: UI tap, long press, hardware button, and wake word each grow their own logic.

Impact: inconsistent behavior, duplicate API calls, harder testing, foreground service rewrite.

Mitigation: normalize every trigger into `AssistIntent` and run one `AssistPipeline`.

### Memory Privacy

Risk: durable user memory stores sensitive inferred facts without consent or deletion controls.

Impact: user harm, compliance risk, loss of trust.

Mitigation: explicit consent, memory classes, deletion policy, user-visible settings, backend ownership.

### SOS Competition

Risk: Assist capture, analysis, or speech blocks emergency workflows.

Impact: safety-critical failure.

Mitigation: SOS preemption in policy engine and state machine, immediate resource release, tests for every active state.

### Provider Coupling

Risk: Flutter or domain code becomes Gemini-specific.

Impact: vendor lock-in and difficult model/provider migration.

Mitigation: backend provider adapter, normalized response, config-driven model selection.

### Foreground Service Rewrite

Risk: Assist depends on widgets and routes.

Impact: background execution requires a new runtime.

Mitigation: lifecycle-neutral runtime, ports for capture/speech/repository, service-host abstraction.

## Medium Risks

### Media Retention Drift

Risk: images and audio are retained longer than intended for debugging or retries.

Mitigation: retention class on every media attachment, encrypted temporary storage, deletion jobs.

### Latency

Risk: capture, upload, Gemini analysis, and TTS create a slow assistive interaction.

Mitigation: Flash-class model, bounded image sizes, streaming path, local state feedback, provider latency metrics.

### Offline Behavior

Risk: user expects Assist to work without network.

Mitigation: define offline UX early. V1 can fail gracefully with spoken feedback; later phases can add limited offline capabilities.

### Multi-Device Ambiguity

Risk: phone and goggle cameras compete or capture different scenes.

Mitigation: camera selection policy, device health, explicit source metadata, fallback rules.

### Long Conversation Quality

Risk: context grows unbounded or summaries become stale.

Mitigation: recent-window plus summary strategy, summary metadata, refresh thresholds.

## Low Risks

### Route Surface

Risk: Assist visible history needs navigation changes.

Mitigation: keep execution route-independent; add routes only for optional history/settings surfaces.

### Debug Metadata Exposure

Risk: provider diagnostics leak into production UI.

Mitigation: diagnostic metadata object and debug-only surfaces.

## Open Human Decisions

- What is the default language and response verbosity for V1?
- Should raw images ever be retained for diagnostics, and under what consent?
- Should audio be retained at all?
- What is the V1 offline message and retry behavior?
- Should follow-up questions remain active for seconds, minutes, or until session closure?
- Which camera is preferred when both phone and Smart Goggles are available?
- Are guardian-triggered Assist requests allowed, or is Assist always user-initiated?
- What memory facts can be stored automatically versus requiring explicit confirmation?
- Should users be able to inspect and edit remembered facts in V1?
- What is the acceptable end-to-end latency target for single tap and long press?
- Which Android foreground-service responsibilities are in the first background milestone?

## Assumptions To Challenge

- TTS in Flutter is likely correct for V1, but backend-generated audio may become useful for consistent voice or streaming later.
- STT in Flutter is likely correct for long press, but wake word and hardware microphone support may require a different implementation.
- Gemini should be backend-owned, but provider response streaming may require a WebSocket or server-sent event design sooner than expected.
- Conversation memory improves UX only if users understand and control what is remembered.
