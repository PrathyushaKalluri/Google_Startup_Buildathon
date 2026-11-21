import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kw_brand/src/brand_app.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

class _FakeBrandApiClient extends KwApiClient {
  _FakeBrandApiClient({required super.config});

  Map<String, dynamic>? lastBrandForwardPayload;
  String? lastBrandApiKey;
  Map<String, dynamic>? lastRetailerHandoverPayload;
  String? lastRetailerApiKey;

  @override
  Future<PagedList<TicketCard>> listBrandRequests({
    String? brand,
    String? cursor,
  }) async {
    return const PagedList<TicketCard>(
      items: [
        TicketCard(
          id: 'tk-brand-c18',
          centreId: 'c_cc',
          trigger: 'brand_forward',
          channel: 'brand_api',
          jobType: 'repair',
          status: 'declined',
          resolution: 'Returned to brand: no authority',
          urgencyClass: 'standard',
          safetyFlag: false,
          entitlement: 'in_warranty',
          household: HouseholdRef(
            id: 'hh-18',
            displayName: 'Srinivasulu Reddy',
            language: 'en',
            pincode: '500081',
            locality: 'Madhapur',
            addressLine: 'Plot 21, Madhapur',
            verifiedVia: 'brand',
            linkedCentresCount: 1,
          ),
          appliance: ApplianceRef(
            id: 'app-18',
            brand: 'Aerovane',
            categoryCode: 'air_conditioner',
            modelCode: 'AV-AC-15T-INV',
            serialMasked: 'AV****412',
            identityStatus: 'verified',
          ),
          complaintSummary: 'Split AC not cooling; warranty forward to c_cc.',
          language: 'en',
          createdAt: '2026-11-20T09:15:00+05:30',
          updatedAt: '2026-11-20T09:16:00+05:30',
          flags: ['no_authority', 'returned_to_brand'],
        ),
        TicketCard(
          id: 'tk-brand-av1',
          centreId: 'c_av',
          trigger: 'brand_forward',
          channel: 'brand_api',
          jobType: 'repair',
          status: 'in_progress',
          urgencyClass: 'urgent',
          safetyFlag: false,
          entitlement: 'in_warranty',
          household: HouseholdRef(
            id: 'hh-19',
            displayName: 'Ananya Deshmukh',
            language: 'hi',
            pincode: '500032',
            locality: 'Gachibowli',
            addressLine: 'Tower B, Gachibowli',
            verifiedVia: 'brand',
            linkedCentresCount: 1,
          ),
          appliance: ApplianceRef(
            id: 'app-19',
            brand: 'Aerovane',
            categoryCode: 'air_conditioner',
            modelCode: 'AV-AC-20T-INV',
            serialMasked: 'AV****901',
            identityStatus: 'verified',
          ),
          complaintSummary: 'Outdoor fan rattling loudly.',
          language: 'hi',
          createdAt: '2026-11-20T10:00:00+05:30',
          updatedAt: '2026-11-20T10:30:00+05:30',
          flags: [],
        ),
        TicketCard(
          id: 'tk-retail-01',
          centreId: 'c_ip',
          trigger: 'retailer_handover',
          channel: 'retailer_api',
          jobType: 'installation',
          status: 'received',
          urgencyClass: 'planned',
          safetyFlag: false,
          entitlement: 'installation',
          household: HouseholdRef(
            id: 'hh-20',
            displayName: 'Meenakshi Iyer',
            language: 'en',
            pincode: '500034',
            locality: 'Banjara Hills',
            addressLine: 'Flat 402, Lotus Residency',
            verifiedVia: 'retailer',
            linkedCentresCount: 1,
          ),
          appliance: ApplianceRef(
            id: 'app-20',
            brand: 'Aerovane',
            categoryCode: 'air_conditioner',
            modelCode: 'AV-AC-15T-INV',
            serialMasked: 'AV****777',
            identityStatus: 'verified',
          ),
          complaintSummary: 'New unit installation handover from Digital Plaza.',
          language: 'en',
          createdAt: '2026-11-20T11:00:00+05:30',
          updatedAt: '2026-11-20T11:05:00+05:30',
          flags: [],
        ),
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> submitBrandRequest(
    Map<String, dynamic> payload, {
    required String apiKey,
    String? idempotencyKey,
  }) async {
    lastBrandForwardPayload = payload;
    lastBrandApiKey = apiKey;
    final centreKey = (payload['centre_key'] ?? '').toString();
    final claimed = (payload['claimed_warranty'] ?? '').toString();
    if (centreKey == 'c_cc' && claimed == 'in_warranty') {
      return {
        'ticket_id': 'tk-202-declined-c18',
        'status': 'declined',
        'declined_reason':
            'Cool Craft Appliance Services, Madhapur is not an authorised warranty centre for Aerovane.',
      };
    }
    return {
      'ticket_id': 'tk-202-accepted-01',
      'status': 'received',
      'declined_reason': null,
    };
  }

  @override
  Future<Map<String, dynamic>> submitRetailerHandover(
    Map<String, dynamic> payload, {
    required String apiKey,
    String? idempotencyKey,
  }) async {
    lastRetailerHandoverPayload = payload;
    lastRetailerApiKey = apiKey;
    return {
      'ticket_id': 'tk-202-retail-99',
      'status': 'received',
      'declined_reason': null,
    };
  }

  @override
  Future<Map<String, dynamic>> getBrandAnalytics({String? brand}) async {
    return {
      'brand': brand ?? 'All Brands',
      'installed_base_count': 124,
      'warranty_active_count': 86,
      'first_time_fix': 0.84,
      'fvr_14d': 0.79,
      'self_fix_resolution': 0.28,
      'avg_turnaround_hours': 18.4,
      'top_fault_families': [
        {'fault_family': 'drainage', 'count': 42},
        {'fault_family': 'cooling', 'count': 38},
        {'fault_family': 'heating', 'count': 21},
      ],
    };
  }
}

void main() {
  const baseConfig = KwConfig(
    firebaseAuthEmulatorHost: '',
    lookerStudioUrl: '',
  );

  testWidgets('Sign-In shows 4 demo accounts, signs in, and signs out',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeBrandApiClient(config: baseConfig);
    await tester.pumpWidget(
      BrandPortalApp(
        config: baseConfig,
        apiClient: api,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('brand.aerovane@keepwell.demo'), findsAtLeastNWidgets(1));
    expect(find.text('brand.zenith@keepwell.demo'), findsOneWidget);
    expect(find.text('brand.wavecrest@keepwell.demo'), findsOneWidget);
    expect(find.text('platform@keepwell.demo'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('persona-brand.aerovane@keepwell.demo')));
    await tester.pumpAndSettle();

    expect(
      find.text('Signed in as brand.aerovane@keepwell.demo'),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('sign-out-btn')));
    await tester.pumpAndSettle();

    expect(find.text('Sign in to Brand & Retailer Portal'), findsOneWidget);
  });

  testWidgets(
      'Forwarded Requests displays C18 declined authority reason and filters by declined',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeBrandApiClient(config: baseConfig);
    final session = KwAuthHelper.findPersonaByEmail('brand.aerovane@keepwell.demo');

    await tester.pumpWidget(
      BrandPortalApp(
        config: baseConfig,
        apiClient: api,
        initialSession: session,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('tk-brand-c18'), findsOneWidget);
    expect(find.text('Returned to brand: no authority'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('status-filter-declined')));
    await tester.pumpAndSettle();

    expect(find.text('tk-brand-c18'), findsOneWidget);
    expect(find.text('tk-brand-av1'), findsNothing);
    expect(find.text('tk-retail-01'), findsNothing);
  });

  testWidgets(
      'Brand Forward to independent c_cc returns 202 declined and Retailer Handover returns 202 received',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 960);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeBrandApiClient(config: baseConfig);
    final session = KwAuthHelper.findPersonaByEmail('brand.aerovane@keepwell.demo');

    await tester.pumpWidget(
      BrandPortalApp(
        config: baseConfig,
        apiClient: api,
        initialSession: session,
      ),
    );
    await tester.pumpAndSettle();

    // Navigate to Forward / Handover tab
    await tester.tap(find.text('Forward / Handover'));
    await tester.pumpAndSettle();

    // Apply c_cc independent centre preset & submit
    await tester.tap(find.byKey(const ValueKey('preset-c-cc-decline')));
    await tester.pumpAndSettle();

    final brandSubmitBtn = find.byKey(const ValueKey('submit-brand-forward-btn'));
    await tester.ensureVisible(brandSubmitBtn);
    await tester.tap(brandSubmitBtn);
    await tester.pumpAndSettle();

    expect(api.lastBrandApiKey, 'demo-brand-key');
    expect(api.lastBrandForwardPayload?['centre_key'], 'c_cc');
    expect(find.text('tk-202-declined-c18'), findsOneWidget);
    expect(
      find.textContaining('not an authorised warranty centre'),
      findsOneWidget,
    );

    // Switch to Retailer Installation Handover tab & submit
    await tester.tap(find.byKey(const ValueKey('tab-retailer-handover')));
    await tester.pumpAndSettle();

    final retailerSubmitBtn =
        find.byKey(const ValueKey('submit-retailer-handover-btn'));
    await tester.ensureVisible(retailerSubmitBtn);
    await tester.tap(retailerSubmitBtn);
    await tester.pumpAndSettle();

    expect(api.lastRetailerApiKey, 'demo-retailer-key');
    expect(api.lastRetailerHandoverPayload?['requested_job'], 'installation');
    expect(find.text('tk-202-retail-99'), findsOneWidget);
  });

  testWidgets(
      'Analytics screen renders KwFvrGauge (FVR-14), accessible table, and Looker Studio fallback/configured modes',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 960);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final api = _FakeBrandApiClient(config: baseConfig);
    final session = KwAuthHelper.findPersonaByEmail('brand.aerovane@keepwell.demo');

    await tester.pumpWidget(
      BrandPortalApp(
        config: baseConfig,
        apiClient: api,
        initialSession: session,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Analytics & Looker'));
    await tester.pumpAndSettle();

    expect(find.byType(KwFvrGauge), findsOneWidget);
    expect(find.text('79%'), findsAtLeastNWidgets(1));
    expect(find.text('FVR-14'), findsAtLeastNWidgets(1));
    expect(find.text('124'), findsOneWidget);
    expect(find.text('86'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('analytics-accessible-table')),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('looker-native-fallback')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.byKey(const ValueKey('looker-native-fallback')),
      findsOneWidget,
    );

    // Verify configured LOOKER_STUDIO_URL renders embed container
    const configuredLooker = KwConfig(
      lookerStudioUrl: 'https://lookerstudio.google.com/embed/reporting/demo-brand-fvr',
    );
    await tester.pumpWidget(
      BrandPortalApp(
        key: const ValueKey('configured-looker-app'),
        config: configuredLooker,
        apiClient: _FakeBrandApiClient(config: configuredLooker),
        initialSession: session,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Analytics & Looker'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('looker-embed-container')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.byKey(const ValueKey('looker-embed-container')),
      findsOneWidget,
    );
    expect(
      find.text('https://lookerstudio.google.com/embed/reporting/demo-brand-fvr'),
      findsOneWidget,
    );
  });
}
