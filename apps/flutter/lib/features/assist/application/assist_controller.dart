import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_error.dart';
import '../../safety/models/safety_state.dart';
import '../../safety/providers/safety_controller.dart';
import '../domain/models/assist_state.dart';
import '../domain/models/assist_trigger.dart';
import 'assist_pipeline.dart';
import 'assist_trigger_normalizer.dart';

class AssistController extends StateNotifier<AssistState> {
  AssistController({
    required AssistPipeline pipeline,
    required AssistTriggerNormalizer normalizer,
    required Ref ref,
  })  : _pipeline = pipeline,
        _normalizer = normalizer,
        _ref = ref,
        super(const AssistState());

  final AssistPipeline _pipeline;
  final AssistTriggerNormalizer _normalizer;
  final Ref _ref;

  Future<void> triggerAssist(AssistTrigger trigger) async {
    if (state.isBusy) {
      // Ignore if already running
      return;
    }

    state = state.copyWith(status: AssistStatus.capturing, error: null);

    final intent = _normalizer.normalize(trigger);
    
    // Check safety state
    final safetyController = _ref.read(safetyControllerProvider);
    final isSafetyActive = safetyController.state.status != SafetyStatus.idle && safetyController.state.status != SafetyStatus.failed;

    try {
      final response = await _pipeline.executeTurn(
        trigger: trigger,
        intent: intent,
        isSafetyActive: isSafetyActive,
        onProgress: (status) {
          state = state.copyWith(status: status);
        },
      );
      
      state = state.copyWith(
        status: AssistStatus.idle,
        lastResponseText: response.displayText,
      );
    } on AppError catch (e) {
      state = state.copyWith(status: AssistStatus.error, error: e);
    } catch (e) {
      state = state.copyWith(
        status: AssistStatus.error,
        error: AppError.unknown(e.toString()),
      );
    }
  }
}
