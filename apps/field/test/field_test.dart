import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_field/src/field_app.dart';

class _FakeKwApiClient extends KwApiClient {
  _FakeKwApiClient() : super(config: const KwConfig());

  final List<String> calls = <String>[];
  String partsRequestStatus = 'requested';
  Map<String, dynamic>? lastStockUpdate;

  @override
  Future<PagedList<Map<String, dynamic>>> getMyJobs({
    String? date,
    String? technicianId,
    String? cursor,
  }) async {
    calls.add('getMyJobs:$technicianId');
    return const PagedList<Map<String, dynamic>>(
      items: [
        {
          'visit_id': 'vis-101',
          'ticket_id': 'tkt-101',
          'status': 'confirmed',
          'urgency_class': 'urgent',
          'complaint_summary': 'Frostline fridge not cooling; compressor clicks',
          'locality': 'Kukatpally',
          'appliance_brand': 'Frostline',
          'appliance_category': 'refrigerator',
          'planned_start': '2026-11-21T04:30:00Z',
          'planned_end': '2026-11-21T06:30:00Z',
        },
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> getVisit(String id) async {
    calls.add('getVisit:$id');
    return {
      'visit_id': id,
      'ticket_id': 'tkt-101',
      'status': 'confirmed',
      'address_released': true,
      'urgency_class': 'urgent',
      'complaint_summary': 'Frostline fridge not cooling; compressor clicks',
      'drive_minutes': 18,
      'distance_km': 6.4,
      'household': {
        'display_name': 'Ramesh Rao',
        'locality': 'Kukatpally',
        'address_line': 'Plot 14, KPHB Phase 3, Hyderabad',
        'phone_masked': '+91 98*** ***21',
        'lat': 17.4948,
        'lon': 78.3996,
      },
      'visit_plan': {
        'id': 'vp-1',
        'version': 1,
        'trigger_reason': 'self_fix_unsuccessful',
        'already_tried': [
          'Checked power socket and voltage stabiliser',
          'Defrosted freezer vents for 30 minutes',
        ],
        'required_skills': ['refrigeration'],
        'est_duration_p50_min': 45,
        'est_duration_p80_min': 70,
        'tools_needed': ['Clamp multimeter', 'Screwdriver set'],
        'requires_safety_cert': [],
        'parts': [
          {
            'part_no': 'FL-REL-PTC',
            'name': 'PTC Starter Relay',
            'probability': 0.82,
            'quantity': 1,
            'source_ladder': 'van',
            'ready': true,
          },
          {
            'part_no': 'FL-CAP-UNVER',
            'name': 'Run Capacitor (compatibility unverified)',
            'probability': 0.45,
            'quantity': 1,
            'source_ladder': 'parts_centre',
            'ready': false,
          },
        ],
        'access_notes': 'Call at gate',
        'confidence': 0.82,
      },
      'diagnosis': {
        'hypotheses': [
          {
            'fault_key': 'ptc_relay_failure',
            'label': 'Compressor PTC starter relay fault',
            'probability': 0.82,
            'evidence': ['Clicking sound every 2 minutes'],
            'citations': [
              {
                'doc_title': 'Frostline Service Manual',
                'page': 42,
                'snippet': 'Test PTC relay resistance between pins M and S.',
              },
            ],
          },
        ],
        'abstained': false,
        'model_version': 'demo-v1',
      },
      'estimate_total_paise': 90000,
    };
  }

  @override
  Future<Visit> checkIn(
    String id, {
    required double lat,
    required double lon,
    String? idempotencyKey,
  }) async {
    calls.add('checkIn:$id');
    return Visit(
      id: id,
      technicianId: 'tech1_c_fw',
      plannedStart: '2026-11-21T04:30:00Z',
      plannedEnd: '2026-11-21T06:30:00Z',
      checkInAt: '2026-11-21T04:35:00Z',
    );
  }

  @override
  Future<Map<String, dynamic>> recordPartsUsed(
    String id, {
    required List<DebriefPartUsed> parts,
    String? idempotencyKey,
  }) async {
    calls.add('recordPartsUsed:$id:${parts.map((p) => p.partNo).join(",")}');
    return {'ok': true};
  }

  @override
  Future<Visit> recordOutcome(
    String id, {
    required String outcome,
    String notes = '',
    String? idempotencyKey,
  }) async {
    calls.add('recordOutcome:$id:$outcome');
    return Visit(
      id: id,
      technicianId: 'tech1_c_fw',
      plannedStart: '2026-11-21T04:30:00Z',
      plannedEnd: '2026-11-21T06:30:00Z',
      outcome: outcome,
    );
  }

  @override
  Future<Map<String, dynamic>> getMediaUploadUrl(
    String id, {
    required String filename,
    required String mimeType,
  }) async {
    calls.add('getMediaUploadUrl:$id:$filename');
    return {'media_ref': 'gs://keepwell-demo/$filename'};
  }

  @override
  Future<Quote> createFirmQuote(
    String ticketId, {
    required List<QuoteLine> lines,
    String? idempotencyKey,
  }) async {
    calls.add('createFirmQuote:$ticketId');
    final total = lines.fold<int>(0, (s, l) => s + l.amountPaise);
    return Quote(
      id: 'q-firm-1',
      version: 2,
      quoteType: 'firm',
      lines: lines,
      totalPaise: total,
      householdPaise: total,
      coveredPaise: 0,
    );
  }

  @override
  Future<Debrief> submitDebrief(
    String visitId, {
    required String mediaRef,
    required String language,
    String? idempotencyKey,
  }) async {
    calls.add('submitDebrief:$visitId:$language');
    return Debrief(
      id: 'deb-1',
      visitId: visitId,
      status: 'needs_confirmation',
      language: language,
      transcript: 'Replaced PTC relay and checked unknown capacitor.',
      extracted: const DebriefExtracted(
        faultFound: 'Burned PTC starter relay',
        workDone: 'Replaced relay and verified compressor start current',
        partsUsed: [DebriefPartUsed(partNo: 'FL-REL-PTC', quantity: 1)],
        adviceForHousehold: 'Keep door closed for 2 hours to stabilise cooling.',
        applianceNotes: 'Compressor healthy at 1.1A',
        followUpNeeded: false,
      ),
      unresolved: const ['generic capacitor'],
    );
  }

  @override
  Future<Debrief> confirmDebrief(
    String visitId, {
    required DebriefExtracted extracted,
    String? idempotencyKey,
  }) async {
    calls.add('confirmDebrief:$visitId');
    return Debrief(
      id: 'deb-1',
      visitId: visitId,
      status: 'confirmed',
      language: 'en',
      transcript: 'Replaced PTC relay and checked unknown capacitor.',
      extracted: extracted,
      unresolved: const [],
      confirmedAt: '2026-11-21T05:20:00Z',
    );
  }

  @override
  Future<Map<String, dynamic>> requestCloseOtp(
    String visitId, {
    String? idempotencyKey,
  }) async {
    calls.add('requestCloseOtp:$visitId');
    return {'otp_ref': 'otp-ref-101'};
  }

  @override
  Future<Map<String, dynamic>> confirmCloseOtp(
    String visitId, {
    required String otpRef,
    required String code,
    String? idempotencyKey,
  }) async {
    calls.add('confirmCloseOtp:$visitId:$code');
    return {'closed': true};
  }

  @override
  Future<PagedList<Map<String, dynamic>>> listPartsRequests({
    String? cursor,
  }) async {
    calls.add('listPartsRequests');
    return PagedList<Map<String, dynamic>>(
      items: [
        {
          'id': 'pr-901',
          'part_no': 'FL-REL-PTC',
          'part_name': 'PTC Starter Relay',
          'quantity': 1,
          'technician_name': 'Technician 1 (Kukatpally)',
          'ticket_id': 'tkt-101',
          'status': partsRequestStatus,
        },
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> acceptPartsRequest(
    String id, {
    String? idempotencyKey,
  }) async {
    calls.add('acceptPartsRequest:$id');
    partsRequestStatus = 'accepted';
    return {'id': id, 'status': 'accepted'};
  }

  @override
  Future<Map<String, dynamic>> readyPartsRequest(
    String id, {
    String? idempotencyKey,
  }) async {
    calls.add('readyPartsRequest:$id');
    partsRequestStatus = 'ready';
    return {'id': id, 'status': 'ready'};
  }

  @override
  Future<Map<String, dynamic>> handoverPartsRequest(
    String id, {
    String? idempotencyKey,
  }) async {
    calls.add('handoverPartsRequest:$id');
    partsRequestStatus = 'handed_over';
    return {'id': id, 'status': 'handed_over'};
  }

  @override
  Future<Map<String, dynamic>> updatePartsStock(
    Map<String, dynamic> items, {
    String? idempotencyKey,
  }) async {
    calls.add('updatePartsStock');
    lastStockUpdate = items;
    return {'ok': true};
  }
}

void main() {
  testWidgets('Technician sign-in routes to Today\'s Jobs', (tester) async {
    final api = _FakeKwApiClient();
    final auth = KwAuthHelper(config: const KwConfig());

    await tester.pumpWidget(
      KeepwellFieldApp(api: api, authHelper: auth),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('kw_quick_tech_fw')));
    await tester.pumpAndSettle();

    expect(find.text("Today's Jobs"), findsOneWidget);
    expect(
      find.text('Frostline fridge not cooling; compressor clicks'),
      findsOneWidget,
    );
  });

  testWidgets('Offline queue captures actions and syncs when online',
      (tester) async {
    final api = _FakeKwApiClient();
    final auth = KwAuthHelper(config: const KwConfig());

    await tester.pumpWidget(
      KeepwellFieldApp(api: api, authHelper: auth),
    );
    await tester.pumpAndSettle();

    // Sign in as technician & open visit
    await tester.tap(find.byKey(const Key('kw_quick_tech_fw')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('kw_job_card_vis-101')));
    await tester.pumpAndSettle();

    // Toggle offline mode
    await tester.tap(find.byKey(const Key('kw_offline_toggle')));
    await tester.pumpAndSettle();

    // Queue check-in while offline
    final listScroll = find.byType(Scrollable).first;
    final checkInBtn = find.byKey(const Key('kw_checkin_button'));
    await tester.scrollUntilVisible(checkInBtn, 200, scrollable: listScroll);
    await tester.ensureVisible(checkInBtn);
    await tester.pumpAndSettle();
    await tester.tap(checkInBtn);
    await tester.pumpAndSettle();

    // Queue parts-used while offline
    final partInput = find.byKey(const Key('kw_part_no_input'));
    await tester.scrollUntilVisible(partInput, 200, scrollable: listScroll);
    await tester.ensureVisible(partInput);
    await tester.pumpAndSettle();
    await tester.enterText(partInput, 'FL-REL-PTC');
    final recordPartBtn = find.byKey(const Key('kw_record_part_button'));
    await tester.ensureVisible(recordPartBtn);
    await tester.pumpAndSettle();
    await tester.tap(recordPartBtn);
    await tester.pumpAndSettle();

    expect(find.text('Offline — 2 actions queued'), findsOneWidget);
    expect(api.calls.where((c) => c.startsWith('checkIn:')), isEmpty);

    // Go back online and tap Sync now
    await tester.tap(find.byKey(const Key('kw_offline_toggle')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('kw_sync_now_button')));
    await tester.pumpAndSettle();

    expect(api.calls, contains('checkIn:vis-101'));
    expect(api.calls, contains('recordPartsUsed:vis-101:FL-REL-PTC'));
    expect(find.text('Synced 2 queued actions'), findsOneWidget);
  });

  testWidgets('Debrief displays Needs checking for unmatched part and confirms',
      (tester) async {
    final api = _FakeKwApiClient();
    final auth = KwAuthHelper(config: const KwConfig());

    await tester.pumpWidget(
      KeepwellFieldApp(api: api, authHelper: auth),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('kw_quick_tech_fw')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('kw_job_card_vis-101')));
    await tester.pumpAndSettle();

    // Submit voice debrief
    final listScroll = find.byType(Scrollable).first;
    final recordBtn = find.byKey(const Key('kw_record_debrief_button'));
    await tester.scrollUntilVisible(recordBtn, 300, scrollable: listScroll);
    await tester.tap(recordBtn);
    await tester.pumpAndSettle();

    // Unmatched part shows Needs checking container
    expect(find.byKey(const Key('kw_debrief_needs_checking')), findsOneWidget);
    expect(find.text('Unmatched part: generic capacitor'), findsOneWidget);

    // Resolve and confirm debrief
    final resolveField =
        find.byKey(const Key('kw_resolve_part_generic capacitor'));
    await tester.scrollUntilVisible(resolveField, 200, scrollable: listScroll);
    await tester.enterText(resolveField, 'FL-CAP-45UF');

    final confirmBtn = find.byKey(const Key('kw_confirm_debrief_button'));
    await tester.scrollUntilVisible(confirmBtn, 200, scrollable: listScroll);
    await tester.tap(confirmBtn);
    await tester.pumpAndSettle();

    expect(api.calls, contains('confirmDebrief:vis-101'));
    expect(find.text('Debrief confirmed'), findsOneWidget);
  });

  testWidgets('OTP closure completes visit with calm completion banner',
      (tester) async {
    final api = _FakeKwApiClient();
    final auth = KwAuthHelper(config: const KwConfig());

    await tester.pumpWidget(
      KeepwellFieldApp(api: api, authHelper: auth),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('kw_quick_tech_fw')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('kw_job_card_vis-101')));
    await tester.pumpAndSettle();

    final listScroll = find.byType(Scrollable).first;
    final reqOtpBtn = find.byKey(const Key('kw_request_otp_button'));
    await tester.scrollUntilVisible(reqOtpBtn, 300, scrollable: listScroll);
    await tester.tap(reqOtpBtn);
    await tester.pumpAndSettle();

    // Paste 6-digit OTP into first digit field of KwOtpInput
    final otpFields = find.descendant(
      of: find.byKey(const Key('kw_close_otp_input')),
      matching: find.byType(TextField),
    );
    await tester.enterText(otpFields.first, '482910');
    await tester.pumpAndSettle();

    final confirmOtpBtn = find.byKey(const Key('kw_confirm_otp_button'));
    await tester.scrollUntilVisible(confirmOtpBtn, 200, scrollable: listScroll);
    await tester.ensureVisible(confirmOtpBtn);
    await tester.pumpAndSettle();
    await tester.tap(confirmOtpBtn);
    await tester.pumpAndSettle();

    expect(api.calls, contains('confirmCloseOtp:vis-101:482910'));
    await tester.scrollUntilVisible(
      find.text('Closure OTP verified. Thank you for completing this visit.'),
      200,
      scrollable: listScroll,
    );
    expect(find.text('Closure OTP verified. Thank you for completing this visit.'),
        findsOneWidget);
  });

  testWidgets('Parts Centre Accept -> Mark Ready -> Handover & Stock stepper',
      (tester) async {
    final api = _FakeKwApiClient();
    final auth = KwAuthHelper(config: const KwConfig());

    await tester.pumpWidget(
      KeepwellFieldApp(api: api, authHelper: auth),
    );
    await tester.pumpAndSettle();

    // Sign in as Parts Centre operator
    await tester.tap(find.byKey(const Key('kw_quick_parts')));
    await tester.pumpAndSettle();

    expect(find.text('PTC Starter Relay (×1)'), findsOneWidget);

    // Accept
    await tester.tap(find.byKey(const Key('kw_parts_accept_pr-901')));
    await tester.pumpAndSettle();
    expect(api.calls, contains('acceptPartsRequest:pr-901'));

    // Mark Ready
    await tester.tap(find.byKey(const Key('kw_parts_ready_pr-901')));
    await tester.pumpAndSettle();
    expect(api.calls, contains('readyPartsRequest:pr-901'));

    // Handover
    await tester.tap(find.byKey(const Key('kw_parts_handover_pr-901')));
    await tester.pumpAndSettle();
    expect(api.calls, contains('handoverPartsRequest:pr-901'));
    expect(find.text('Handed over to technician'), findsOneWidget);

    // Switch to Stock tab and increment quantity
    await tester.tap(find.text('Stock'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('kw_stock_inc_AV-CAP-45UF')));
    await tester.pumpAndSettle();
    expect(find.text('9'), findsOneWidget);

    await tester.tap(find.byKey(const Key('kw_save_stock_button')));
    await tester.pumpAndSettle();
    expect(api.calls, contains('updatePartsStock'));
  });
}
