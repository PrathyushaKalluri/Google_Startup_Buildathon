import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_household/src/call_dialer_screen.dart';
import 'package:kw_household/src/home_memory_screen.dart';
import 'package:kw_household/src/household_app.dart';
import 'package:kw_household/src/media/kw_media_bridge.dart';
import 'package:kw_household/src/quote_approval_screen.dart';
import 'package:kw_household/src/video_link_screen.dart';
import 'package:kw_ui/kw_ui.dart';

class _FakeLiveCallClient extends LiveCallClient {
  _FakeLiveCallClient() : super(config: const KwConfig());

  final StreamController<LiveServerMessage> _controller =
      StreamController<LiveServerMessage>.broadcast();

  final List<String> sentVideoFrames = <String>[];
  final List<String> sentImages = <String>[];
  final List<Map<String, dynamic>> sentStates = <Map<String, dynamic>>[];
  bool started = false;
  bool ended = false;

  @override
  Stream<LiveServerMessage> get messages => _controller.stream;

  void emit(LiveServerMessage message) {
    _controller.add(message);
  }

  @override
  Future<void> start({
    required String centreKey,
    required String callerNumber,
    String? languageHint,
    String? resumeConversationId,
    String? authToken,
  }) async {
    started = true;
  }

  @override
  void sendVideoFrame(
    String base64Jpeg,
    int ts, {
    String mime = 'image/jpeg',
  }) {
    sentVideoFrames.add(base64Jpeg);
  }

  @override
  void sendImage(
    String base64Jpeg, {
    String caption = 'sticker',
    String mime = 'image/jpeg',
  }) {
    sentImages.add(caption);
  }

  @override
  void sendClientState({
    required String modality,
    required bool muted,
  }) {
    sentStates.add(<String, dynamic>{'modality': modality, 'muted': muted});
  }

  @override
  Future<void> end() async {
    ended = true;
  }

  @override
  Future<void> dispose() async {
    await _controller.close();
  }
}

Widget _wrapScreen(Widget child) {
  return KwLocaleScope(
    languageCode: 'en',
    child: MaterialApp(
      theme: KwTheme.light(),
      home: Scaffold(body: child),
    ),
  );
}

void main() {
  testWidgets(
      'WhatsApp simulator loads households, activates session, and displays verbatim agent reply',
      (tester) async {
    var sessionCreated = false;
    var inboundCalled = false;

    final mockHttp = MockClient((request) async {
      if (request.url.path.endsWith('/admin/demo/households')) {
        return http.Response(
          jsonEncode(<String, dynamic>{
            'items': <Map<String, dynamic>>[
              <String, dynamic>{
                'household_id': 'hh_01',
                'display_name': 'Ananya Rao',
                'phone_masked': '+919848011111',
                'language': 'en',
                'magic_token': 'tok-ananya-01',
                'centre_key': 'c_fw',
                'centre_id': 'cid_fw',
              },
            ],
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (request.url.path.endsWith('/public/session')) {
        sessionCreated = true;
        return http.Response(
          jsonEncode(<String, dynamic>{'ok': true}),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (request.url.path.endsWith('/channels/whatsapp/simulator/inbound')) {
        inboundCalled = true;
        return http.Response(
          jsonEncode(<String, dynamic>{
            'replies': <String>[
              'Got it! Would you like to try a safe drain-filter check first?',
            ],
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      return http.Response('{}', 404);
    });

    final api = KwApiClient(config: const KwConfig(), httpClient: mockHttp);
    final live = _FakeLiveCallClient();
    addTearDown(() async {
      api.close();
      await live.dispose();
    });

    await tester.pumpWidget(
      KeepwellHouseholdApp(
        apiClient: api,
        liveCallClient: live,
        initialRoute: '/whatsapp',
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('WhatsApp simulator'), findsOneWidget);
    expect(find.textContaining('Frost and Wave Service Point'), findsWidgets);
    expect(sessionCreated, isTrue);

    // Tap quick-reply chip.
    await tester.tap(find.text('Yes, try safe fix'));
    await tester.pumpAndSettle();

    expect(inboundCalled, isTrue);
    expect(
      find.text(
        'Got it! Would you like to try a safe drain-filter check first?',
      ),
      findsOneWidget,
    );
  });

  testWidgets(
      'Call dialer C03 state renders recording notice verbatim, bilingual captions, video transition card, and go_away reconnect state',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final live = _FakeLiveCallClient();
    String? switchedToken;
    addTearDown(live.dispose);

    await tester.pumpWidget(
      _wrapScreen(
        CallDialerScreen(
          liveCallClient: live,
          activeCentre: KwAuthHelper.demoCentres[2],
          onSwitchToVideoToken: (token) => switchedToken = token,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Plain-language microphone banner visible initially.
    expect(find.text('Microphone access for this voice call'), findsOneWidget);

    await tester.tap(find.text('Allow microphone'));
    await tester.pumpAndSettle();
    expect(live.started, isTrue);

    // Emit LiveReadyMessage with verbatim recording notice.
    live.emit(
      const LiveReadyMessage(
        conversationId: 'conv_c03',
        sessionId: 'sess_c03',
        centreName: 'Frost and Wave Service Point, Kukatpally',
        recordingNotice:
            'This call with Frost and Wave Service Point is recorded for service quality and your home memory.',
      ),
    );
    live.emit(
      const LiveTranscriptMessage(
        speaker: 'agent',
        text: 'Namaste! Kya aap washing machine ka error code dikha sakte hain?',
        isFinal: true,
        lang: 'hi',
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text(
        'This call with Frost and Wave Service Point is recorded for service quality and your home memory.',
      ),
      findsOneWidget,
    );
    expect(
      find.text(
        'Namaste! Kya aap washing machine ka error code dikha sakte hain?',
      ),
      findsOneWidget,
    );

    // Emit LiveVideoLinkMessage -> "Switching to video..." transition card.
    live.emit(
      const LiveVideoLinkMessage(
        url: 'https://household.keepwell.local/v/tok-c03-video',
        expiresAt: '2026-11-21T12:00:00Z',
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Switching to video...'), findsOneWidget);
    await tester.tap(find.text('Open video check now'));
    await tester.pumpAndSettle();
    expect(switchedToken, 'tok-c03-video');

    // Emit LiveGoAwayMessage -> graceful degraded/reconnect banner.
    live.emit(const LiveGoAwayMessage(seconds: 20));
    await tester.pumpAndSettle();
    expect(find.textContaining('Session refreshing in 20s'), findsOneWidget);
  });

  testWidgets(
      'Video-link screen displays dynamic framing guides, 1 fps counter, stop-video control, and camera-denied still-photo fallback',
      (tester) async {
    final live = _FakeLiveCallClient();
    var stoppedToVoice = false;
    addTearDown(live.dispose);

    await tester.pumpWidget(
      _wrapScreen(
        VideoLinkScreen(
          token: 'tok-video-1',
          liveCallClient: live,
          activeCentre: KwAuthHelper.demoCentres[2],
          onStopVideoToVoice: () => stoppedToVoice = true,
          mediaBridge: KwMediaBridge(
            onTestCaptureFrame: () => 'QUJDREVGRw==',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Grant camera permission.
    await tester.tap(find.text('Allow camera'));
    await tester.pump(const Duration(milliseconds: 500));
    expect(live.sentVideoFrames.length, greaterThanOrEqualTo(1));
    expect(find.text('Frame model sticker'), findsOneWidget);

    // Drive all 4 framing guides via LiveUiHintMessage.
    live.emit(
      const LiveUiHintMessage(
        kind: 'show_display',
        text: 'Point at the front LED error display.',
      ),
    );
    await tester.pump();
    expect(find.text('Frame display panel'), findsOneWidget);

    live.emit(
      const LiveUiHintMessage(
        kind: 'show_drain_filter',
        text: 'Point at the lower-right drain filter flap.',
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.textContaining('drain filter'), findsAtLeastNWidgets(1));

    live.emit(
      const LiveUiHintMessage(
        kind: 'hold_steady',
        text: 'Hold steady for two seconds.',
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Hold phone steady'), findsOneWidget);

    // Stop video button must be >= 48dp tall and switch back to voice.
    final stopFinder = find.text('Stop video (continue on voice)');
    expect(stopFinder, findsOneWidget);
    final stopSize = tester.getSize(
      find.ancestor(of: stopFinder, matching: find.byType(OutlinedButton)),
    );
    expect(stopSize.height, greaterThanOrEqualTo(48));

    await tester.tap(stopFinder);
    await tester.pump();
    expect(stoppedToVoice, isTrue);

    // Camera-denied fallback to sending a still photo.
    await tester.pumpWidget(
      _wrapScreen(
        VideoLinkScreen(
          key: const ValueKey('video-denied'),
          token: 'tok-video-denied',
          liveCallClient: live,
          activeCentre: KwAuthHelper.demoCentres[2],
          initialCameraDenied: true,
          mediaBridge: KwMediaBridge(
            onTestCaptureFrame: () => 'QUJDREVGRw==',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Camera unavailable — send a still photo instead'),
      findsOneWidget,
    );
    await tester.tap(find.text('Send still photo'));
    await tester.pump();
    expect(live.sentImages, contains('model_sticker'));
  });

  testWidgets(
      'Home Memory renders appliance cards, Care Index with reasons, timeline, due services, and advice notes',
      (tester) async {
    final mockHttp = MockClient((request) async {
      if (request.url.path.endsWith('/public/home/tok-home-1')) {
        return http.Response(
          jsonEncode(<String, dynamic>{
            'centre_name': 'Frost and Wave Service Point, Kukatpally',
            'household': <String, dynamic>{
              'display_name': 'Ananya Rao',
              'locality': 'Kukatpally',
            },
            'appliances': <Map<String, dynamic>>[
              <String, dynamic>{
                'brand': 'Wavecrest',
                'model_code': 'WC-FL700',
                'category_code': 'washing_machine',
                'age_label': '2 yr 4 mo old',
                'warranty_status': 'Extended Plan Active',
                'care_index': 84,
                'care_index_reasons': <String>[
                  'Drain filter cleaned on schedule',
                  'No repeat fault in the last 12 months',
                ],
                'timeline': <Map<String, dynamic>>[
                  <String, dynamic>{
                    'at': '2026-10-12T10:30:00Z',
                    'type': 'ticket_closed',
                    'actor': 'technician',
                    'title': 'Drain pump lint cleared',
                    'detail': 'Verified spin cycle with household OTP.',
                  },
                ],
              },
            ],
            'next_due_services': <Map<String, dynamic>>[
              <String, dynamic>{
                'title': 'Drum descaling & inlet mesh rinse',
                'appliance': 'Wavecrest WC-FL700',
                'due_date': '15 Dec 2026',
              },
            ],
            'advice_notes': <Map<String, dynamic>>[
              <String, dynamic>{
                'text': 'Clean the lower drain filter every 6 weeks.',
                'by': 'Ravi (Technician)',
                'at': '12 Oct 2026',
              },
            ],
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      return http.Response('{}', 404);
    });

    final api = KwApiClient(config: const KwConfig(), httpClient: mockHttp);
    addTearDown(api.close);

    await tester.pumpWidget(
      _wrapScreen(
        HomeMemoryScreen(
          token: 'tok-home-1',
          apiClient: api,
          activeCentre: KwAuthHelper.demoCentres[2],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Wavecrest WC-FL700'), findsAtLeastNWidgets(1));
    expect(find.text('Extended Plan Active'), findsOneWidget);
    expect(find.text('84 / 100'), findsOneWidget);
    expect(find.text('Drain filter cleaned on schedule'), findsOneWidget);
    expect(find.text('Drain pump lint cleared'), findsOneWidget);
    expect(find.text('Drum descaling & inlet mesh rinse'), findsOneWidget);
    expect(
      find.text('Clean the lower drain filter every 6 weeks.'),
      findsOneWidget,
    );
  });

  testWidgets(
      'Quote -> Sandbox Payment -> OTP closure flow renders Needs checking, OTP banner, Google Pay TEST sheet, and closes job',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    var quoteApproved = false;
    var sandboxCompleted = false;
    var otpConfirmed = false;

    Map<String, dynamic> quoteJson({required bool approved}) =>
        <String, dynamic>{
          'id': 'q_01',
          'version': 1,
          'quote_type': 'firm',
          'lines': <Map<String, dynamic>>[
            <String, dynamic>{
              'kind': 'part',
              'description': 'Drain pump assembly',
              'part_no': 'WC-DP-440',
              'amount_paise': 120000,
              'payer': 'household',
            },
            <String, dynamic>{
              'kind': 'labour',
              'description': 'Visit & labour (covered under plan)',
              'amount_paise': 45000,
              'payer': 'plan',
            },
            <String, dynamic>{
              'kind': 'unmatched',
              'description': 'Door gasket seal',
              'amount_paise': 0,
              'payer': 'household',
              'needs_checking': true,
            },
            <String, dynamic>{
              'kind': 'gst',
              'description': 'GST (18%)',
              'amount_paise': 21600,
              'payer': 'household',
            },
          ],
          'total_paise': 186600,
          'household_paise': 141600,
          'covered_paise': 45000,
          'approved_at': approved ? '2026-11-21T08:00:00Z' : null,
        };

    final mockHttp = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/public/quotes/tok-q1') && request.method == 'GET') {
        return http.Response(
          jsonEncode(<String, dynamic>{
            'centre_name': 'Frost and Wave Service Point, Kukatpally',
            'appliance_summary': 'Wavecrest WC-FL700 · Washing Machine',
            'quote': quoteJson(approved: quoteApproved),
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (path.endsWith('/public/quotes/tok-q1/approve')) {
        quoteApproved = true;
        return http.Response(
          jsonEncode(quoteJson(approved: true)),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (path.endsWith('/public/quotes/tok-q1/pay-intent')) {
        return http.Response(
          jsonEncode(<String, dynamic>{
            'id': 'pay_01',
            'quote_id': 'q_01',
            'amount_paise': 141600,
            'status': 'created',
            'method': 'google_pay',
            'upi_intent_url': 'upi://pay?pa=frostwave@upi&am=1416.00',
            'google_pay': <String, dynamic>{
              'environment': 'TEST',
              'merchant_name': 'Frost and Wave Service Point',
              'merchant_id': 'BCR2DN4TKEEPWELL',
              'gateway': 'keepwell_sandbox',
              'gateway_merchant_id': 'kw_fw_001',
              'transaction_info': <String, dynamic>{
                'currency_code': 'INR',
                'total_price_status': 'FINAL',
                'total_price': '1416.00',
              },
            },
            'created_at': '2026-11-21T08:05:00Z',
            'expires_at': '2026-11-21T08:35:00Z',
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (path.endsWith('/public/quotes/tok-q1/payment/sandbox-complete')) {
        sandboxCompleted = true;
        return http.Response(
          jsonEncode(<String, dynamic>{
            'id': 'pay_01',
            'quote_id': 'q_01',
            'amount_paise': 141600,
            'status': 'paid',
            'method': 'google_pay',
            'payment_ref': 'SBX-REF-991',
            'created_at': '2026-11-21T08:05:00Z',
            'expires_at': '2026-11-21T08:35:00Z',
            'paid_at': '2026-11-21T08:06:00Z',
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      if (path.endsWith('/public/otp/tok-q1/confirm')) {
        otpConfirmed = true;
        return http.Response(
          jsonEncode(<String, dynamic>{
            'status': 'closed',
            'ticket_id': 'TKT-7741',
          }),
          200,
          headers: const <String, String>{'content-type': 'application/json'},
        );
      }
      return http.Response('{}', 404);
    });

    final api = KwApiClient(
      config: const KwConfig(paymentMode: 'sandbox'),
      httpClient: mockHttp,
    );
    addTearDown(api.close);

    await tester.pumpWidget(
      _wrapScreen(
        QuoteApprovalScreen(
          token: 'tok-q1',
          apiClient: api,
          activeCentre: KwAuthHelper.demoCentres[2],
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Explicit OTP boundary banner is always visible.
    expect(
      find.text(
        'Payment does not close the job — only your OTP closes the repair.',
      ),
      findsOneWidget,
    );
    // Unmatched part shows "Needs checking" treatment.
    expect(find.text('Needs checking'), findsOneWidget);
    expect(find.text('₹1,416.00'), findsOneWidget);

    // 1. Approve quote.
    await tester.scrollUntilVisible(
      find.text('Approve quote'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.text('Approve quote'));
    await tester.tap(find.text('Approve quote'));
    await tester.pumpAndSettle();
    expect(quoteApproved, isTrue);

    // 2. Initiate Google Pay (TEST) and verify transaction sheet.
    await tester.scrollUntilVisible(
      find.text('Google Pay (TEST)'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.text('Google Pay (TEST)'));
    await tester.tap(find.text('Google Pay (TEST)'));
    await tester.pumpAndSettle();
    expect(
      find.text('Google Pay (TEST) Transaction Sheet'),
      findsOneWidget,
    );

    // 3. Complete sandbox test payment (Success).
    await tester.scrollUntilVisible(
      find.text('Complete test payment (Success)'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.text('Complete test payment (Success)'));
    await tester.tap(find.text('Complete test payment (Success)'));
    await tester.pumpAndSettle();
    expect(sandboxCompleted, isTrue);
    expect(find.text('PAID'), findsOneWidget);

    // 4. Enter 6-digit OTP to close repair.
    await tester.scrollUntilVisible(
      find.byType(KwOtpInput),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.byType(KwOtpInput));
    final firstOtpField = find.descendant(
      of: find.byType(KwOtpInput),
      matching: find.byType(TextField),
    );
    await tester.enterText(firstOtpField.first, '482910');
    await tester.pumpAndSettle();

    expect(otpConfirmed, isTrue);
    expect(find.text('Repair closed with your OTP'), findsOneWidget);
    expect(find.text('Reference: TKT-7741'), findsOneWidget);
  });
}
