class CaneMessageDto {
  final int version;
  final String type;
  final Map<String, dynamic> payload;

  CaneMessageDto({
    required this.version,
    required this.type,
    required this.payload,
  });

  factory CaneMessageDto.fromJson(Map<String, dynamic> json) {
    if (!json.containsKey('v') || !json.containsKey('t')) {
      throw const FormatException('Missing required fields: v or t');
    }
    
    final version = json['v'];
    if (version is! int) {
      throw const FormatException('Field "v" must be an integer');
    }

    final type = json['t'];
    if (type is! String) {
      throw const FormatException('Field "t" must be a string');
    }

    return CaneMessageDto(
      version: version,
      type: type,
      payload: json,
    );
  }
}
