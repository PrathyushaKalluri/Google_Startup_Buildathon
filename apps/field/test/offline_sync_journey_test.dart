import 'package:flutter_test/flutter_test.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_field/src/technician/offline_outbox.dart';

class _RecordingFieldApi extends KwApiClient {
  _RecordingFieldApi() : super(config: const KwConfig(demoMode: true));

  final List<String> replayed = [];
  final List<String?> idempotencyKeys = [];

  @override
  Future<Visit> checkIn(
    String visitId, {
    required double lat,
    required double lon,
    String? idempotencyKey,
  }) async {
    replayed.add('check_in:$visitId');
    idempotencyKeys.add(idempotencyKey);
    return Visit(
      id: visitId,
      technicianId: 'tech_1',
      plannedStart: '2026-11-21T10:00:00Z',
      plannedEnd: '2026-11-21T12:00:00Z',
      checkInAt: '2026-11-21T10:05:00Z',
    );
  }

  @override
  Future<Map<String, dynamic>> recordPartsUsed(
    String visitId, {
    required List<DebriefPartUsed> parts,
    String? idempotencyKey,
  }) async {
    replayed.add('parts_used:$visitId:${parts.map((p) => p.partNo).join(",")}');
    idempotencyKeys.add(idempotencyKey);
    return {'status': 'ok'};
  }

  @override
  Future<Visit> recordOutcome(
    String visitId, {
    required String outcome,
    String? notes,
    String? idempotencyKey,
  }) async {
    replayed.add('outcome:$visitId:$outcome');
    idempotencyKeys.add(idempotencyKey);
    return Visit(
      id: visitId,
      technicianId: 'tech_1',
      plannedStart: '2026-11-21T10:00:00Z',
      plannedEnd: '2026-11-21T12:00:00Z',
      outcome: outcome,
    );
  }
}

void main() {
  test('Journey: Technician offline outbox queues check-in, parts-used, and outcome then syncs in FIFO order with idempotency keys', () async {
    final api = _RecordingFieldApi();
    final outbox = OfflineOutboxController(api: api);
    addTearDown(outbox.dispose);

    // 1. Go offline (basement / lift)
    outbox.setOffline(true);
    expect(outbox.isOffline, isTrue);

    final r1 = await outbox.submitCheckIn(visitId: 'vis-c03', lat: 17.494, lon: 78.399);
    final r2 = await outbox.submitPartsUsed(
      visitId: 'vis-c03',
      parts: const [DebriefPartUsed(partNo: 'WC-DP-85', quantity: 1)],
    );
    final r3 = await outbox.submitOutcome(
      visitId: 'vis-c03',
      outcome: 'fixed',
      notes: 'Removed coin from drain pump housing and tested spin.',
    );

    expect(r1.queued, isTrue);
    expect(r2.queued, isTrue);
    expect(r3.queued, isTrue);
    expect(outbox.pendingCount, 3);
    expect(api.replayed, isEmpty);

    // 2. Back online -> sync outbox
    outbox.setOffline(false);
    final synced = await outbox.syncNow();

    expect(synced, 3);
    expect(outbox.pendingCount, 0);
    expect(api.replayed, [
      'check_in:vis-c03',
      'parts_used:vis-c03:WC-DP-85',
      'outcome:vis-c03:fixed',
    ]);
    expect(api.idempotencyKeys.every((k) => k != null && k.isNotEmpty), isTrue);
  });
}
