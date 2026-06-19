# Auth UX Audit — Diya (2ndEye)

**Date**: June 20, 2026  
**Branch**: `feat/auth-ux-hardening`  
**Auditor**: Kiro (Staff Engineer review)  
**Scope**: Flutter app auth, backend auth module, network interceptors, session lifecycle

---

## Section 1 — Executive Summary

### Authentication Completeness Score: 6 / 10

**Reasoning**

The core plumbing is solid. Login, register, refresh, logout, and session persistence all work end-to-end. The network interceptor chain is correctly designed — `AuthInterceptor` attaches tokens proactively, `TokenExpiryInterceptor` handles reactive 401 recovery. The session bootstrap logic is thorough, handling network-offline edge cases gracefully.

What drags the score down:

- **No profile screen**. Users cannot view or edit their account. There is no route, no screen, and no backend endpoint for it (beyond `/auth/me`).
- **No password change or reset flow**. Missing entirely from both Flutter and backend.
- **No account deletion**. Missing from both layers.
- **LoginRequest has no validation**. `email: str` with no format enforcement at login; passwords are not validated.
- **`phone_number` is a ghost field**. Present in the database model and migration, referenced in notification/guardian services, but never exposed in any API request schema and never collected from users.
- **Auth test suite is effectively dead**. The only backend test for auth is marked `@pytest.mark.skip`. Flutter session tests exist and pass but do not cover the interceptors.
- **Backend token decode is duplicated**. Every protected router decodes the JWT manually with an identical try/except block — there is no reusable `get_current_user` dependency.
- **Token expiry interceptor can fail silently on FormData retry**. The retry path in `_retryRequest` calls `_dio.fetch()` which will succeed — but the original FormData body may have already been consumed by the first attempt before `AuthInterceptor` ran.

The system is **functional for a controlled demo**. It is not production-hardened.

---

## Section 2 — Backend Authentication

### Endpoints

| Endpoint | Method | Auth Required | Status |
|---|---|---|---|
| `/auth/login` | POST | No | ✅ Implemented |
| `/auth/register` | POST | No | ✅ Implemented |
| `/auth/refresh` | POST | No | ✅ Implemented |
| `/auth/logout` | POST | Yes (Bearer) | ✅ Implemented |
| `/auth/me` | GET | Yes (Bearer) | ✅ Implemented |
| `/auth/change-password` | - | - | ❌ Missing |
| `/auth/reset-password` | - | - | ❌ Missing |
| `/auth/delete-account` | - | - | ❌ Missing |


### Login (`/auth/login`)

**Status**: ✅ Implemented  
**Evidence**: `backend/api/app/modules/auth/service.py:login()`

- Looks up user by email, verifies bcrypt hash, creates a session, returns a `TokenPair`.
- Access token: HS256 JWT, signed with `settings.auth.secret_key`, expires in `access_token_expire_minutes` (default 30 min).
- Refresh token: opaque UUID stored in `auth_sessions` table.
- `session_id` and `token_version` are included in both the JWT payload and the response body.

**Gap**: `LoginRequest` has no email format validation. The `email` field is `str`, not `EmailStr`. A request with `email: "not-an-email"` will pass Pydantic and attempt a DB lookup. `RegisterRequest` correctly uses `EmailStr` — `LoginRequest` should too.

**Gap**: No rate limiting or brute-force protection on this endpoint.

---

### Register (`/auth/register`)

**Status**: ✅ Implemented  
**Evidence**: `backend/api/app/modules/auth/service.py:register()`

- Checks for duplicate email, hashes password with bcrypt (72-byte truncation handled), creates user and session.
- `RegisterRequest` validates: `email` as `EmailStr`, `password` min 8 / max 128, `roles` must be `["blind"]` or `["family"]`.
- Password constraints are reasonable but not communicated to the user in Flutter — the error returned on short password is a 422, which Flutter's `AppErrorMapper` maps to `AppErrorType.unknown` (not `auth`), so the UI shows a generic error instead of "password too short".

**Gap**: `phone_number` is in the `User` model and migration but absent from `RegisterRequest`. Users can never provide a phone number. Notification/guardian services reference `guardian.phone_number` for SMS dispatch, but it will always be `None`.

**Gap**: No email verification. Users can register with any email, including ones they don't own.

---

### Logout (`/auth/logout`)

**Status**: ✅ Implemented  
**Evidence**: `backend/api/app/modules/auth/service.py:logout()`

- Accepts either a `session_id` in the request body or decodes it from the Bearer token.
- Sets `auth_sessions.revoked_at` timestamp.
- If the backend is unreachable, Flutter's `SessionController.signOut()` still clears local storage — good defensive behavior.

**Gap**: No multi-device logout. There is no "logout all sessions" endpoint. A user who loses their phone cannot invalidate all active sessions.

---

### Refresh (`/auth/refresh`)

**Status**: ✅ Implemented  
**Evidence**: `backend/api/app/modules/auth/service.py:refresh()`

- Rotates session: old refresh token is replaced with a new UUID, `token_version` is incremented.
- Revoked session check: if `revoked_at` is set, returns 401 with `AUTH.REFRESH.TOKEN.REUSE`.
- `rotate_session()` does a commit and refresh — the old token is invalidated after the new one is issued.

**Gap**: No detection of refresh token reuse from a different session (token theft scenario). If an attacker has the refresh token and uses it first, the legitimate user's refresh attempt will return `AUTH.REFRESH.TOKEN.REUSE` — but no alert or forced full logout happens on the server side.

**Gap**: `refresh_token_expire_days` is set in settings (default 30 days) but `AuthSession` has no `expires_at` column. Refresh tokens never expire based on time — only on explicit revocation or rotation.

---

### Session Management

**Status**: ✅ Functional  
**Evidence**: `backend/api/app/modules/auth/repository.py:SqlAlchemyAuthRepository`

- `auth_sessions` table stores `user_id`, `refresh_token` (UUID string), `token_version`, `revoked_at`.
- Sessions are per-login, not per-device. Multiple active sessions are supported but not visible to the user.
- `InMemoryAuthRepository` is still present in the codebase. It is not used in production (startup uses `SqlAlchemyAuthRepository`) but it is test-accessible dead code risk.

---

### Roles

**Status**: ✅ Implemented (limited)  
**Evidence**: `RegisterRequest.validate_roles()`, `User.roles` (JSON array)

- Supported roles: `blind`, `family`. Backend enforces this at registration.
- JWT claims include `roles` and hardcoded `permissions: ["auth:read", "auth:write"]`.
- `permissions` claim in the JWT is hardcoded — it is not used anywhere for authorization decisions. It exists in the token but no endpoint checks it.

**Gap**: No role-based access control (RBAC) on any endpoint. Any valid token can call any protected endpoint regardless of role. There is no guard that prevents a `family` user from calling `/assist/sessions/*/turns` or a `blind` user from accepting a guardian invitation as a guardian.

---

### Guardian Assumptions

**Status**: ⚠️ Partial  
**Evidence**: `backend/api/app/modules/guardian/service.py`

- Guardian invite flow exists. A blind user invites by email, a guardian accepts.
- Role checking inside `GuardianService` is done by querying user roles from the DB — not from the JWT. This is the correct pattern, but it means an extra DB round-trip per guardian operation.
- `GuardianService.invite_guardian()` checks that the inviter is `blind` and the target is `family`.

**Gap**: Flutter has no UI for guardian management. The backend flow is complete, but there is no screen for it on the mobile side.

---

### Password Validation

**Status**: ⚠️ Partial  
**Evidence**: `RegisterRequest.password = Field(min_length=8, max_length=128)`

- Register enforces 8-128 chars via Pydantic.
- Login has no password validation (by design — it's better to fail at the DB level for login).
- No strength requirements (uppercase, digit, symbol). The demo password `Test1234@` passes; `password` (8 chars, all lowercase) also passes.
- No validation error message forwarding to Flutter UI for 422 responses.

---

### Phone Number Support

**Status**: ⚠️ Ghost field  
**Evidence**: `User.phone_number`, migration `0002_sprint2`, `guardian/service.py`, `safety/service.py`

- Column exists in DB: `phone_number VARCHAR(20) NULLABLE`.
- Migration 0002 adds it.
- `GuardianService` and `SafetyEventService` pass `phone_number` to notification providers for SMS — but it will always be `None` because no API endpoint allows setting it.
- The `RegisterRequest` schema does not include `phone_number`.
- The `MockSMSProvider` is used for notifications anyway — so this is not a live breakage, but it is a silent data gap.

---

## Section 3 — Flutter Authentication

### Current Flow Diagram

```
App Launch
    │
    ▼
main.dart
    │── DiyaRuntime.boot()          ← HardwareBootstrapper, SafetyBootstrapper, AssistBootstrapper
    │── UncontrolledProviderScope   ← Injects runtime container into widget tree
    │
    ▼
SecondEyeApp.build()
    │── ref.watch(appRouterProvider) ← creates GoRouter, watches sessionControllerProvider
    │
    ▼
GoRouter initialLocation: '/'
    │
    ▼
StartupScreen ('/')
    │── Router redirect fires
    │── sessionState.isLoading → stay at '/'
    │
    ▼ (SessionController bootstrap completes)

[No session stored]          [Session found in SecureStorage]
    │                               │
    │                               ▼
    │                    AuthApi.me(accessToken)
    │                               │
    │                    ┌──────────┴──────────┐
    │                    │ OK (200)             │ Error
    │                    │                      │
    │                    ▼                      ▼
    │              authenticated           AuthApi.refresh()
    │                                           │
    │                               ┌───────────┴──────────┐
    │                               │ OK                    │ Error
    │                               │                       │
    │                               ▼                       ▼
    │                         save + authenticated    clear + unauthenticated
    │
    ▼
AuthStatus.unauthenticated
    │
    ▼
GoRouter redirect → '/login'
    │
    ▼
LoginScreen
    │── signIn() or signUp()
    │── SessionController.signIn() → AuthApi.login()
    │── save session to SecureStorage
    │── AuthStatus.authenticated
    │
    ▼
GoRouter redirect → '/home'
    │
    ▼
HomeScreen
```

---

### SessionController

**Status**: ✅ Well implemented  
**File**: `apps/flutter/lib/core/session/session_controller.dart`

- Extends `ChangeNotifier` — GoRouter can `refreshListenable` on it directly. Good pattern.
- Bootstrap: load → me → [refresh if failed] → [clear if refresh fails]. Network errors keep the session alive (offline-first).
- `refreshSession()` uses `AsyncLock` to prevent concurrent refresh races. Correct.
- `updateSession()` exists for interceptor-driven token updates. This is the right contract.
- `signOut()`: tries backend logout, falls back gracefully if unreachable. Correct.

**Gap**: `_bootstrap()` has duplicated error handling paths for `AppError` vs generic `Exception`. The two paths do the same thing (try refresh, then fall back). This is defensive but confusing — could be simplified to one catch block.

---

### SessionRepository / SecureSessionRepository

**Status**: ✅ Well implemented  
**File**: `apps/flutter/lib/core/session/secure_session_repository.dart`

- Uses `flutter_secure_storage` for token storage. Correct.
- Includes migration path from `SharedPreferences` — handles upgrades from legacy installs.
- Corrupt data is handled: delete + return null. Does not crash.
- Storage key: `AppConfig.sessionStorageKey` = `"second_eye_session"`.

---

### Interceptor Chain

**Status**: ✅ Correctly designed, with one significant caveat  
**Files**: `auth_interceptor.dart`, `token_expiry_interceptor.dart`, `api_client.dart`

**Chain order** (from `apiDioProvider`):
```
Request →  AuthInterceptor.onRequest()   →  [token attached]
       →  Network
       →  TokenExpiryInterceptor.onError()  ← only fires on 401
```

**AuthInterceptor** (proactive):
- Attaches `Authorization: Bearer <token>` on every outbound request from `apiDioProvider`.
- Removes the header first to prevent duplicates on retries. Correct.
- Reads token from `SessionController.state.session` synchronously. Correct.

**TokenExpiryInterceptor** (reactive):
- On 401: calls `authApi.refresh()`, updates session via `sessionController.updateSession()`, retries with new token.
- Uses a `Completer` to queue concurrent 401s. Only one refresh runs; others wait. Correct.
- On refresh failure: calls `sessionController.signOut()`. Correct.

**Critical Issue — FormData Retry**:
The interceptor calls `_dio.fetch(err.requestOptions)`. For `FormData`/`MultipartFile` requests (i.e., `AssistApi.createTurn()`), the multipart body is a stream that is consumed on the first send. By the time a 401 arrives, the stream is exhausted. `_dio.fetch()` on the original `requestOptions` will send an empty body.

**However** — `AuthInterceptor` mitigates this by attaching the token before the first attempt, so a fresh session should never hit a 401 on the first request. The retry path is only invoked if the token has expired mid-flight. For tokens with a 30-minute TTL, this is a rare edge case but it does exist (e.g., token expires during a slow upload).

The current design accepts this risk with the comment in `api_client.dart`. It is documented but not fixed.

---

### GoRouter / Routing

**Status**: ✅ Functional, with gaps

**Defined routes**:
```
/             → StartupScreen
/login        → LoginScreen
/home         → HomeScreen
/debug        → DeviceDebugScreen
/debug/device/:id → DeviceDetailScreen
```

**Redirect logic**:
- Loading → stay at `/`
- Unauthenticated, not `/login` → `/login`
- Authenticated, at `/login` → `/home`
- Authenticated, at `/` → `/home`

**Gap**: No `/register` route. Registration is hidden inside `LoginScreen` via a toggle button. This is a UX debt — not a functional problem, but register is an afterthought in the routing model.

**Gap**: No `/profile`, `/settings`, `/change-password` routes. These features don't exist at all.

**Gap**: Debug routes (`/debug`, `/debug/device/:id`) are accessible to any authenticated user. There is no role check or build-mode guard on them.

---

## Section 4 — Current UX

### Can Users…

| Action | Status | Evidence | Notes |
|---|---|---|---|
| **Login** | ✅ Implemented | `LoginScreen`, `SessionController.signIn()` | Works. Email + password form. |
| **Register** | ✅ Implemented | `LoginScreen` toggle, `SessionController.signUp()` | Functional but buried — same screen as login, toggled by a text button. |
| **Logout** | ✅ Implemented | (no dedicated button visible in `HomeScreen`) | `SessionController.signOut()` exists and works but **there is no logout button on `HomeScreen`**. Users cannot log out through the UI. |
| **View profile** | ❌ Missing | No screen, no route, no widget | Backend has `/auth/me` but Flutter has no profile screen. |
| **Change password** | ❌ Missing | No endpoint, no screen | Not implemented on either layer. |
| **Reset password (forgot)** | ❌ Missing | No endpoint, no screen, no email flow | Not implemented anywhere. |
| **Delete account** | ❌ Missing | No endpoint, no screen | Not implemented on either layer. |
| **View session status** | ⚠️ Partial | `SessionState.status` exists, shown on login screen only as loading indicator | No persistent indicator in the main UI. |

### Login UX

**What works**:
- Email + password form with show/hide password toggle.
- `FilledButton` disabled while loading, with spinner inside button. Good.
- Error messages shown in a styled container below the form.
- Demo login button autofills and submits instantly. Useful for development.

**What's missing**:
- No "forgot password" link.
- No input validation feedback before submission (empty fields just return silently).
- Password field does not indicate minimum length requirement.
- Role selector on register is a `SegmentedButton` — clean, but no description of what each role means. A first-time user does not know the difference between "Blind User" and "Family Member" without context.

### Registration UX

**What works**:
- Animated transition between login and register mode.
- Role selection with `SegmentedButton`.
- Correct error propagation for duplicate email (422 → `AppError`).

**What's missing**:
- 422 validation errors (e.g., password too short) map to `AppErrorType.unknown`, not `AppErrorType.auth`. The error container shows a generic "Something went wrong" message instead of "Password must be at least 8 characters".
- No password confirmation field.
- No terms of service acknowledgement.

### Logout UX

**Critical Gap**: There is no logout button anywhere in the authenticated UI. `HomeScreen` has an `AppBar` with only a title. `SessionController.signOut()` is fully implemented but unreachable by the user through normal navigation. A user who wants to sign out cannot.

---

## Section 5 — Assist Authentication

### Does Flutter attach access tokens to Assist requests?

**Status**: ✅ Yes — via `AuthInterceptor`  
**Evidence**: `apps/flutter/lib/core/network/auth_interceptor.dart`

`AssistApi` uses `_dio` which is sourced from `apiDioProvider`. The `apiDioProvider` has `AuthInterceptor` registered as the first interceptor. Every request through it — including multipart Assist turns — gets `Authorization: Bearer <token>` attached before the first attempt.

This was the root cause of the original 401 bug (Task 3 in sprint history). The fix was correct: `AuthInterceptor` now runs before the network call.

**Log evidence from user session** (Query #3):
```
I/flutter: [AutoCaptureAdapter] Fallback capture succeeded: ...jpg
```
The request gets through to the backend without auth errors.

---

### Are refresh retries implemented?

**Status**: ✅ Yes — via `TokenExpiryInterceptor`  
**Evidence**: `apps/flutter/lib/core/network/token_expiry_interceptor.dart`

- 401 response triggers refresh via `authApi.refresh()`.
- Session updated in `sessionController.updateSession()`.
- Original request retried with new token via `_dio.fetch(err.requestOptions)`.
- Concurrent 401s are queued using a `Completer`.

**Known limitation**: The retry via `_dio.fetch()` will not work correctly for multipart/FormData bodies because the stream is consumed on the first send. See Section 3 for full analysis. This is a known, documented risk.

---

### Do 401 handlers work correctly?

**Status**: ✅ Yes for JSON requests, ⚠️ Theoretical failure for multipart  

For standard JSON requests (login, refresh, logout, guardian, safety, location): the 401 → refresh → retry chain works correctly.

For multipart requests (Assist turns): `AuthInterceptor` prevents the 401 from occurring in the first place on a valid session. If the token expires mid-flight during a slow upload, the retry will send an empty body. This is an edge case that has not been observed in practice given the 30-minute token TTL.

---

### Does Assist participate correctly in auth?

**Status**: ✅ Yes (backend), ✅ Yes (Flutter)  
**Evidence**: `backend/api/app/modules/assist/router.py`

Backend:
- `token: str = Depends(get_bearer_token)` — requires Bearer token.
- Manually decodes JWT with `decode_access_token(token)`.
- Checks `payload.get("sub")` for user ID.
- Returns 401 with `AUTH.TOKEN.INVALID` on JWTError.

Flutter:
- `AssistApi` uses `apiDioProvider` (has `AuthInterceptor`).
- Token is attached proactively on every Assist request.
- Confirmed working from real device logs.

**Gap** (backend structural): The JWT decode pattern in the Assist router is copy-pasted identically across `assist/router.py`, `safety/router.py`, `guardian/router.py`, `location/router.py`, and `notifications/router.py`. There is no shared `get_current_user` FastAPI dependency. This is a maintenance hazard — any change to the validation logic must be applied in 5 places.

---

## Section 6 — Gap Analysis

| Feature | Expected | Implemented | Missing | Risk |
|---|---|---|---|---|
| **Login** | Email + password → JWT session | ✅ Complete | — | Low |
| **Register** | Email + password + role → JWT session | ✅ Complete | Phone number collection | Low |
| **Logout** | Clear session, revoke server-side | ✅ Complete (backend + controller) | Logout button in UI | High (users can't sign out) |
| **Token Refresh** | 401 → refresh → retry | ✅ Complete | FormData retry failure on mid-flight expiry | Medium |
| **Session Persistence** | Survive app restart | ✅ Complete (SecureStorage) | — | Low |
| **Session Bootstrap** | Validate stored session on launch | ✅ Complete | Offline fallback keeps expired tokens alive | Low |
| **Profile Screen** | View user info (email, roles) | ❌ Missing | Entire screen + route | Medium |
| **Change Password** | Authenticated password update | ❌ Missing | Backend endpoint + Flutter screen | Medium |
| **Reset Password** | Forgot password email flow | ❌ Missing | Backend endpoint + email provider + Flutter flow | High (users locked out if they forget password) |
| **Delete Account** | Purge user + sessions | ❌ Missing | Backend endpoint + Flutter screen | Medium |
| **Email Validation (Login)** | Reject malformed email at input | ⚠️ Partial | `LoginRequest.email` is `str`, not `EmailStr` | Low |
| **422 Error UX** | Show field-specific errors | ⚠️ Partial | AppErrorMapper doesn't handle 422 specially | Low |
| **Phone Number** | Collect + use for SMS | ⚠️ Ghost field | API schema, Flutter form, SMS provider | Medium (blocks real SOS SMS) |
| **Role-Based Access** | Restrict endpoints by role | ❌ Missing | RBAC guard/dependency on endpoints | Medium |
| **Multi-Session Logout** | Revoke all sessions | ❌ Missing | Backend endpoint | Low (edge case) |
| **Refresh Token Expiry** | Token expires after N days | ⚠️ Config exists, DB missing | `expires_at` column on `auth_sessions` | Low (tokens live forever until rotation) |
| **Rate Limiting (login)** | Brute force protection | ❌ Missing | Middleware or decorator | Medium |
| **Auth Test Coverage** | Backend auth service tested | ❌ Dead | Existing test `@skip`'d, no replacement | High |
| **get_current_user dep** | Single JWT validation point | ❌ Missing | 5 routers decode JWT independently | Medium (maintenance) |
| **Debug Route Guard** | Debug only in dev/debug builds | ❌ Missing | Build mode check or role check | Low |
| **Guardian UI** | Invite/accept/view guardians | ❌ Missing | Entire feature set on Flutter side | Medium |

---

## Section 7 — Recommendations

These are small, targeted improvements. No redesigns. No new abstractions. Ordered by impact.

---

### 7.1 Add a Logout Button (Critical UX)

**Impact**: High. Users currently cannot log out.  
**Effort**: 30 minutes.  
**Where**: `HomeScreen` AppBar, trailing icon.

```dart
IconButton(
  icon: const Icon(Icons.logout),
  onPressed: () => ref.read(sessionControllerProvider).signOut(),
)
```

One commit. No backend changes needed.

---

### 7.2 Create a `get_current_user` FastAPI Dependency

**Impact**: Medium. Eliminates 5 identical try/except blocks.  
**Effort**: 1–2 hours.  
**Where**: `backend/api/app/api/deps.py`

```python
async def get_current_user(token: str = Depends(get_bearer_token)) -> dict:
    try:
        return decode_access_token(token)
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": str(error)},
        ) from error
```

Replace all 5 router decode blocks with `Depends(get_current_user)`. Small commits per router.

---

### 7.3 Fix `LoginRequest` Email Validation

**Impact**: Low but correct.  
**Effort**: 5 minutes.  
**Where**: `backend/api/app/schemas.py`

Change `email: str` to `email: EmailStr` in `LoginRequest`. Consistent with `RegisterRequest`.

---

### 7.4 Fix 422 Error Mapping in Flutter

**Impact**: Medium UX improvement. Users see "password too short" instead of "Something went wrong."  
**Effort**: 30 minutes.  
**Where**: `apps/flutter/lib/core/errors/app_error_mapper.dart`

Add a case for status 422 in `fromDioException`:
```dart
if (statusCode == 422) {
  // Try to extract Pydantic validation message
  final detail = error.response?.data?['detail'];
  final msg = _extract422Message(detail) ?? 'Validation failed. Check your input.';
  return AppError.auth(msg, code: 'VALIDATION_ERROR');
}
```

---

### 7.5 Add a Profile Screen (Minimal)

**Impact**: Medium. Required for production.  
**Effort**: 2–3 hours.  
**Scope**: Read-only first. Show email and roles from `sessionController.state.session`.

- New route `/profile` in `app_router.dart`.
- New file `apps/flutter/lib/features/auth/profile_screen.dart`.
- Link from `HomeScreen` AppBar (person icon).
- No backend changes — reads from local session.

Add logout button here too (or in AppBar).

---

### 7.6 Add `expires_at` to `auth_sessions`

**Impact**: Low. Makes refresh token expiry actually work.  
**Effort**: 30 minutes + migration.  
**Where**: `backend/api/app/modules/auth/models.py`, new migration

```python
expires_at: Mapped[datetime | None] = mapped_column(default=None)
```

Set in `create_session()`:
```python
expires_at=datetime.now(UTC) + timedelta(days=settings.auth.refresh_token_expire_days)
```

Check in `refresh()`:
```python
if session.expires_at and session.expires_at < datetime.now(UTC):
    raise HTTPException(401, ...)
```

---

### 7.7 Resurrect the Auth Test Suite

**Impact**: High. The only auth test is `@pytest.mark.skip`.  
**Effort**: 2–3 hours.  
**Where**: `backend/api/tests/test_auth_service.py`

Write async tests using `InMemoryAuthRepository` (it exists and is correct). Cover:
- `test_login_success`
- `test_login_invalid_credentials`
- `test_register_duplicate_email`
- `test_refresh_rotates_token`
- `test_refresh_revoked_token_rejected`
- `test_logout_revokes_session`
- `test_me_with_valid_token`
- `test_me_with_invalid_token`

---

### 7.8 Add Phone Number to Register (When SMS Is Needed)

**Impact**: Medium. Required for SOS SMS to work.  
**Effort**: 1 hour.  
**Scope**: Only when SMS notifications are being activated. Not urgent now.

- Add `phone_number: str | None` to `RegisterRequest`.
- Pass it to `repository.create_user()`.
- Add optional phone field to Flutter registration form.

Do not make it required — it should be optional.

---

### What to Defer

The following are real gaps but not worth tackling now:

- **Password reset / forgot password**: Requires email provider integration. Not a small task. Defer to a dedicated sprint.
- **Account deletion**: Requires cascade cleanup across tables. Defer.
- **RBAC on endpoints**: Requires clear product decision on which roles can call which endpoints. Defer until guardian/family features are more complete.
- **Rate limiting**: Can be handled at infrastructure level (nginx, API gateway) rather than in app code. Defer.
- **Multi-device logout**: Low user impact today. Defer.

---

## Appendix — Token Flow Reference

### JWT Claims (access token)

```json
{
  "sub": "<user_uuid>",
  "uid": "<user_uuid>",
  "roles": ["blind"],
  "permissions": ["auth:read", "auth:write"],
  "session_id": "<session_uuid>",
  "token_version": 1,
  "jti": "<random_uuid>",
  "iat": 1718847600,
  "exp": 1718849400
}
```

Note: `permissions` is hardcoded. `uid` duplicates `sub`. Neither is currently used by the authorization layer.

### Auth Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `AUTH.CREDENTIALS.INVALID` | 401 | Wrong email or password |
| `AUTH.EMAIL.EXISTS` | 400 | Duplicate email on register |
| `AUTH.REFRESH.TOKEN.REUSE` | 401 | Refresh token already rotated or revoked |
| `AUTH.TOKEN.INVALID` | 401 | JWT decode failure or missing sub |
| `AUTH.TOKEN.EXPIRED` | 401 | Session revoked or token_version mismatch |
| `AUTH.TOKEN.MISSING` | 401 | No Bearer token in Authorization header |
| `AUTH.USER.NOT_FOUND` | 404 | User deleted after session created |

### Response Envelope

All auth endpoints return:
```json
{
  "success": true,
  "data": { ... },
  "trace_id": "trace-local-demo"
}
```

Error responses:
```json
{
  "success": false,
  "error": {
    "code": "AUTH.CREDENTIALS.INVALID",
    "message": "Invalid credentials",
    "details": null
  },
  "trace_id": "trace-local-demo"
}
```

`AppErrorMapper._fromBackendResponse()` reads `error.code` and `error.message`. This is wired correctly in Flutter.

---

*Audit complete. Do NOT implement. Review first.*
