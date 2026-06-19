import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../session/session_controller.dart';
import 'auth_api.dart';

/// Interceptor to handle 401 token expiry by attempting a single refresh.
/// Queues concurrent 401 requests using a Completer to ensure only one refresh happens.
class TokenExpiryInterceptor extends Interceptor {
  TokenExpiryInterceptor(
    this._dio, {
    required this.authApi,
    required this.sessionController,
  });

  final Dio _dio;
  final AuthApi authApi;
  final SessionController sessionController;

  bool _isRefreshing = false;
  Completer<void>? _completer;

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    // If it's a 401 and we have a session, we need to refresh
    if (err.response?.statusCode == 401) {
      final currentSession = sessionController.state.session;
      if (currentSession == null) {
        return handler.next(err);
      }

      if (_isRefreshing) {
        // Wait for the ongoing refresh to complete
        try {
          await _completer?.future;
          // After wait, token should be refreshed. Retry request.
          return _retryRequest(err, handler);
        } catch (_) {
          // If the queued refresh failed, pass the error along
          return handler.next(err);
        }
      }

      _isRefreshing = true;
      _completer = Completer<void>();

      try {
        // Attempt to refresh the token using the dedicated AuthApi
        final newSession = await authApi.refresh(session: currentSession);
        
        // Update the global session state
        await sessionController.updateSession(newSession);

        // Resolve the completer so queued requests can proceed
        _completer?.complete();
        _isRefreshing = false;
        _completer = null;

        // Retry the original request
        return _retryRequest(err, handler);
      } catch (e) {
        // Refresh failed. Revoke session and pass error.
        _completer?.completeError(e);
        _isRefreshing = false;
        _completer = null;
        
        await sessionController.signOut();
        return handler.next(err);
      }
    }

    return handler.next(err);
  }

  Future<void> _retryRequest(DioException err, ErrorInterceptorHandler handler) async {
    final session = sessionController.state.session;
    if (session == null) {
      debugPrint('[TokenExpiryInterceptor] Cannot retry: no session after refresh');
      return handler.next(err);
    }

    // Safely update the authorization header to prevent duplicates
    err.requestOptions.headers.remove('Authorization');
    err.requestOptions.headers['Authorization'] = 'Bearer ${session.accessToken}';

    debugPrint('[TokenExpiryInterceptor] Retrying ${err.requestOptions.method} ${err.requestOptions.path}');

    try {
      // Use the provided dio instance (apiDioProvider) to preserve all configs and interceptors
      final response = await _dio.fetch<dynamic>(err.requestOptions);
      debugPrint('[TokenExpiryInterceptor] Retry succeeded with ${response.statusCode}');
      return handler.resolve(response);
    } on DioException catch (e) {
      debugPrint('[TokenExpiryInterceptor] Retry failed: ${e.type} ${e.message}');
      return handler.next(e);
    }
  }
}
