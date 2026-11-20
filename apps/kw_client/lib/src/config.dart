/// Runtime configuration for Keepwell client apps.
///
/// Reads compile-time `--dart-define` values matching Contract §4 and defaults
/// to the local Part B mock servers (`localhost:8081` REST, `localhost:8082` WS).
class KwConfig {
  const KwConfig({
    this.apiBaseUrl = 'http://localhost:8081/v1',
    this.liveWsUrl = 'ws://localhost:8082/v1/live/call',
    this.firebaseProjectId = 'keepwell-demo',
    this.firestoreEmulatorHost = '',
    this.firebaseAuthEmulatorHost = '',
    this.demoMode = true,
    this.paymentMode = 'sandbox',
    this.googleMapsApiKey = '',
    this.lookerStudioUrl = '',
  });

  /// Constructs configuration from `--dart-define` environment variables.
  factory KwConfig.fromEnvironment() {
    return const KwConfig(
      apiBaseUrl: String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://localhost:8081/v1',
      ),
      liveWsUrl: String.fromEnvironment(
        'LIVE_WS_URL',
        defaultValue: 'ws://localhost:8082/v1/live/call',
      ),
      firebaseProjectId: String.fromEnvironment(
        'FIREBASE_PROJECT_ID',
        defaultValue: 'keepwell-demo',
      ),
      firestoreEmulatorHost: String.fromEnvironment(
        'FIRESTORE_EMULATOR_HOST',
        defaultValue: '',
      ),
      firebaseAuthEmulatorHost: String.fromEnvironment(
        'FIREBASE_AUTH_EMULATOR_HOST',
        defaultValue: '',
      ),
      demoMode: bool.fromEnvironment(
        'DEMO_MODE',
        defaultValue: true,
      ),
      paymentMode: String.fromEnvironment(
        'PAYMENT_MODE',
        defaultValue: 'sandbox',
      ),
      googleMapsApiKey: String.fromEnvironment(
        'GOOGLE_MAPS_API_KEY',
        defaultValue: '',
      ),
      lookerStudioUrl: String.fromEnvironment(
        'LOOKER_STUDIO_URL',
        defaultValue: '',
      ),
    );
  }

  final String apiBaseUrl;
  final String liveWsUrl;
  final String firebaseProjectId;
  final String firestoreEmulatorHost;
  final String firebaseAuthEmulatorHost;
  final bool demoMode;
  final String paymentMode;
  final String googleMapsApiKey;
  final String lookerStudioUrl;

  /// Normalized API base URI without trailing slash (e.g. `http://localhost:8081/v1`).
  Uri get apiBaseUri {
    final trimmed = apiBaseUrl.endsWith('/')
        ? apiBaseUrl.substring(0, apiBaseUrl.length - 1)
        : apiBaseUrl;
    return Uri.parse(trimmed);
  }

  /// Root service URI without `/v1` suffix, used for `/healthz` and `/readyz`.
  Uri get apiRootUri {
    final base = apiBaseUri;
    final path = base.path;
    if (path.endsWith('/v1')) {
      final rootPath = path.substring(0, path.length - 3);
      return base.replace(path: rootPath.isEmpty ? '/' : rootPath);
    }
    return base;
  }

  /// WebSocket URI for the Live Call bridge (`/v1/live/call`).
  Uri get liveWsUri => Uri.parse(liveWsUrl);

  /// Whether the Firestore emulator host is configured.
  bool get useFirestoreEmulator => firestoreEmulatorHost.trim().isNotEmpty;

  /// Whether the Firebase Auth emulator host is configured.
  bool get useAuthEmulator => firebaseAuthEmulatorHost.trim().isNotEmpty;

  /// Whether sandbox payment completion is enabled.
  bool get isSandboxPayment => paymentMode.toLowerCase() == 'sandbox';

  /// Base URL for Firestore REST document queries.
  String get firestoreDocumentsBaseUrl {
    if (useFirestoreEmulator) {
      final host = firestoreEmulatorHost.trim();
      final prefix = host.startsWith('http://') || host.startsWith('https://')
          ? host
          : 'http://$host';
      return '$prefix/v1/projects/$firebaseProjectId/databases/(default)/documents';
    }
    return 'https://firestore.googleapis.com/v1/projects/$firebaseProjectId/databases/(default)/documents';
  }

  KwConfig copyWith({
    String? apiBaseUrl,
    String? liveWsUrl,
    String? firebaseProjectId,
    String? firestoreEmulatorHost,
    String? firebaseAuthEmulatorHost,
    bool? demoMode,
    String? paymentMode,
    String? googleMapsApiKey,
    String? lookerStudioUrl,
  }) {
    return KwConfig(
      apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
      liveWsUrl: liveWsUrl ?? this.liveWsUrl,
      firebaseProjectId: firebaseProjectId ?? this.firebaseProjectId,
      firestoreEmulatorHost:
          firestoreEmulatorHost ?? this.firestoreEmulatorHost,
      firebaseAuthEmulatorHost:
          firebaseAuthEmulatorHost ?? this.firebaseAuthEmulatorHost,
      demoMode: demoMode ?? this.demoMode,
      paymentMode: paymentMode ?? this.paymentMode,
      googleMapsApiKey: googleMapsApiKey ?? this.googleMapsApiKey,
      lookerStudioUrl: lookerStudioUrl ?? this.lookerStudioUrl,
    );
  }
}
