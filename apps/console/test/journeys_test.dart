import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_console/main.dart';
import 'package:kw_console/src/console_state.dart';
import 'package:kw_ui/kw_ui.dart';

class _JourneyConsoleApiClient extends KwApiClient {
  _JourneyConsoleApiClient() : super(config: const KwConfig(demoMode: true));

  final List<String> reclassifyHistory = [];
  final List<String> reassignHistory = [];
  String _currentUrgency = 'standard';
  String _currentTechId = 'tech_ramesh';

  TicketCard _card() => TicketCard(
        id: 'T-C03',
        centreId: 'c_fw',
        trigger: 'household_call',
        channel: 'voice',
        jobType: 'repair',
        status: 'assigned',
        urgencyClass: _currentUrgency,
        neededBy: '2026-11-21T16:00:00Z',
        safetyFlag: _currentUrgency == 'safety',
        entitlement: 'paid',
        household: const HouseholdRef(
          id: 'hh_c03',
          displayName: 'Sunita Sharma',
          language: 'hi',
          pincode: '500072',
          locality: 'Kukatpally',
          addressLine: 'Flat 204, Sai Enclave, Kukatpally',
          verifiedVia: 'call_line',
          linkedCentresCount: 1,
        ),
        appliance: const ApplianceRef(
          id: 'app_c03',
          brand: 'Wavecrest',
          categoryCode: 'washing_machine',
          modelCode: 'WC-FL85',
          serialMasked: 'WC****991',
          identityStatus: 'verified',
        ),
        complaintSummary: 'Washer showing E21; water not draining.',
        language: 'hi',
        createdAt: '2026-11-21T08:15:00Z',
        updatedAt: '2026-11-21T08:25:00Z',
        flags: const [],
      );

  TicketDetail _detail() => TicketDetail(
        card: _card(),
        caseCard: const CaseCard(
          summary: 'E21 drain failure; drain filter cleaned, error returned.',
          symptoms: ['E21', 'Not draining'],
          errorCodes: ['E21'],
          whatWasTried: ['SF-WM-DRAINFILTER-WC: coins removed, E21 returned'],
          safetyNotes: '',
          identityNotes: '',
          sources: [
            Citation(
              docTitle: 'Wavecrest Washer Manual',
              page: 14,
              snippet: 'E21 indicates drain pump blockage or pump motor fault.',
            ),
          ],
        ),
        urgency: [
          UrgencyAssessment(
            urgencyClass: _currentUrgency,
            ruleCodes: const ['STD-DEFAULT'],
            facts: const {'water_spreading': false},
            assessedBy: 'agent',
            reason: 'Water contained inside drum',
            protectiveStepsSent: false,
            createdAt: '2026-11-21T08:16:00Z',
          ),
        ],
        gates: const [
          ConsentGate(gate: 1, answer: 'yes'),
          ConsentGate(gate: 2, answer: 'yes', choice: 'switch_to_video'),
        ],
        clarifyingQa: const [],
        fixAttempts: const [],
        triedSummary: const [],
        slotProposals: const [],
        quotes: const [],
        payments: const [],
        timeline: const [],
        candidates: [
          AssignmentCandidate(
            technicianId: 'tech_ramesh',
            name: 'Ramesh Naik',
            rank: 1,
            score: 91,
            scoreBreakdown: const ScoreBreakdown(
              fixConfidence: 28,
              partsReadiness: 23,
              timeToVisit: 18,
              routeCost: 13,
              reliability: 5,
              householdFit: 4,
            ),
            slotStart: '2026-11-21T10:00:00Z',
            slotEnd: '2026-11-21T12:00:00Z',
            outcome: _currentTechId == 'tech_ramesh' ? 'chosen' : 'not_chosen',
            chosenBy: 'agent',
            why: 'Highest washer E21 fix confidence',
          ),
          AssignmentCandidate(
            technicianId: 'tech_anitha',
            name: 'Anitha Reddy',
            rank: 2,
            score: 86,
            scoreBreakdown: const ScoreBreakdown(
              fixConfidence: 26,
              partsReadiness: 22,
              timeToVisit: 17,
              routeCost: 12,
              reliability: 4,
              householdFit: 5,
            ),
            slotStart: '2026-11-21T11:00:00Z',
            slotEnd: '2026-11-21T13:00:00Z',
            outcome: _currentTechId == 'tech_anitha' ? 'chosen' : 'not_chosen',
            chosenBy: 'centre_console',
            why: 'Closer to Kukatpally',
          ),
        ],
        authority: const AuthorityResult(
          level: 'authorised_service',
          decision: 'proceed',
        ),
      );

  @override
  Future<PagedList<TicketCard>> listTickets({
    String? status,
    String? urgencyClass,
    String? trigger,
    String? q,
    String? centreKey,
    String? centreId,
    String? cursor,
    int? limit,
  }) async =>
      PagedList(items: [_card()]);

  @override
  Future<TicketDetail> getTicket(String ticketId) async => _detail();

  @override
  Future<TicketDetail> reclassifyUrgency(
    String ticketId, {
    required String urgencyClass,
    required String reason,
    String? idempotencyKey,
  }) async {
    reclassifyHistory.add('$urgencyClass:$reason');
    _currentUrgency = urgencyClass;
    return _detail();
  }

  @override
  Future<TicketDetail> reassignTicket(
    String ticketId, {
    required String technicianId,
    required String slotStart,
    required String slotEnd,
    required String reason,
    String? idempotencyKey,
  }) async {
    reassignHistory.add('$technicianId:$reason');
    _currentTechId = technicianId;
    return _detail();
  }

  @override
  Future<PagedList<DemoCase>> listDemoCases({String? cursor}) async =>
      const PagedList(items: []);
}

void main() {
  testWidgets(
      'Journey 1: C03 Stage View plays full Hindi call -> video switch -> failed fix -> re-run in Projector Mode',
      (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _JourneyConsoleApiClient();
    final controller = ConsoleController(
      config: const KwConfig(demoMode: true),
      apiClient: api,
      initialSession:
          KwAuthHelper.findPersonaByEmail('console.c_fw@keepwell.demo'),
      initialDestination: ConsoleDestination.stage,
      initialProjectorMode: true,
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(KeepwellConsoleApp(controller: controller));
    await tester.pumpAndSettle();

    expect(controller.themePreset, KwThemePreset.projector);
    expect(find.byKey(const Key('stage_play_c03_button')), findsOneWidget);

    await tester.tap(find.byKey(const Key('stage_play_c03_button')));
    // Advance through C03 beats
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(seconds: 2));
    }

    expect(find.text('Live Conversation Transcript'), findsOneWidget);
    expect(find.text('What the agent knows'), findsOneWidget);
    expect(find.textContaining('Diagnosis Probability'), findsOneWidget);

    controller.signOut();
    await tester.pump();
  });

  testWidgets(
      'Journey 2: Reclassify Urgency and Reassign both execute Undo restoring prior state',
      (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _JourneyConsoleApiClient();
    final controller = ConsoleController(
      config: const KwConfig(demoMode: true),
      apiClient: api,
      initialSession:
          KwAuthHelper.findPersonaByEmail('console.c_fw@keepwell.demo'),
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(KeepwellConsoleApp(controller: controller));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('case_card_T-C03')));
    await tester.pumpAndSettle();

    // 1. Reclassify urgency -> tap Undo
    await tester.tap(find.byKey(const Key('action_change_urgency')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('reclassify_reason_field')),
      'Water leaking onto balcony',
    );
    await tester.tap(find.byKey(const Key('reclassify_confirm_button')));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(api.reclassifyHistory.length, 1);
    expect(find.text('Undo'), findsOneWidget);
    await tester.tap(find.text('Undo'));
    await tester.pump(const Duration(milliseconds: 500));
    expect(api.reclassifyHistory.length, 2);
    expect(api.reclassifyHistory.last, startsWith('standard:Undo'));

    // 2. Reassign technician -> tap Undo
    await tester.tap(find.byKey(const Key('action_reassign')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('reassign_reason_field')),
      'Anitha is 10 mins away',
    );
    await tester.tap(find.byKey(const Key('reassign_confirm_button')));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(api.reassignHistory.length, 1);
    expect(find.text('Undo'), findsOneWidget);
    await tester.tap(find.text('Undo'));
    await tester.pump(const Duration(milliseconds: 500));
    expect(api.reassignHistory.length, 2);
    expect(api.reassignHistory.last, contains('Undo'));

    controller.signOut();
    await tester.pump();
  });
}
