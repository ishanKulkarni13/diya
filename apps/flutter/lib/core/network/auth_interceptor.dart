import 'package:dio/dio.dart';
import '../session/session_controller.dart';

/// Proactively attaches `Authorization: Bearer <access_token>` to every
/// outgoing request on the [apiDioProvider] Dio instance.
///
/// This is intentionally separate from [TokenExpiryInterceptor], which only
/// handles *reactive* 401 recovery.  Without this interceptor, the first
/// request always goes out unauthenticated, triggers a 401, then a refresh,
/// then a retry — which fails for multipart/form-data requests because
/// [FormData] / [MultipartFile] streams are single-use and cannot be replayed.
///
/// Execution order in [apiDioProvider]:
///   AuthInterceptor (onRequest)  →  network  →  TokenExpiryInterceptor (onError)
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._sessionController);

  final SessionController _sessionController;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final session = _sessionController.state.session;
    if (session != null && session.accessToken.isNotEmpty) {
      // Remove first to prevent duplicates on interceptor-driven retries.
      options.headers.remove('Authorization');
      options.headers['Authorization'] = 'Bearer ${session.accessToken}';
    }
    handler.next(options);
  }
}
