import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../application/assist_controller.dart';
import '../application/assist_pipeline.dart';
import '../application/assist_policy_engine.dart';
import '../application/assist_trigger_normalizer.dart';
import '../domain/models/assist_state.dart';
import '../domain/ports/image_capture_port.dart';
import '../domain/ports/speech_output_port.dart';
import '../infrastructure/assist_api.dart';
import '../infrastructure/flutter_tts_adapter.dart';
import '../infrastructure/image_picker_adapter.dart';
import '../application/assist_ingress_service.dart';
import '../../../core/hardware/providers/hardware_providers.dart';

final assistApiProvider = Provider<AssistApi>((ref) {
  final dio = ref.watch(apiDioProvider);
  return AssistApi(dio);
});

final imageCapturePortProvider = Provider<ImageCapturePort>((ref) {
  return ImagePickerAdapter();
});

final speechOutputPortProvider = Provider<SpeechOutputPort>((ref) {
  return FlutterTtsAdapter();
});

final assistPolicyEngineProvider = Provider<AssistPolicyEngine>((ref) {
  return AssistPolicyEngine();
});

final assistTriggerNormalizerProvider = Provider<AssistTriggerNormalizer>((ref) {
  return AssistTriggerNormalizer();
});

final assistPipelineProvider = Provider<AssistPipeline>((ref) {
  return AssistPipeline(
    imageCapturePort: ref.watch(imageCapturePortProvider),
    speechOutputPort: ref.watch(speechOutputPortProvider),
    assistApi: ref.watch(assistApiProvider),
    policyEngine: ref.watch(assistPolicyEngineProvider),
  );
});

final assistControllerProvider = StateNotifierProvider<AssistController, AssistState>((ref) {
  return AssistController(
    pipeline: ref.watch(assistPipelineProvider),
    normalizer: ref.watch(assistTriggerNormalizerProvider),
    ref: ref,
  );
});

final assistIngressServiceProvider = Provider<AssistIngressService>((ref) {
  final service = AssistIngressService(
    eventRouter: ref.watch(eventRouterProvider),
    assistController: ref.watch(assistControllerProvider.notifier),
  );

  service.start();
  ref.onDispose(() => service.dispose());

  return service;
});
