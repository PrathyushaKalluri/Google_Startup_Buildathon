import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_console/main.dart';
import 'package:kw_console/src/console_state.dart';
import 'package:kw_ui/kw_ui.dart';

class _FakeConsoleApiClient extends KwApiClient {
  _FakeConsoleApiClient() : super(config: const KwConfig(demoMode: true));

  String urgencyForT2 = 'standard';
  String assignedTechForT2 = 'tech_ravi';
  int reclassifyCalls = 0;
  int reassignCalls = 0;

  TicketCard _card({
    required String id,
    required String urgency,
    required String summary,
    required String householdName,
    String? neededBy,
  }) {
    return TicketCard(
      id: id,
      centreId: 'centre_fw',
      trigger: 'voice',
      channel: 'voice',
      jobType: 'repair',
      status: 'assigned',
      urgencyClass: urgency,
      neededBy: neededBy,
      safetyFlag: urgency == 'safety',
      safetyReason:
          urgency == 'safety' ? 'Burning smell near power socket' : null,
      entitlement: 'warranty',
      household: HouseholdRef(
        id: 'hh_$id',
        displayName: householdName,
        language: 'en',
        pincode: '500072',
        locality: 'Kukatpally',
        addressLine: 'Flat 402, Lakeview Heights',
        verifiedVia: 'phone_match',
        linkedCentresCount: 1,
      ),
      appliance: const ApplianceRef(
        id: 'app_1',
        brand: 'Wavecrest',
        categoryCode: 'washer',
        modelCode: 'WC-FL700-IN',
        serialMasked: 'WC****891',
        identityStatus: 'verified_sticker',
        warrantyEnd: '2027-06-30',
      ),
      complaintSummary: summary,
      language: 'en',
      createdAt: '2026-11-21T06:00:00Z',
      updatedAt: '2026-11-21T07:00:00Z',
      flags: const [],
    );
  }

  TicketDetail _detailFor(String id) {
    final isSafety = id == 'T-SAFETY';
    final urgency = isSafety ? 'safety' : urgencyForT2;
    return TicketDetail(
      card: _card(
        id: id,
        urgency: urgency,
        summary: isSafety
            ? 'Sparks from AC isolator switch'
            : 'Wavecrest washer E20 not draining',
        householdName: isSafety ? 'Ramesh Verma' : 'Meera Rao',
        neededBy: '2026-11-21T11:00:00Z',
      ),
      caseCard: const CaseCard(
        summary: 'Front-load washer displays E20 after rinse cycle.',
        symptoms: ['Standing water', 'E20 display'],
        errorCodes: ['E20'],
        whatWasTried: ['Drain filter cleaned on video'],
        safetyNotes: 'No electrical hazard detected.',
        identityNotes: 'Sticker verified.',
        sources: [],
      ),
      urgency: [
        UrgencyAssessment(
          urgencyClass: urgency,
          ruleCodes: const ['E20_STANDING_WATER'],
          facts: const {},
          assessedBy: 'agent',
          reason: 'Standing water in drum requires same-day visit.',
          protectiveStepsSent: isSafety,
          createdAt: '2026-11-21T06:10:00Z',
        ),
      ],
      gates: const [
        ConsentGate(gate: 1, answer: 'yes'),
        ConsentGate(gate: 2, answer: 'yes', choice: 'switch_to_video'),
      ],
      clarifyingQa: const [
        ClarifyingQa(
          seq: 1,
          question: 'Does the machine hum when trying to drain?',
          answer: 'Yes, it hums for 20 seconds then shows E20.',
        ),
      ],
      fixAttempts: const [
        FixAttempt(
          id: 'fix_1',
          catalogueCode: 'SF-WC-01',
          title: 'Clean front drain filter',
          offeredAt: '2026-11-21T06:15:00Z',
          stepsDone: 4,
          ofSteps: 4,
          outcome: 'not_resolved',
          householdReport: 'Filter was clean; water still stands.',
          observedOnVideo: true,
        ),
      ],
      triedSummary: const [],
      diagnosis: const Diagnosis(
        hypotheses: [
          DiagnosisHypothesis(
            faultKey: 'drain_pump_motor',
            label: 'Faulty drain pump motor',
            probability: 0.86,
            evidence: ['Clean filter verified on video', 'E20 persists'],
            citations: [
              Citation(
                docTitle: 'Wavecrest FL700 Service Manual',
                page: 42,
                snippet: 'If filter is clear and E20 persists, replace WC-DP-402.',
              ),
            ],
          ),
        ],
        abstained: false,
        modelVersion: 'kw-diag-v2',
      ),
      visitPlan: const VisitPlan(
        id: 'vp_1',
        version: 2,
        triggerReason: 'Safe fix did not resolve',
        alreadyTried: ['Drain filter check'],
        requiredSkills: ['washer_front_load'],
        estDurationP50Min: 45,
        estDurationP80Min: 70,
        toolsNeeded: ['Multimeter', 'Clamp pliers'],
        requiresSafetyCert: [],
        parts: [
          VisitPlanPart(
            partNo: 'WC-DP-402',
            name: 'Wavecrest Drain Pump Assembly',
            probability: 0.86,
            quantity: 1,
            sourceLadder: 'van',
            ready: true,
          ),
          VisitPlanPart(
            partNo: '',
            name: 'Unverified Hose Clamp',
            probability: 0.25,
            quantity: 1,
            sourceLadder: 'unmatched',
            ready: false,
          ),
        ],
        accessNotes: 'Gate code 4021',
        confidence: 0.86,
      ),
      candidates: [
        AssignmentCandidate(
          technicianId: 'tech_ravi',
          name: 'Ravi Kumar',
          rank: 1,
          score: 92,
          scoreBreakdown: const ScoreBreakdown(
            fixConfidence: 29,
            partsReadiness: 25,
            timeToVisit: 18,
            routeCost: 11,
            reliability: 5,
            householdFit: 4,
          ),
          slotStart: '2026-11-21T08:30:00Z',
          slotEnd: '2026-11-21T10:30:00Z',
          outcome: assignedTechForT2 == 'tech_ravi' ? 'assigned' : 'proposed',
          chosenBy: 'agent',
          why: 'Carrying pump part in van',
        ),
        AssignmentCandidate(
          technicianId: 'tech_anitha',
          name: 'Anitha Reddy',
          rank: 2,
          score: 81,
          scoreBreakdown: const ScoreBreakdown(
            fixConfidence: 26,
            partsReadiness: 19,
            timeToVisit: 15,
            routeCost: 12,
            reliability: 5,
            householdFit: 4,
          ),
          slotStart: '2026-11-21T10:30:00Z',
          slotEnd: '2026-11-21T12:30:00Z',
          outcome: assignedTechForT2 == 'tech_anitha' ? 'assigned' : 'proposed',
          chosenBy: assignedTechForT2 == 'tech_anitha' ? 'centre' : 'agent',
          why: 'Available second slot',
        ),
      ],
      slotProposals: const [],
      quotes: const [],
      payments: const [],
      timeline: const [
        TimelineEvent(
          at: '2026-11-21T06:00:00Z',
          type: 'conversation_started',
          actor: 'agent',
          title: 'Inbound voice call received',
          detail: 'Matched to Frost & Wave Kukatpally',
        ),
      ],
      authority: const AuthorityResult(
        level: 'authorised',
        decision: 'proceed',
      ),
    );
  }

  @override
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
    return PagedList<TicketCard>(
      items: [
        _card(
          id: 'T-STD',
          urgency: urgencyForT2,
          summary: 'Wavecrest washer E20 not draining',
          householdName: 'Meera Rao',
          neededBy: '2026-11-21T11:00:00Z',
        ),
        _card(
          id: 'T-SAFETY',
          urgency: 'safety',
          summary: 'Sparks from AC isolator switch',
          householdName: 'Ramesh Verma',
          neededBy: '2026-11-21T09:00:00Z',
        ),
      ],
    );
  }

  @override
  Future<TicketDetail> getTicket(String id) async => _detailFor(id);

  @override
  Future<TicketDetail> reclassifyUrgency(
    String id, {
    required String urgencyClass,
    required String reason,
    String? idempotencyKey,
  }) async {
    reclassifyCalls++;
    urgencyForT2 = urgencyClass;
    return _detailFor(id);
  }

  @override
  Future<TicketDetail> reassignTicket(
    String id, {
    required String technicianId,
    required String slotStart,
    required String slotEnd,
    required String reason,
    String? idempotencyKey,
  }) async {
    reassignCalls++;
    assignedTechForT2 = technicianId;
    return _detailFor(id);
  }
}

void main() {
  testWidgets('Sign-In -> Case Board renders sorted by safety first',
      (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeConsoleApiClient();
    final controller = ConsoleController(
      config: const KwConfig(demoMode: true),
      apiClient: api,
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(KeepwellConsoleApp(controller: controller));
    await tester.pumpAndSettle();

    // Sign-in screen renders quick button for Frost & Wave
    expect(find.byKey(const Key('quick_sign_in_c_fw')), findsOneWidget);
    await tester.tap(find.byKey(const Key('quick_sign_in_c_fw')));
    await tester.pumpAndSettle();

    // Board renders with safety card above standard card
    final safetyFinder = find.byKey(const Key('case_card_T-SAFETY'));
    final stdFinder = find.byKey(const Key('case_card_T-STD'));
    expect(safetyFinder, findsOneWidget);
    expect(stdFinder, findsOneWidget);
    expect(
      tester.getTopLeft(safetyFinder).dy,
      lessThan(tester.getTopLeft(stdFinder).dy),
    );
    controller.signOut();
    await tester.pump();
  });

  testWidgets('Live Stage View renders in Projector Mode and runs C03 demo',
      (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeConsoleApiClient();
    final controller = ConsoleController(
      config: const KwConfig(demoMode: true),
      apiClient: api,
      initialSession: KwAuthHelper.findPersonaByEmail(
        'console.c_fw@keepwell.demo',
      ),
      initialDestination: ConsoleDestination.stage,
      initialProjectorMode: true,
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(KeepwellConsoleApp(controller: controller));
    await tester.pumpAndSettle();

    expect(controller.themePreset, KwThemePreset.projector);
    expect(
      find.text('Nothing happening — start a C03 Stage Demo or Test Call'),
      findsOneWidget,
    );

    // Trigger C03 Stage Call (falls back cleanly when WS server is offline)
    await tester.tap(find.byKey(const Key('stage_play_c03_button')));
    await tester.pump(const Duration(seconds: 3));
    await tester.pump(const Duration(seconds: 4));

    expect(find.text('Live Conversation Transcript'), findsOneWidget);
    expect(find.text('What the agent knows'), findsOneWidget);
    controller.signOut();
    await tester.pump();
  });

  testWidgets('Reclassify Urgency and Reassign show 10s Undo SnackBar',
      (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeConsoleApiClient();
    final controller = ConsoleController(
      config: const KwConfig(demoMode: true),
      apiClient: api,
      initialSession: KwAuthHelper.findPersonaByEmail(
        'console.c_fw@keepwell.demo',
      ),
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(KeepwellConsoleApp(controller: controller));
    await tester.pumpAndSettle();

    // Select T-STD card so we test Reclassify & Reassign on it
    await tester.tap(find.byKey(const Key('case_card_T-STD')));
    await tester.pumpAndSettle();

    // Reclassify urgency
    await tester.tap(find.byKey(const Key('action_change_urgency')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('reclassify_reason_field')),
      'Standing water in utility balcony',
    );
    await tester.tap(find.byKey(const Key('reclassify_confirm_button')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(api.reclassifyCalls, 1);
    expect(find.text('Undo'), findsOneWidget);

    // Reassign technician
    await tester.tap(find.byKey(const Key('action_reassign')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('reassign_reason_field')),
      'Anitha is closer to Kukatpally',
    );
    await tester.tap(find.byKey(const Key('reassign_confirm_button')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(api.reassignCalls, 1);
    expect(find.text('Undo'), findsOneWidget);
    controller.signOut();
    await tester.pump();
  });
}
