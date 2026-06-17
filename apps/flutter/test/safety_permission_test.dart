import 'package:flutter_test/flutter_test.dart';

import 'package:diya_flutter/core/errors/app_error.dart';
import 'package:diya_flutter/core/permissions/permission_manager.dart';
import 'package:diya_flutter/core/queue/queue_item.dart';
import 'package:diya_flutter/core/queue/queue_repository.dart';
import 'package:diya_flutter/core/network/safety_api.dart';
import 'package:diya_flutter/features/safety/models/safety_state.dart';
import 'package:dio/dio.dart';
import 'package:diya_flutter/features/safety/providers/safety_controller.dart';
import 'package:diya_flutter/features/safety/services/safety_service.dart';

import 'dart:async';
import 'package:diya_flutter/core/hardware/domain/messaging/arbitration_result.dart';
import 'package:diya_flutter/core/hardware/domain/messaging/event_router.dart';
import 'package:diya_flutter/core/hardware/domain/models/hardware_event.dart';
import 'package:diya_flutter/core/session/session_repository.dart';
import 'package:diya_flutter/core/session/auth_session.dart';

class FakeEventRouter implements EventRouter {
  final _controller = StreamController<HardwareEvent>.broadcast();
  @override
  Stream<HardwareEvent> get resolvedEvents => _controller.stream;
  @override
  Stream<ArbitrationResult> get arbitrationLog => const Stream.empty();
  @override
  Duration get bufferDuration => const Duration(milliseconds: 300);
  @override
  void dispose() => _controller.close();
}

class FakeSessionRepository implements SessionRepository {
  @override Future<void> save(AuthSession session) async {}
  @override Future<AuthSession?> load() async => AuthSession(userId: 'u', email: 'e', roles: [], accessToken: 'token', refreshToken: 'refresh', sessionId: 's', tokenVersion: 1);
  @override Future<void> clear() async {}
}

class FakePermissionManager implements PermissionManager {
  FakePermissionManager(this.status);

  AppPermissionStatus status;
  bool openSettingsCalled = false;

  @override
  Future<AppPermissionStatus> check(AppPermission permission) async => status;

  @override
  Future<void> openSettings() async {
    openSettingsCalled = true;
  }

  @override
  Future<AppPermissionStatus> request(AppPermission permission) async => status;
}

class FakeSafetyApi extends SafetyApi {
  FakeSafetyApi() : super(dio: Dio());

  bool shouldFail = false;

  @override
  Future<SafetyEventResponse> createSafetyEvent({
    required String accessToken,
    required Map<String, dynamic> payload,
    required String idempotencyKey,
    required String type,
  }) async {
    if (shouldFail) {
      throw AppError.network('offline');
    }
    return SafetyEventResponse(eventId: 'evt-1', traceId: 'trace-1', timestamp: DateTime.now());
  }
}

class FakeQueueRepository extends QueueRepository {
  FakeQueueRepository() : super(prefs: null);

  final List<QueueItem> _items = [];

  @override
  Future<void> clear() async {
    _items.clear();
  }

  @override
  Future<void> dequeue(String id) async {
    _items.removeWhere((item) => item.id == id);
  }

  @override
  Future<void> enqueue(QueueItem item) async {
    _items.add(item);
  }

  @override
  Future<List<QueueItem>> loadQueue() async => List<QueueItem>.from(_items);

  @override
  Future<void> update(QueueItem item) async {
    final index = _items.indexWhere((queued) => queued.id == item.id);
    if (index != -1) {
      _items[index] = item;
    }
  }
}

class RecordingSafetyService extends SafetyService {
  RecordingSafetyService({required super.safetyApi, required super.queueRepository});

  bool triggerCalled = false;

  @override
  Future<SafetyState> triggerSOS({required String accessToken, required String location}) async {
    triggerCalled = true;
    return SafetyState(status: SafetyStatus.sent, traceId: 'trace-1');
  }
}

void main() {
  group('SafetyController permission flow', () {
    test('denied location permission fails SOS without calling service', () async {
      final permissionManager = FakePermissionManager(AppPermissionStatus.denied);
      final queueRepository = FakeQueueRepository();
      final service = RecordingSafetyService(
        safetyApi: FakeSafetyApi(),
        queueRepository: queueRepository,
      );
      final controller = SafetyController(service, queueRepository, permissionManager);

      await controller.triggerSOS(accessToken: 'token', location: 'loc');

      expect(service.triggerCalled, isFalse);
      expect(controller.state.status, SafetyStatus.failed);
      expect(controller.state.error?.type, AppErrorType.permission);
      expect(controller.state.error?.retryable, isTrue);
    });

    test('permanently denied permission keeps settings path explicit', () async {
      final permissionManager = FakePermissionManager(AppPermissionStatus.permanentlyDenied);
      final queueRepository = FakeQueueRepository();
      final service = RecordingSafetyService(
        safetyApi: FakeSafetyApi(),
        queueRepository: queueRepository,
      );
      final controller = SafetyController(service, queueRepository, permissionManager);

      await controller.triggerSOS(accessToken: 'token', location: 'loc');

      expect(controller.state.status, SafetyStatus.failed);
      expect(controller.state.error?.type, AppErrorType.permission);
      expect(controller.state.error?.retryable, isFalse);
    });
  });
}