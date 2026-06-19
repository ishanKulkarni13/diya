import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../session/session_controller.dart';
import 'auth_interceptor.dart';
import 'token_expiry_interceptor.dart';

/// Base options for all Dio instances.
final _baseOptions = BaseOptions(
  baseUrl: AppConfig.apiBaseUrl,
  connectTimeout: const Duration(seconds: 10),
  receiveTimeout: const Duration(seconds: 10),
  sendTimeout: const Duration(seconds: 10),
);

/// A raw Dio client specifically for authentication operations (login, register, refresh).
/// This client does NOT include the token expiry interceptor to prevent circular refresh loops.
final authDioProvider = Provider<Dio>((ref) {
  return Dio(_baseOptions);
});

/// The main Dio client for all domain API requests.
///
/// Interceptor order (important):
///   1. [AuthInterceptor]       — proactively attaches Bearer token on every request.
///   2. [TokenExpiryInterceptor] — catches 401s, refreshes, and retries.
///
/// AuthInterceptor must run first so that the token is present on the initial
/// attempt.  This prevents the 401 on multipart requests (e.g. Assist turns)
/// where the FormData body cannot be replayed on a retry.
final apiDioProvider = Provider<Dio>((ref) {
  final dio = Dio(_baseOptions);
  final sessionController = ref.read(sessionControllerProvider);

  dio.interceptors.add(AuthInterceptor(sessionController));
  dio.interceptors.add(
    TokenExpiryInterceptor(
      dio,
      authApi: ref.read(authApiProvider),
      sessionController: sessionController,
    ),
  );

  return dio;
});
