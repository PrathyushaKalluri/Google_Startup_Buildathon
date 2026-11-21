import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/models.dart';
import 'embedded_snapshot.dart';

/// Callback returning the current Firebase ID token (or demo token) if signed in.
typedef KwTokenProvider = FutureOr<String?> Function();

/// Typed pure-Dart REST client covering every Keepwell API v1 endpoint (Contract §5.2).
class KwApiClient {
  KwApiClient({
    required this.config,
    http.Client? httpClient,
    this.tokenProvider,
    this.timeout = const Duration(seconds: 15),
    this.maxRetries = 2,
    this.retryBaseDelay = const Duration(milliseconds: 250),
  }) : _http = httpClient ?? http.Client();

  final KwConfig config;
  final http.Client _http;
  final KwTokenProvider? tokenProvider;
  final Duration timeout;
  final int maxRetries;
  final Duration retryBaseDelay;

  // ---------------------------------------------------------------------------
  // Meta & Health
  // ---------------------------------------------------------------------------

  Future<Map<String, dynamic>> healthz() => _requestJsonMap(
        'GET',
        '/healthz',
        useRootUri: true,
        includeAuth: false,
      );

  Future<Map<String, dynamic>> readyz() => _requestJsonMap(
        'GET',
        '/readyz',
        useRootUri: true,
        includeAuth: false,
      );

  Future<Map<String, dynamic>> version() => _requestJsonMap(
        'GET',
        '/meta/version',
        includeAuth: false,
      );

  // ---------------------------------------------------------------------------
  // Centre Console
  // ---------------------------------------------------------------------------

  Future<PagedList<TicketCard>> listTickets({
    String? status,
    String? urgencyClass,
    String? trigger,
    String? q,
    String? centreId,
    String? centreKey,
    String? cursor,
    int? limit,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/tickets',
      query: {
        if (status != null && status.isNotEmpty) 'status': status,
        if (urgencyClass != null && urgencyClass.isNotEmpty)
          'urgency_class': urgencyClass,
        if (trigger != null && trigger.isNotEmpty) 'trigger': trigger,
        if (q != null && q.isNotEmpty) 'q': q,
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
        if (limit != null) 'limit': limit.toString(),
      },
    );
    return PagedList.fromJson(data, TicketCard.fromJson);
  }

  Future<TicketDetail> getTicket(String id) async {
    final data = await _requestJsonMap('GET', '/tickets/$id');
    return TicketDetail.fromJson(data);
  }

  Future<TicketDetail> reclassifyUrgency(
    String id, {
    required String urgencyClass,
    required String reason,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$id/reclassify-urgency',
      body: {
        'class': urgencyClass,
        'reason': reason,
      },
      idempotencyKey: idempotencyKey,
    );
    return TicketDetail.fromJson(data);
  }

  Future<TicketDetail> reassignTicket(
    String id, {
    required String technicianId,
    required String slotStart,
    required String slotEnd,
    required String reason,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$id/reassign',
      body: {
        'technician_id': technicianId,
        'slot_start': slotStart,
        'slot_end': slotEnd,
        'reason': reason,
      },
      idempotencyKey: idempotencyKey,
    );
    return TicketDetail.fromJson(data);
  }

  Future<TicketDetail> rerunDiagnosis(
    String id, {
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$id/rerun-diagnosis',
      idempotencyKey: idempotencyKey,
    );
    return TicketDetail.fromJson(data);
  }

  Future<TicketDetail> returnToBrand(
    String id, {
    required String reason,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$id/return-to-brand',
      body: {'reason': reason},
      idempotencyKey: idempotencyKey,
    );
    return TicketDetail.fromJson(data);
  }

  Future<TimelineEvent> sendCentreMessage(
    String id, {
    required String text,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$id/message',
      body: {'text': text},
      idempotencyKey: idempotencyKey,
    );
    return TimelineEvent.fromJson(data);
  }

  Future<CentreOverview> getCentreOverview({
    String? centreId,
    String? centreKey,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/overview',
      query: {
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
      },
    );
    return CentreOverview.fromJson(data);
  }

  Future<PagedList<TechnicianSummary>> getCentreTechnicians({
    String? centreId,
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/technicians',
      query: {
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, TechnicianSummary.fromJson);
  }

  Future<PagedList<Map<String, dynamic>>> getCentreCalendar({
    String? date,
    String? centreId,
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/calendar',
      query: {
        if (date != null && date.isNotEmpty) 'date': date,
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<PagedList<Map<String, dynamic>>> getCentreStock({
    String? centreId,
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/stock',
      query: {
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<PagedList<Map<String, dynamic>>> getCentrePrices({
    String? centreId,
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/prices',
      query: {
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<PagedList<Map<String, dynamic>>> getCentreOverrides({
    String? centreId,
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/centre/overrides',
      query: {
        if (centreId != null && centreId.isNotEmpty) 'centre_id': centreId,
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<PagedList<TimelineEvent>> getApplianceTimeline(
    String id, {
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/appliances/$id/timeline',
      query: {
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, TimelineEvent.fromJson);
  }

  Future<PagedList<SafeFixEntry>> listSafeFixes({String? cursor}) async {
    final data = await _requestJsonMap(
      'GET',
      '/safefix',
      query: {
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, SafeFixEntry.fromJson);
  }

  Future<SafeFixEntry> getSafeFix(String code) async {
    final data = await _requestJsonMap('GET', '/safefix/$code');
    return SafeFixEntry.fromJson(data);
  }

  // ---------------------------------------------------------------------------
  // Technician
  // ---------------------------------------------------------------------------

  Future<PagedList<Map<String, dynamic>>> getMyJobs({
    String? date,
    String? technicianId,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/technicians/me/jobs',
      query: {
        if (date != null && date.isNotEmpty) 'date': date,
        if (technicianId != null && technicianId.isNotEmpty)
          'technician_id': technicianId,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<Map<String, dynamic>> getVisit(String id) =>
      _requestJsonMap('GET', '/visits/$id');

  Future<Visit> checkIn(
    String id, {
    required double lat,
    required double lon,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/visits/$id/check-in',
      body: {'lat': lat, 'lon': lon},
      idempotencyKey: idempotencyKey,
    );
    return Visit.fromJson(data);
  }

  Future<Map<String, dynamic>> recordPartsUsed(
    String id, {
    required List<DebriefPartUsed> parts,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/visits/$id/parts-used',
      body: {'parts': parts.map((p) => p.toJson()).toList()},
      idempotencyKey: idempotencyKey,
    );
  }

  Future<Visit> recordOutcome(
    String id, {
    required String outcome,
    String notes = '',
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/visits/$id/outcome',
      body: {'outcome': outcome, 'notes': notes},
      idempotencyKey: idempotencyKey,
    );
    return Visit.fromJson(data);
  }

  Future<Map<String, dynamic>> getMediaUploadUrl(
    String id, {
    required String filename,
    required String mimeType,
  }) {
    return _requestJsonMap(
      'POST',
      '/visits/$id/media/upload-url',
      body: {'filename': filename, 'mime_type': mimeType},
    );
  }

  Future<Quote> createFirmQuote(
    String ticketId, {
    required List<QuoteLine> lines,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/tickets/$ticketId/quotes',
      body: {'lines': lines.map((l) => l.toJson()).toList()},
      idempotencyKey: idempotencyKey,
    );
    return Quote.fromJson(data);
  }

  Future<Debrief> submitDebrief(
    String visitId, {
    required String mediaRef,
    required String language,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/visits/$visitId/debrief',
      body: {'media_ref': mediaRef, 'language': language},
      idempotencyKey: idempotencyKey,
    );
    return Debrief.fromJson(data);
  }

  Future<Debrief> confirmDebrief(
    String visitId, {
    required DebriefExtracted extracted,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/visits/$visitId/debrief/confirm',
      body: {'extracted': extracted.toJson()},
      idempotencyKey: idempotencyKey,
    );
    return Debrief.fromJson(data);
  }

  Future<Map<String, dynamic>> requestCloseOtp(
    String visitId, {
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/visits/$visitId/close/request-otp',
      idempotencyKey: idempotencyKey,
    );
  }

  Future<Map<String, dynamic>> confirmCloseOtp(
    String visitId, {
    required String otpRef,
    required String code,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/visits/$visitId/close/confirm',
      body: {'otp_ref': otpRef, 'code': code},
      idempotencyKey: idempotencyKey,
    );
  }

  Future<Map<String, dynamic>> postLocation({
    required double lat,
    required double lon,
    String? at,
    String? technicianId,
  }) {
    return _requestJsonMap(
      'POST',
      '/technicians/me/location',
      body: {
        'lat': lat,
        'lon': lon,
        if (at != null) 'at': at,
        if (technicianId != null) 'technician_id': technicianId,
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Parts Centre
  // ---------------------------------------------------------------------------

  Future<PagedList<Map<String, dynamic>>> listPartsRequests({
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/partscentre/requests',
      query: {
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, (m) => m);
  }

  Future<Map<String, dynamic>> acceptPartsRequest(
    String id, {
    String? idempotencyKey,
  }) =>
      _requestJsonMap(
        'POST',
        '/partscentre/requests/$id/accept',
        idempotencyKey: idempotencyKey,
      );

  Future<Map<String, dynamic>> readyPartsRequest(
    String id, {
    String? idempotencyKey,
  }) =>
      _requestJsonMap(
        'POST',
        '/partscentre/requests/$id/ready',
        idempotencyKey: idempotencyKey,
      );

  Future<Map<String, dynamic>> handoverPartsRequest(
    String id, {
    String? idempotencyKey,
  }) =>
      _requestJsonMap(
        'POST',
        '/partscentre/requests/$id/handover',
        idempotencyKey: idempotencyKey,
      );

  Future<Map<String, dynamic>> updatePartsStock(
    Map<String, dynamic> items, {
    String? idempotencyKey,
  }) =>
      _requestJsonMap(
        'PUT',
        '/partscentre/stock',
        body: items,
        idempotencyKey: idempotencyKey,
      );

  // ---------------------------------------------------------------------------
  // Brand & Retailer
  // ---------------------------------------------------------------------------

  Future<PagedList<TicketCard>> listBrandRequests({
    String? brand,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/brand/requests',
      query: {
        if (brand != null && brand.isNotEmpty) 'brand': brand,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, TicketCard.fromJson);
  }

  Future<Map<String, dynamic>> getBrandAnalytics({String? brand}) {
    return _requestJsonMap(
      'GET',
      '/brand/analytics',
      query: {
        if (brand != null && brand.isNotEmpty) 'brand': brand,
      },
    );
  }

  Future<Map<String, dynamic>> submitBrandRequest(
    Map<String, dynamic> payload, {
    required String apiKey,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/channels/brand/requests',
      body: payload,
      includeAuth: false,
      extraHeaders: {'X-Keepwell-Key': apiKey},
      idempotencyKey: idempotencyKey,
    );
  }

  Future<Map<String, dynamic>> submitRetailerHandover(
    Map<String, dynamic> payload, {
    required String apiKey,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/channels/retailer/handovers',
      body: payload,
      includeAuth: false,
      extraHeaders: {'X-Keepwell-Key': apiKey},
      idempotencyKey: idempotencyKey,
    );
  }

  // ---------------------------------------------------------------------------
  // Public Household (signed magic token)
  // ---------------------------------------------------------------------------

  Future<Map<String, dynamic>> getPublicHome(String token) =>
      _requestJsonMap('GET', '/public/home/$token', includeAuth: false);

  Future<Map<String, dynamic>> getPublicQuote(String token) =>
      _requestJsonMap('GET', '/public/quotes/$token', includeAuth: false);

  Future<Quote> approvePublicQuote(
    String token, {
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/public/quotes/$token/approve',
      includeAuth: false,
      idempotencyKey: idempotencyKey,
    );
    return Quote.fromJson(data);
  }

  Future<Map<String, dynamic>> confirmPublicOtp(
    String token, {
    required String code,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/public/otp/$token/confirm',
      body: {'code': code},
      includeAuth: false,
      idempotencyKey: idempotencyKey,
    );
  }

  Future<PaymentIntent> createPayIntent(
    String token, {
    required String method,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/public/quotes/$token/pay-intent',
      body: {'method': method},
      includeAuth: false,
      idempotencyKey: idempotencyKey,
    );
    return PaymentIntent.fromJson(data);
  }

  Future<PaymentIntent> getPublicPayment(String token) async {
    final data = await _requestJsonMap(
      'GET',
      '/public/quotes/$token/payment',
      includeAuth: false,
    );
    return PaymentIntent.fromJson(data);
  }

  Future<PaymentIntent> sandboxCompletePayment(
    String token, {
    required String paymentId,
    required String result,
    String? reason,
    String? idempotencyKey,
  }) async {
    final data = await _requestJsonMap(
      'POST',
      '/public/quotes/$token/payment/sandbox-complete',
      body: {
        'payment_id': paymentId,
        'result': result,
        if (reason != null) 'reason': reason,
      },
      includeAuth: false,
      idempotencyKey: idempotencyKey,
    );
    return PaymentIntent.fromJson(data);
  }

  Future<Map<String, dynamic>> createPublicSession(String magicToken) {
    return _requestJsonMap(
      'POST',
      '/public/session',
      body: {'magic_token': magicToken},
      includeAuth: false,
    );
  }

  // ---------------------------------------------------------------------------
  // Channels (WhatsApp Simulator)
  // ---------------------------------------------------------------------------

  Future<Map<String, dynamic>> sendWhatsAppSimulatorInbound({
    required String toNumber,
    required String fromPhone,
    required String senderProfileName,
    required List<Map<String, dynamic>> messages,
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/channels/whatsapp/simulator/inbound',
      body: {
        'to_number': toNumber,
        'from_phone': fromPhone,
        'sender_profile_name': senderProfileName,
        'messages': messages,
      },
      includeAuth: false,
      idempotencyKey: idempotencyKey,
    );
  }

  Future<Map<String, dynamic>> uploadWhatsAppSimulatorMedia(
    List<int> bytes, {
    String contentType = 'application/octet-stream',
  }) async {
    final uri = _buildUri('/channels/whatsapp/simulator/media');
    final resp = await _http
        .post(
          uri,
          headers: {'Content-Type': contentType},
          body: bytes,
        )
        .timeout(timeout);
    return _decodeMapResponse(resp);
  }

  // ---------------------------------------------------------------------------
  // Admin & Demo
  // ---------------------------------------------------------------------------

  Future<PagedList<DemoCase>> listDemoCases({String? cursor}) async {
    final data = await _requestJsonMap(
      'GET',
      '/admin/demo/cases',
      query: {
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, DemoCase.fromJson);
  }

  Future<Map<String, dynamic>> playDemoCase(
    String caseId, {
    String? idempotencyKey,
  }) {
    return _requestJsonMap(
      'POST',
      '/admin/demo/play-case',
      body: {'case_id': caseId},
      idempotencyKey: idempotencyKey,
    );
  }

  Future<PagedList<DemoHousehold>> listDemoHouseholds({
    String? centreKey,
    String? cursor,
  }) async {
    final data = await _requestJsonMap(
      'GET',
      '/admin/demo/households',
      query: {
        if (centreKey != null && centreKey.isNotEmpty) 'centre_key': centreKey,
        if (cursor != null && cursor.isNotEmpty) 'cursor': cursor,
      },
    );
    return PagedList.fromJson(data, DemoHousehold.fromJson);
  }

  Future<Map<String, dynamic>> resetDemo({String? idempotencyKey}) =>
      _requestJsonMap(
        'POST',
        '/admin/demo/reset',
        idempotencyKey: idempotencyKey,
      );

  Future<Map<String, dynamic>> rebuildProjection({String? idempotencyKey}) =>
      _requestJsonMap(
        'POST',
        '/admin/projection/rebuild',
        idempotencyKey: idempotencyKey,
      );

  // ---------------------------------------------------------------------------
  // Internal HTTP plumbing with retry & Contract §5 error envelope parsing
  // ---------------------------------------------------------------------------

  Uri _buildUri(
    String path, {
    Map<String, String>? query,
    bool useRootUri = false,
  }) {
    final base = useRootUri ? config.apiRootUri : config.apiBaseUri;
    final cleanBasePath = base.path.endsWith('/')
        ? base.path.substring(0, base.path.length - 1)
        : base.path;
    final cleanPath = path.startsWith('/') ? path : '/$path';
    return base.replace(
      path: '$cleanBasePath$cleanPath',
      queryParameters: (query != null && query.isNotEmpty) ? query : null,
    );
  }

  Future<Map<String, dynamic>> _requestJsonMap(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
    bool useRootUri = false,
    bool includeAuth = true,
    Map<String, String>? extraHeaders,
    String? idempotencyKey,
  }) async {
    final uri = _buildUri(path, query: query, useRootUri: useRootUri);
    final headers = <String, String>{
      'Accept': 'application/json',
      if (body != null) 'Content-Type': 'application/json',
      if (idempotencyKey != null && idempotencyKey.isNotEmpty)
        'Idempotency-Key': idempotencyKey,
      if (extraHeaders != null) ...extraHeaders,
    };

    if (includeAuth && tokenProvider != null) {
      final token = await tokenProvider!();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }

    final encodedBody = body != null ? jsonEncode(body) : null;
    final canRetry =
        method == 'GET' || (idempotencyKey != null && idempotencyKey.isNotEmpty);

    var attempt = 0;
    while (true) {
      attempt += 1;
      try {
        final req = http.Request(method, uri)..headers.addAll(headers);
        if (encodedBody != null) {
          req.body = encodedBody;
        }
        final streamed = await _http.send(req).timeout(timeout);
        final response = await http.Response.fromStream(streamed).timeout(timeout);

        if (response.statusCode >= 200 && response.statusCode < 300) {
          return _decodeMapResponse(response);
        }

        final retryAfter = int.tryParse(response.headers['retry-after'] ?? '');
        final apiError = _parseErrorEnvelope(response);
        final exception = KwApiException(
          statusCode: response.statusCode,
          error: apiError,
          retryAfterSeconds: retryAfter,
        );

        if (canRetry && exception.isTransient && attempt <= maxRetries) {
          final delay = retryAfter != null
              ? Duration(seconds: retryAfter)
              : retryBaseDelay * (1 << (attempt - 1));
          await Future<void>.delayed(delay);
          continue;
        }
        if (config.demoMode) {
          final snap = KwEmbeddedSnapshot.resolve(method, path, query, body);
          if (snap != null) return snap;
        }
        throw exception;
      } on KwApiException {
        rethrow;
      } on TimeoutException catch (e) {
        if (canRetry && attempt <= maxRetries) {
          await Future<void>.delayed(retryBaseDelay * (1 << (attempt - 1)));
          continue;
        }
        if (config.demoMode) {
          final snap = KwEmbeddedSnapshot.resolve(method, path, query, body);
          if (snap != null) return snap;
        }
        throw KwApiException(
          statusCode: 504,
          error: KwApiError(
            code: 'request_timeout',
            message: e.message ?? 'Request timed out after ${timeout.inSeconds}s',
          ),
        );
      } on Object catch (e) {
        if (canRetry && attempt <= maxRetries) {
          await Future<void>.delayed(retryBaseDelay * (1 << (attempt - 1)));
          continue;
        }
        if (config.demoMode) {
          final snap = KwEmbeddedSnapshot.resolve(method, path, query, body);
          if (snap != null) return snap;
        }
        throw KwApiException(
          statusCode: 503,
          error: KwApiError(
            code: 'network_error',
            message: e.toString(),
          ),
        );
      }
    }
  }

  Map<String, dynamic> _decodeMapResponse(http.Response response) {
    if (response.body.trim().isEmpty) {
      return const {};
    }
    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    if (decoded is Map) {
      return decoded.map((k, v) => MapEntry(k.toString(), v));
    }
    return {'data': decoded};
  }

  KwApiError _parseErrorEnvelope(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map) {
        return KwApiError.fromJson(
          decoded.map((k, v) => MapEntry(k.toString(), v)),
        );
      }
    } catch (_) {
      // Fall through to generic HTTP error.
    }
    return KwApiError(
      code: 'http_${response.statusCode}',
      message: response.reasonPhrase ?? 'HTTP ${response.statusCode}',
    );
  }

  void close() {
    _http.close();
  }
}
