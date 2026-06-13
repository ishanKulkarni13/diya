import 'package:uuid/uuid.dart';

enum AssistTriggerSourceType {
  uiButton,
  hardwareButton,
  voiceCommand,
  wakeWord,
  foregroundService,
  automation,
  unknown
}

enum AssistPressType { tap, longPress, doublePress, unknown }

/// Represents the raw source event that initiated Assist.
class AssistTrigger {
  const AssistTrigger({
    required this.triggerId,
    required this.sourceType,
    required this.occurredAt,
    this.sourceDeviceId,
    this.pressType = AssistPressType.unknown,
    this.confidence = 1.0,
    required this.idempotencyKey,
    this.rawEventRef,
  });

  final String triggerId;
  final AssistTriggerSourceType sourceType;
  final String? sourceDeviceId;
  final AssistPressType pressType;
  final DateTime occurredAt;
  final double confidence;
  final String idempotencyKey;
  final String? rawEventRef;

  factory AssistTrigger.create({
    required AssistTriggerSourceType sourceType,
    String? sourceDeviceId,
    AssistPressType pressType = AssistPressType.unknown,
    double confidence = 1.0,
    String? idempotencyKey,
    String? rawEventRef,
  }) {
    final now = DateTime.now();
    return AssistTrigger(
      triggerId: const Uuid().v4(),
      sourceType: sourceType,
      sourceDeviceId: sourceDeviceId,
      pressType: pressType,
      occurredAt: now,
      confidence: confidence,
      idempotencyKey: idempotencyKey ?? const Uuid().v4(),
      rawEventRef: rawEventRef,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'trigger_id': triggerId,
      'source_type': _sourceTypeToString(sourceType),
      'source_device_id': sourceDeviceId,
      'press_type': _pressTypeToString(pressType),
      'occurred_at': occurredAt.toIso8601String(),
      'confidence': confidence,
      'idempotency_key': idempotencyKey,
      'raw_event_ref': rawEventRef,
    };
  }

  String _sourceTypeToString(AssistTriggerSourceType type) {
    switch (type) {
      case AssistTriggerSourceType.uiButton: return 'ui_button';
      case AssistTriggerSourceType.hardwareButton: return 'hardware_button';
      case AssistTriggerSourceType.voiceCommand: return 'voice_command';
      case AssistTriggerSourceType.wakeWord: return 'wake_word';
      case AssistTriggerSourceType.foregroundService: return 'foreground_service';
      case AssistTriggerSourceType.automation: return 'automation';
      case AssistTriggerSourceType.unknown: return 'unknown';
    }
  }

  String _pressTypeToString(AssistPressType type) {
    switch (type) {
      case AssistPressType.tap: return 'tap';
      case AssistPressType.longPress: return 'long_press';
      case AssistPressType.doublePress: return 'double_press';
      case AssistPressType.unknown: return 'unknown';
    }
  }
}
