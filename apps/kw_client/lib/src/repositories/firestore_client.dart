import 'dart:convert';

import 'package:http/http.dart' as http;

import '../api/kw_api_client.dart';
import '../config.dart';

/// Pure-Dart Firestore REST client supporting both `FIRESTORE_EMULATOR_HOST`
/// and production Firestore without native platform-channel dependencies.
///
/// Clients in Keepwell are strictly read-only on Firestore (Contract §6).
class KwFirestoreClient {
  KwFirestoreClient({
    required this.config,
    http.Client? httpClient,
    this.tokenProvider,
    this.timeout = const Duration(seconds: 6),
  }) : _http = httpClient ?? http.Client();

  final KwConfig config;
  final http.Client _http;
  final KwTokenProvider? tokenProvider;
  final Duration timeout;

  /// Lists documents in a Firestore collection path (e.g. `centres/{cid}/feed`).
  Future<List<Map<String, dynamic>>> listCollection(
    String collectionPath, {
    int pageSize = 100,
  }) async {
    final cleanPath = collectionPath.startsWith('/')
        ? collectionPath.substring(1)
        : collectionPath;
    final uri = Uri.parse(
      '${config.firestoreDocumentsBaseUrl}/$cleanPath?pageSize=$pageSize',
    );
    final headers = await _headers();
    final resp = await _http.get(uri, headers: headers).timeout(timeout);
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw StateError(
        'Firestore REST GET $cleanPath failed with HTTP ${resp.statusCode}',
      );
    }

    final decoded = jsonDecode(resp.body);
    if (decoded is! Map) return const [];
    final docs = decoded['documents'];
    if (docs is! List) return const [];

    return docs
        .whereType<Map>()
        .map((doc) => decodeDocument(
              doc.map((k, v) => MapEntry(k.toString(), v)),
            ))
        .toList(growable: false);
  }

  /// Fetches a single Firestore document by relative path (e.g. `meta/demo`).
  Future<Map<String, dynamic>?> getDocument(String documentPath) async {
    final cleanPath =
        documentPath.startsWith('/') ? documentPath.substring(1) : documentPath;
    final uri = Uri.parse('${config.firestoreDocumentsBaseUrl}/$cleanPath');
    final headers = await _headers();
    final resp = await _http.get(uri, headers: headers).timeout(timeout);
    if (resp.statusCode == 404) return null;
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw StateError(
        'Firestore REST GET $cleanPath failed with HTTP ${resp.statusCode}',
      );
    }
    final decoded = jsonDecode(resp.body);
    if (decoded is! Map) return null;
    return decodeDocument(
      decoded.map((k, v) => MapEntry(k.toString(), v)),
    );
  }

  Future<Map<String, String>> _headers() async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (tokenProvider != null) {
      final token = await tokenProvider!();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  /// Decodes a Firestore REST document payload (`{ name, fields }`) into a
  /// plain JSON map, attaching the document ID under `'id'` if not present.
  static Map<String, dynamic> decodeDocument(Map<String, dynamic> doc) {
    final result = <String, dynamic>{};
    final name = doc['name']?.toString();
    if (name != null && name.contains('/')) {
      result['id'] = name.split('/').last;
    }
    final fields = doc['fields'];
    if (fields is Map) {
      for (final entry in fields.entries) {
        result[entry.key.toString()] = decodeValue(entry.value);
      }
    }
    return result;
  }

  /// Decodes a single Firestore REST typed value wrapper.
  static dynamic decodeValue(dynamic wrapped) {
    if (wrapped is! Map) return wrapped;
    if (wrapped.containsKey('nullValue')) return null;
    if (wrapped.containsKey('stringValue')) return wrapped['stringValue'];
    if (wrapped.containsKey('booleanValue')) return wrapped['booleanValue'];
    if (wrapped.containsKey('timestampValue')) return wrapped['timestampValue'];
    if (wrapped.containsKey('integerValue')) {
      final raw = wrapped['integerValue'];
      return raw is int ? raw : int.tryParse(raw.toString()) ?? 0;
    }
    if (wrapped.containsKey('doubleValue')) {
      final raw = wrapped['doubleValue'];
      return raw is double ? raw : double.tryParse(raw.toString()) ?? 0.0;
    }
    if (wrapped.containsKey('geoPointValue')) {
      final gp = wrapped['geoPointValue'];
      if (gp is Map) {
        return {
          'lat': (gp['latitude'] as num?)?.toDouble() ?? 0.0,
          'lon': (gp['longitude'] as num?)?.toDouble() ?? 0.0,
        };
      }
      return null;
    }
    if (wrapped.containsKey('arrayValue')) {
      final arr = wrapped['arrayValue'];
      if (arr is Map && arr['values'] is List) {
        return (arr['values'] as List).map(decodeValue).toList();
      }
      return const <dynamic>[];
    }
    if (wrapped.containsKey('mapValue')) {
      final mapVal = wrapped['mapValue'];
      if (mapVal is Map && mapVal['fields'] is Map) {
        final fields = mapVal['fields'] as Map;
        return fields.map(
          (k, v) => MapEntry(k.toString(), decodeValue(v)),
        );
      }
      return const <String, dynamic>{};
    }
    return null;
  }

  void close() {
    _http.close();
  }
}
