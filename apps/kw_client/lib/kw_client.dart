/// Keepwell shared pure-Dart client library.
///
/// Exports configuration, Contract §5/§8 domain models, REST API client,
/// Live Call WebSocket client (Contract §7), demo/Firebase auth helpers,
/// and reactive Firestore / REST polling repositories.
library;

export 'src/api/embedded_snapshot.dart';
export 'src/api/kw_api_client.dart';
export 'src/auth/kw_auth.dart';
export 'src/config.dart';
export 'src/live/live_call_client.dart';
export 'src/models/models.dart';
export 'src/repositories/firestore_client.dart';
export 'src/repositories/live_feed_repository.dart';
