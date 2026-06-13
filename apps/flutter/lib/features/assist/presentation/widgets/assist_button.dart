import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/models/assist_state.dart';
import '../../domain/models/assist_trigger.dart';
import '../../providers/assist_providers.dart';

class AssistButton extends ConsumerWidget {
  const AssistButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(assistControllerProvider);

    return Semantics(
      label: 'Get Assistance',
      hint: 'Takes a picture and describes the scene',
      button: true,
      child: ElevatedButton(
        onPressed: state.isBusy
            ? null
            : () {
                final trigger = AssistTrigger.create(
                  sourceType: AssistTriggerSourceType.uiButton,
                  pressType: AssistPressType.tap,
                );
                ref.read(assistControllerProvider.notifier).triggerAssist(trigger);
              },
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 24),
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          foregroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
        ),
        child: _buildChild(context, state),
      ),
    );
  }

  Widget _buildChild(BuildContext context, AssistState state) {
    if (state.isBusy) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 3),
          ),
          const SizedBox(width: 16),
          Text(
            _getStatusText(state),
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
        ],
      );
    }

    return const Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.camera_alt, size: 32),
        SizedBox(width: 16),
        Text(
          'Assist',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  String _getStatusText(AssistState state) {
    if (state.isCapturing) return 'Capturing...';
    if (state.isAnalyzing) return 'Analyzing...';
    if (state.isSpeaking) return 'Speaking...';
    return 'Processing...';
  }
}
