import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import '../field_l10n.dart';

/// Action kinds supported by the offline-first technician outbox.
enum OutboxActionKind {
  checkIn('check-in'),
  partsUsed('parts-used'),
  outcome('outcome'),
  debrief('debrief');

  const OutboxActionKind(this.wireName);

  final String wireName;
}

/// Immutable queued action waiting to sync to the Keepwell backend.
@immutable
class QueuedFieldAction {
  const QueuedFieldAction({
    required this.id,
    required this.visitId,
    required this.kind,
    required this.summary,
    required this.payload,
    required this.queuedAt,
    required this.idempotencyKey,
  });

  final String id;
  final String visitId;
  final OutboxActionKind kind;
  final String summary;
  final Map<String, dynamic> payload;
  final DateTime queuedAt;
  final String idempotencyKey;
}

/// Result of submitting a technician field action through [OfflineOutboxController].
@immutable
class OutboxResult<T> {
  const OutboxResult({
    required this.queued,
    this.data,
    this.queuedAction,
  });

  final bool queued;
  final T? data;
  final QueuedFieldAction? queuedAction;
}

/// Persistent in-memory offline-first action outbox for field technicians.
///
/// Allows simulated offline operation so technicians can complete check-in,
/// parts-used recording, outcome logging, and close-out debriefs without
/// connectivity, then flush queued actions idempotently when back online.
class OfflineOutboxController extends ChangeNotifier {
  OfflineOutboxController({
    required this.api,
    bool initialOffline = false,
  }) : _isOffline = initialOffline;

  final KwApiClient api;

  bool _isOffline;
  bool _isSyncing = false;
  int _seq = 0;
  final List<QueuedFieldAction> _queue = <QueuedFieldAction>[];
  String? _lastSyncMessage;
  String? _lastSyncError;
  DateTime? _lastSyncedAt;

  bool get isOffline => _isOffline;
  bool get isSyncing => _isSyncing;
  List<QueuedFieldAction> get pendingActions =>
      List<QueuedFieldAction>.unmodifiable(_queue);
  int get pendingCount => _queue.length;
  String? get lastSyncMessage => _lastSyncMessage;
  String? get lastSyncError => _lastSyncError;
  DateTime? get lastSyncedAt => _lastSyncedAt;

  void setOffline(bool offline) {
    if (_isOffline == offline) return;
    _isOffline = offline;
    _lastSyncError = null;
    notifyListeners();
  }

  void toggleOffline() => setOffline(!_isOffline);

  String _nextKey(OutboxActionKind kind, String visitId) {
    _seq += 1;
    return 'field-${kind.wireName}-$visitId-$_seq';
  }

  QueuedFieldAction _enqueue({
    required String visitId,
    required OutboxActionKind kind,
    required String summary,
    required Map<String, dynamic> payload,
  }) {
    final key = _nextKey(kind, visitId);
    final action = QueuedFieldAction(
      id: key,
      visitId: visitId,
      kind: kind,
      summary: summary,
      payload: Map<String, dynamic>.unmodifiable(payload),
      queuedAt: DateTime.now(),
      idempotencyKey: key,
    );
    _queue.add(action);
    _lastSyncMessage = null;
    _lastSyncError = null;
    notifyListeners();
    return action;
  }

  Future<OutboxResult<Visit>> submitCheckIn({
    required String visitId,
    required double lat,
    required double lon,
  }) async {
    if (_isOffline) {
      final queued = _enqueue(
        visitId: visitId,
        kind: OutboxActionKind.checkIn,
        summary: 'Check-in (${lat.toStringAsFixed(4)}, ${lon.toStringAsFixed(4)})',
        payload: {'lat': lat, 'lon': lon},
      );
      return OutboxResult<Visit>(queued: true, queuedAction: queued);
    }

    final visit = await api.checkIn(
      visitId,
      lat: lat,
      lon: lon,
      idempotencyKey: _nextKey(OutboxActionKind.checkIn, visitId),
    );
    return OutboxResult<Visit>(queued: false, data: visit);
  }

  Future<OutboxResult<Map<String, dynamic>>> submitPartsUsed({
    required String visitId,
    required List<DebriefPartUsed> parts,
  }) async {
    if (_isOffline) {
      final totalQty = parts.fold<int>(0, (sum, p) => sum + p.quantity);
      final queued = _enqueue(
        visitId: visitId,
        kind: OutboxActionKind.partsUsed,
        summary: 'Parts used ($totalQty item${totalQty == 1 ? '' : 's'})',
        payload: {
          'parts': parts.map((p) => p.toJson()).toList(),
        },
      );
      return OutboxResult<Map<String, dynamic>>(
        queued: true,
        queuedAction: queued,
      );
    }

    final resp = await api.recordPartsUsed(
      visitId,
      parts: parts,
      idempotencyKey: _nextKey(OutboxActionKind.partsUsed, visitId),
    );
    return OutboxResult<Map<String, dynamic>>(queued: false, data: resp);
  }

  Future<OutboxResult<Visit>> submitOutcome({
    required String visitId,
    required String outcome,
    String notes = '',
  }) async {
    if (_isOffline) {
      final queued = _enqueue(
        visitId: visitId,
        kind: OutboxActionKind.outcome,
        summary: 'Visit outcome: $outcome',
        payload: {'outcome': outcome, 'notes': notes},
      );
      return OutboxResult<Visit>(queued: true, queuedAction: queued);
    }

    final visit = await api.recordOutcome(
      visitId,
      outcome: outcome,
      notes: notes,
      idempotencyKey: _nextKey(OutboxActionKind.outcome, visitId),
    );
    return OutboxResult<Visit>(queued: false, data: visit);
  }

  Future<OutboxResult<Debrief>> submitDebrief({
    required String visitId,
    required String mediaRef,
    required String language,
  }) async {
    if (_isOffline) {
      final queued = _enqueue(
        visitId: visitId,
        kind: OutboxActionKind.debrief,
        summary: 'Voice debrief ($language)',
        payload: {'media_ref': mediaRef, 'language': language},
      );
      return OutboxResult<Debrief>(queued: true, queuedAction: queued);
    }

    final debrief = await api.submitDebrief(
      visitId,
      mediaRef: mediaRef,
      language: language,
      idempotencyKey: _nextKey(OutboxActionKind.debrief, visitId),
    );
    return OutboxResult<Debrief>(queued: false, data: debrief);
  }

  /// Flushes all queued actions in FIFO order when online.
  /// Returns the number of actions successfully synced.
  Future<int> syncNow() async {
    if (_isOffline || _isSyncing || _queue.isEmpty) {
      return 0;
    }

    _isSyncing = true;
    _lastSyncError = null;
    notifyListeners();

    var synced = 0;
    try {
      while (_queue.isNotEmpty) {
        final action = _queue.first;
        await _dispatchAction(action);
        _queue.removeAt(0);
        synced += 1;
        notifyListeners();
      }
      _lastSyncedAt = DateTime.now();
      _lastSyncMessage =
          'Synced $synced queued action${synced == 1 ? '' : 's'}';
    } catch (e) {
      _lastSyncError = 'Sync paused after $synced action(s): $e';
    } finally {
      _isSyncing = false;
      notifyListeners();
    }
    return synced;
  }

  Future<void> _dispatchAction(QueuedFieldAction action) async {
    switch (action.kind) {
      case OutboxActionKind.checkIn:
        await api.checkIn(
          action.visitId,
          lat: (action.payload['lat'] as num).toDouble(),
          lon: (action.payload['lon'] as num).toDouble(),
          idempotencyKey: action.idempotencyKey,
        );
      case OutboxActionKind.partsUsed:
        final rawList = action.payload['parts'] as List<dynamic>? ?? const [];
        final parts = rawList
            .whereType<Map<String, dynamic>>()
            .map(DebriefPartUsed.fromJson)
            .toList();
        await api.recordPartsUsed(
          action.visitId,
          parts: parts,
          idempotencyKey: action.idempotencyKey,
        );
      case OutboxActionKind.outcome:
        await api.recordOutcome(
          action.visitId,
          outcome: (action.payload['outcome'] ?? 'fixed').toString(),
          notes: (action.payload['notes'] ?? '').toString(),
          idempotencyKey: action.idempotencyKey,
        );
      case OutboxActionKind.debrief:
        await api.submitDebrief(
          action.visitId,
          mediaRef: (action.payload['media_ref'] ?? '').toString(),
          language: (action.payload['language'] ?? 'en').toString(),
          idempotencyKey: action.idempotencyKey,
        );
    }
  }
}

/// Honest connectivity & outbox sync status banner displayed across the
/// Technician Shell.
class OfflineSyncBanner extends StatelessWidget {
  const OfflineSyncBanner({
    super.key,
    required this.outbox,
    this.onSynced,
  });

  final OfflineOutboxController outbox;
  final VoidCallback? onSynced;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: outbox,
      builder: (context, _) {
        final theme = Theme.of(context);
        final kw = theme.kwColors;
        final strings = FieldStrings.of(context);
        final count = outbox.pendingCount;
        final isOffline = outbox.isOffline;

        final role = isOffline
            ? kw.needsChecking
            : count > 0
                ? kw.standard
                : kw.verified;

        final statusText = isOffline
            ? (count > 0
                ? 'Offline — $count action${count == 1 ? '' : 's'} queued'
                : strings.offlineNoQueue)
            : count > 0
                ? '${strings.onlineStatus} — $count action${count == 1 ? '' : 's'} queued'
                : outbox.lastSyncMessage ?? strings.onlineStatus;

        return Semantics(
          liveRegion: true,
          container: true,
          label: statusText,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.md,
              vertical: KwSpacing.sm,
            ),
            decoration: BoxDecoration(
              color: role.container,
              border: Border(
                bottom: BorderSide(
                  color: role.accent.withValues(alpha: 0.45),
                ),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: KwSpacing.sm,
                  runSpacing: KwSpacing.xs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  alignment: WrapAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          isOffline
                              ? Icons.cloud_off_rounded
                              : count > 0
                                  ? Icons.cloud_upload_rounded
                                  : Icons.cloud_done_rounded,
                          size: 20,
                          color: role.onContainer,
                        ),
                        const SizedBox(width: KwSpacing.xs),
                        Flexible(
                          child: Text(
                            statusText,
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: role.onContainer,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (!isOffline && count > 0) ...[
                          FilledButton.tonalIcon(
                            key: const Key('kw_sync_now_button'),
                            onPressed: outbox.isSyncing
                                ? null
                                : () async {
                                    final synced = await outbox.syncNow();
                                    if (synced > 0) {
                                      onSynced?.call();
                                    }
                                  },
                            icon: outbox.isSyncing
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.sync_rounded, size: 18),
                            label: Text(strings.syncNow),
                          ),
                          const SizedBox(width: KwSpacing.xs),
                        ],
                        MergeSemantics(
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                strings.simulateOffline,
                                style: theme.textTheme.labelMedium?.copyWith(
                                  color: role.onContainer,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Semantics(
                                label: strings.simulateOffline,
                                child: Switch(
                                  key: const Key('kw_offline_toggle'),
                                  value: isOffline,
                                  onChanged: outbox.setOffline,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                if (outbox.lastSyncError != null) ...[
                  const SizedBox(height: KwSpacing.xxs),
                  Text(
                    outbox.lastSyncError!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: kw.safety.onContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
                if (count > 0) ...[
                  const SizedBox(height: KwSpacing.xs),
                  Wrap(
                    spacing: KwSpacing.xs,
                    runSpacing: KwSpacing.xxs,
                    children: [
                      for (final action in outbox.pendingActions)
                        Chip(
                          visualDensity: VisualDensity.compact,
                          avatar: const Icon(Icons.schedule_send_rounded, size: 16),
                          label: Text(action.summary),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
