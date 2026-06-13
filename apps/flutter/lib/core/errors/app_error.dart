enum AppErrorType { auth, network, permission, safety, assist, unknown }

class AppError implements Exception {
  const AppError({
    required this.type,
    required this.message,
    this.code,
    this.retryable = false,
  });

  final AppErrorType type;
  final String message;
  final String? code;
  final bool retryable;

  factory AppError.auth(String message, {String? code, bool retryable = false}) {
    return AppError(type: AppErrorType.auth, message: message, code: code, retryable: retryable);
  }

  factory AppError.network(String message, {String? code, bool retryable = true}) {
    return AppError(type: AppErrorType.network, message: message, code: code, retryable: retryable);
  }

  factory AppError.permission(String message, {String? code, bool retryable = false}) {
    return AppError(type: AppErrorType.permission, message: message, code: code, retryable: retryable);
  }

  factory AppError.safety(String message, {String? code, bool retryable = false}) {
    return AppError(type: AppErrorType.safety, message: message, code: code, retryable: retryable);
  }

  factory AppError.assist(String message, {String? code, bool retryable = false}) {
    return AppError(type: AppErrorType.assist, message: message, code: code, retryable: retryable);
  }

  factory AppError.unknown(String message, {String? code, bool retryable = false}) {
    return AppError(type: AppErrorType.unknown, message: message, code: code, retryable: retryable);
  }

  @override
  String toString() => 'AppError(type: $type, code: $code, retryable: $retryable, message: $message)';
}