import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:diya_flutter/core/session/auth_session.dart';
import 'package:diya_flutter/core/session/session_controller.dart';
import 'package:diya_flutter/core/session/session_repository.dart';
import 'package:diya_flutter/core/network/auth_api.dart';
import 'package:diya_flutter/core/errors/app_error.dart';

class FakeSessionRepository implements SessionRepository {
  AuthSession? _session;
  @override
  Future<void> clear() async {
    _session = null;
  }

  @override
  Future<AuthSession?> load() async => _session;

  @override
  Future<void> save(AuthSession session) async {
    _session = session;
  }
}

class FakeAuthApi extends AuthApi {
  FakeAuthApi() : super(dio: Dio());

  bool throwOnMe = false;
  bool refreshSucceeds = true;

  @override
  Future<void> me({required String accessToken}) async {
    if (throwOnMe && !accessToken.contains('-refreshed')) throw const AppError(type: AppErrorType.auth, message: '401');
  }

  @override
  Future<AuthSession> refresh({required AuthSession session}) async {
    if (!refreshSucceeds) throw const AppError(type: AppErrorType.auth, message: 'refresh failed');
    return AuthSession(
      userId: session.userId,
      email: session.email,
      roles: session.roles,
      accessToken: '${session.accessToken}-refreshed',
      refreshToken: '${session.refreshToken}-refreshed',
      sessionId: session.sessionId,
      tokenVersion: session.tokenVersion + 1,
    );
  }
}

void main() {
  group('SessionController bootstrap', () {
    test('valid session stays authenticated', () async {
      final repo = FakeSessionRepository();
      final api = FakeAuthApi();
      final session = AuthSession(
        userId: 'u1',
        email: 'a@b.com',
        roles: [],
        accessToken: 'token',
        refreshToken: 'rtoken',
        sessionId: 's1',
        tokenVersion: 1,
      );
      await repo.save(session);

      final controller = SessionController(api, repo);
      // Allow bootstrap to finish
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(controller.state.isAuthenticated, isTrue);
      expect(controller.state.session?.accessToken, equals('token'));
    });

    test('expired token triggers refresh and persists refreshed token', () async {
      final repo = FakeSessionRepository();
      final api = FakeAuthApi();
      api.throwOnMe = true; // me() fails, force refresh path
      final session = AuthSession(
        userId: 'u1',
        email: 'a@b.com',
        roles: [],
        accessToken: 'token',
        refreshToken: 'rtoken',
        sessionId: 's1',
        tokenVersion: 1,
      );
      await repo.save(session);

      final controller = SessionController(api, repo);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(controller.state.isAuthenticated, isTrue);
      expect(controller.state.session?.accessToken, endsWith('-refreshed'));
    });

    test('refresh failure logs out', () async {
      final repo = FakeSessionRepository();
      final api = FakeAuthApi();
      api.throwOnMe = true;
      api.refreshSucceeds = false;

      final session = AuthSession(
        userId: 'u1',
        email: 'a@b.com',
        roles: [],
        accessToken: 'token',
        refreshToken: 'rtoken',
        sessionId: 's1',
        tokenVersion: 1,
      );
      await repo.save(session);

      final controller = SessionController(api, repo);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(controller.state.isAuthenticated, isFalse);
      expect(controller.state.status, equals(AuthStatus.unauthenticated));
    });
  });
}
