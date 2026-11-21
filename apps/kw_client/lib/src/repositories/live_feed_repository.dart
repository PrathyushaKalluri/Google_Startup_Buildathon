import 'dart:async';

import '../api/kw_api_client.dart';
import '../config.dart';
import '../models/models.dart';
import 'firestore_client.dart';

/// Reactive repository exposing live streams of feed events, ticket boards,
/// conversation turns, and household WhatsApp threads (Contract §6 & §8).
///
/// Uses [KwFirestoreClient] when Firestore (or its emulator) is configured and
/// automatically falls back to [KwApiClient] REST polling when Firestore is
/// unavailable, so Flutter Web and pure-Dart tests work with zero crashes.
class LiveFeedRepository {
  LiveFeedRepository({
    required this.config,
    required this.apiClient,
    KwFirestoreClient? firestoreClient,
    KwTokenProvider? tokenProvider,
  }) : _firestore = firestoreClient ??
            KwFirestoreClient(
              config: config,
              tokenProvider: tokenProvider,
            );

  final KwConfig config;
  final KwApiClient apiClient;
  final KwFirestoreClient _firestore;

  /// True when Firestore reads should be queried directly (either against the
  /// local emulator or against production Firestore when `DEMO_MODE=false` and
  /// `FIREBASE_PROJECT_ID` is configured).
  bool get shouldUseFirestore =>
      config.useFirestoreEmulator ||
      (!config.demoMode && config.firebaseProjectId.trim().isNotEmpty);

  /// Watches live events in `centres/{centreId}/feed`.
  ///
  /// Reads directly from Firestore when [shouldUseFirestore] is true (no mock
  /// REST server needed for live data), falling back to REST only in demo mode
  /// when Firestore is not configured.
  Stream<List<LiveEvent>> watchFeed(
    String centreId, {
    String? centreKey,
    Duration pollInterval = const Duration(seconds: 2),
  }) {
    return _pollingStream<List<LiveEvent>>(
      pollInterval: pollInterval,
      fetcher: () async {
        if (shouldUseFirestore && centreId.isNotEmpty) {
          try {
            final docs = await _firestore.listCollection(
              'centres/$centreId/feed',
            );
            final events = docs.map(LiveEvent.fromJson).toList()
              ..sort((a, b) => b.at.compareTo(a.at));
            return events;
          } catch (_) {
            if (!config.demoMode) rethrow;
          }
        }
        return _fetchFeedFallbackFromRest(
          centreId: centreId,
          centreKey: centreKey,
        );
      },
    );
  }

  /// Watches the live ticket board for a centre.
  Stream<List<TicketCard>> watchTickets({
    String? centreId,
    String? centreKey,
    String? status,
    String? urgencyClass,
    Duration pollInterval = const Duration(seconds: 3),
  }) {
    return _pollingStream<List<TicketCard>>(
      pollInterval: pollInterval,
      fetcher: () async {
        if (shouldUseFirestore &&
            centreId != null &&
            centreId.isNotEmpty &&
            status == null &&
            urgencyClass == null) {
          try {
            final docs = await _firestore.listCollection(
              'centres/$centreId/tickets',
            );
            return docs.map(TicketCard.fromJson).toList();
          } catch (_) {
            if (!config.demoMode) rethrow;
          }
        }
        final page = await apiClient.listTickets(
          centreId: centreId,
          centreKey: centreKey,
          status: status,
          urgencyClass: urgencyClass,
        );
        return page.items;
      },
    );
  }

  /// Watches turns in `centres/{centreId}/conversations/{conversationId}/turns`.
  Stream<List<ConversationTurn>> watchConversationTurns(
    String centreId,
    String conversationId, {
    Duration pollInterval = const Duration(seconds: 1),
  }) {
    return _pollingStream<List<ConversationTurn>>(
      pollInterval: pollInterval,
      fetcher: () async {
        if (shouldUseFirestore) {
          try {
            final docs = await _firestore.listCollection(
              'centres/$centreId/conversations/$conversationId/turns',
            );
            final turns = docs.map(ConversationTurn.fromJson).toList()
              ..sort((a, b) => a.at.compareTo(b.at));
            return turns;
          } catch (_) {
            // Return empty list if unavailable.
          }
        }
        return const <ConversationTurn>[];
      },
    );
  }

  /// Watches messages in `households/{householdId}/whatsapp_thread`.
  Stream<List<WhatsAppMessage>> watchWhatsAppThread(
    String householdId, {
    Duration pollInterval = const Duration(seconds: 2),
  }) {
    return _pollingStream<List<WhatsAppMessage>>(
      pollInterval: pollInterval,
      fetcher: () async {
        if (shouldUseFirestore) {
          try {
            final docs = await _firestore.listCollection(
              'households/$householdId/whatsapp_thread',
            );
            final messages = docs.map(WhatsAppMessage.fromJson).toList()
              ..sort((a, b) => a.at.compareTo(b.at));
            return messages;
          } catch (_) {
            // Return empty list if unavailable.
          }
        }
        return const <WhatsAppMessage>[];
      },
    );
  }

  Future<List<LiveEvent>> _fetchFeedFallbackFromRest({
    required String centreId,
    String? centreKey,
  }) async {
    final page = await apiClient.listTickets(
      centreId: centreId.isNotEmpty ? centreId : null,
      centreKey: centreKey,
      limit: 20,
    );
    final events = <LiveEvent>[];
    for (final card in page.items) {
      events.add(
        LiveEvent(
          id: 'rest_${card.id}',
          at: card.updatedAt,
          centreId: card.centreId,
          ticketId: card.id,
          type: card.safetyFlag ? 'safety_stop_sent' : 'urgency_assessed',
          actor: 'agent',
          title: '${card.household.displayName} — ${card.complaintSummary}',
          detail: 'Status: ${card.status} • Urgency: ${card.urgencyClass}',
          payload: {
            'urgency_class': card.urgencyClass,
            'safety_flag': card.safetyFlag,
            'status': card.status,
          },
        ),
      );
    }
    events.sort((a, b) => b.at.compareTo(a.at));
    return events;
  }

  Stream<T> _pollingStream<T>({
    required Duration pollInterval,
    required Future<T> Function() fetcher,
  }) {
    late final StreamController<T> controller;
    Timer? timer;
    var active = false;
    var inFlight = false;

    Future<void> pollOnce() async {
      if (!active || inFlight || controller.isClosed) return;
      inFlight = true;
      try {
        final value = await fetcher();
        if (active && !controller.isClosed) {
          controller.add(value);
        }
      } catch (e, st) {
        if (active && !controller.isClosed) {
          controller.addError(e, st);
        }
      } finally {
        inFlight = false;
      }
    }

    controller = StreamController<T>(
      onListen: () {
        active = true;
        unawaited(pollOnce());
        timer = Timer.periodic(pollInterval, (_) => unawaited(pollOnce()));
      },
      onCancel: () async {
        active = false;
        timer?.cancel();
        timer = null;
      },
    );

    return controller.stream;
  }
}
