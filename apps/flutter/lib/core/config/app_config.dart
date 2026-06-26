import 'package:flutter/foundation.dart';

class AppConfig {
  AppConfig._();

  static const String environment = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'dev',
  );

  static const String apiBaseUrl = String.fromEnvironment('API_BASE_URL');

  static const String sessionStorageKey = 'second_eye_session';

  static const String geminiApiKey = String.fromEnvironment('GEMINI_API_KEY');

  static bool get configured => apiBaseUrl.isNotEmpty;

  static bool get isDev => environment == 'dev';

  static bool get isStaging => environment == 'staging';

  static bool get isProd =>
      environment == 'prod' || environment == 'production';

  static void validate() {
    if (!configured) {
      throw StateError('''
        API_BASE_URL is not configured.

        Did you forget to provide an environment file?

        Examples:

        flutter run --dart-define-from-file=env/dev.json

        flutter build apk --dart-define-from-file=env/prod.json
        ''');
    }

    if (geminiApiKey.isEmpty) {
      throw StateError('GEMINI_API_KEY is not configured.');
    }

    debugPrint('[Config] Environment: $environment');

    debugPrint('[Config] API: $apiBaseUrl');
  }
}
