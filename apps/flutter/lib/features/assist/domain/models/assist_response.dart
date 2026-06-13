/// Normalized response returned by FastAPI and consumed by Flutter.
class AssistResponse {
  const AssistResponse({
    required this.turnId,
    required this.sessionId,
    required this.status,
    required this.spokenText,
    required this.displayText,
    this.confidence,
    this.followUpMode,
    this.detectedObjects = const [],
    this.hazards = const [],
    this.providerName,
    this.modelName,
    this.latencyMs,
  });

  final String turnId;
  final String sessionId;
  final String status;
  final String spokenText;
  final String displayText;
  final double? confidence;
  final String? followUpMode;
  final List<String> detectedObjects;
  final List<String> hazards;
  final String? providerName;
  final String? modelName;
  final int? latencyMs;

  factory AssistResponse.fromJson(Map<String, dynamic> json) {
    final data = json['data'] as Map<String, dynamic>? ?? json;
    final responseData = data['response'] as Map<String, dynamic>? ?? {};
    final providerData = data['provider'] as Map<String, dynamic>? ?? {};

    return AssistResponse(
      turnId: data['turn_id'] as String? ?? '',
      sessionId: data['session_id'] as String? ?? '',
      status: data['status'] as String? ?? '',
      spokenText: responseData['spoken_text'] as String? ?? '',
      displayText: responseData['display_text'] as String? ?? '',
      confidence: (responseData['confidence'] as num?)?.toDouble(),
      followUpMode: responseData['follow_up_mode'] as String?,
      detectedObjects: (responseData['detected_objects'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      hazards: (responseData['hazards'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      providerName: providerData['name'] as String?,
      modelName: providerData['model'] as String?,
      latencyMs: providerData['latency_ms'] as int?,
    );
  }
}
