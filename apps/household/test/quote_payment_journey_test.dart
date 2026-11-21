import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_household/src/quote_approval_screen.dart';
import 'package:kw_ui/kw_ui.dart';

void main() {
  testWidgets(
      'Journey: Quote approval -> Google Pay TEST -> sandbox payment does NOT close job until OTP confirmed',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    var approved = false;
    var paid = false;
    var otpClosed = false;

    final mockHttp = MockClient((req) async {
      final p = req.url.path;
      if (p.endsWith('/public/quotes/tok-j1') && req.method == 'GET') {
        return http.Response(
          jsonEncode({
            'centre_name': 'Frost and Wave Service Point, Kukatpally',
            'appliance_summary': 'Wavecrest WC-FL85 · Washing Machine',
            'quote': {
              'id': 'q-j1',
              'version': 2,
              'quote_type': 'firm',
              'lines': [
                {
                  'kind': 'part',
                  'description': 'Drain Pump Motor (WC-DP-85)',
                  'amount_paise': 135000,
                  'payer': 'household',
                },
                {
                  'kind': 'labour',
                  'description': 'Repair labour + visit',
                  'amount_paise': 45000,
                  'payer': 'household',
                },
                {
                  'kind': 'gst',
                  'description': 'GST 18%',
                  'amount_paise': 32400,
                  'payer': 'household',
                },
              ],
              'total_paise': 212400,
              'household_paise': 212400,
              'covered_paise': 0,
              'approved_at': approved ? '2026-11-21T10:00:00Z' : null,
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (p.endsWith('/public/quotes/tok-j1/approve')) {
        approved = true;
        return http.Response(
          jsonEncode({
            'id': 'q-j1',
            'version': 2,
            'quote_type': 'firm',
            'lines': [],
            'total_paise': 212400,
            'household_paise': 212400,
            'covered_paise': 0,
            'approved_at': '2026-11-21T10:00:00Z',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (p.endsWith('/public/quotes/tok-j1/pay-intent')) {
        return http.Response(
          jsonEncode({
            'id': 'pi-j1',
            'quote_id': 'q-j1',
            'amount_paise': 212400,
            'status': 'created',
            'method': 'google_pay',
            'google_pay': {
              'environment': 'TEST',
              'merchant_name': 'Frost and Wave Service Point',
              'merchant_id': 'BCR2DN4TKEEPWELL',
              'gateway': 'keepwell_sandbox',
              'gateway_merchant_id': 'kw_fw_001',
              'transaction_info': {
                'currency_code': 'INR',
                'total_price_status': 'FINAL',
                'total_price': '2124.00',
              },
            },
            'created_at': '2026-11-21T10:01:00Z',
            'expires_at': '2026-11-21T10:31:00Z',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (p.endsWith('/public/quotes/tok-j1/payment/sandbox-complete')) {
        paid = true;
        return http.Response(
          jsonEncode({
            'id': 'pi-j1',
            'quote_id': 'q-j1',
            'amount_paise': 212400,
            'status': 'paid',
            'method': 'google_pay',
            'payment_ref': 'SBX-J1-PAID',
            'created_at': '2026-11-21T10:01:00Z',
            'expires_at': '2026-11-21T10:31:00Z',
            'paid_at': '2026-11-21T10:02:00Z',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (p.endsWith('/public/otp/tok-j1/confirm')) {
        otpClosed = true;
        return http.Response(
          jsonEncode({'status': 'closed', 'ticket_id': 'T-C03'}),
          200,
          headers: {'content-type': 'application/json'},
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
      KwLocaleScope(
        languageCode: 'en',
        child: MaterialApp(
          theme: KwTheme.light(),
          home: Scaffold(
            body: QuoteApprovalScreen(
              token: 'tok-j1',
              apiClient: api,
              activeCentre: KwAuthHelper.demoCentres[2],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final scroll = find.byType(Scrollable).first;

    // 1. Approve firm quote
    await tester.scrollUntilVisible(find.text('Approve quote'), 200, scrollable: scroll);
    await tester.tap(find.text('Approve quote'));
    await tester.pumpAndSettle();
    expect(approved, isTrue);

    // 2. Pay via Google Pay TEST sandbox
    await tester.scrollUntilVisible(find.text('Google Pay (TEST)'), 200, scrollable: scroll);
    await tester.tap(find.text('Google Pay (TEST)'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Complete test payment (Success)'), 200, scrollable: scroll);
    await tester.tap(find.text('Complete test payment (Success)'));
    await tester.pumpAndSettle();

    // Payment is PAID, but job is NOT closed yet!
    expect(paid, isTrue);
    expect(otpClosed, isFalse);
    expect(find.text('PAID'), findsOneWidget);
    expect(find.text('Repair closed with your OTP'), findsNothing);

    // 3. Confirm OTP -> job closes
    await tester.scrollUntilVisible(find.byType(KwOtpInput), 200, scrollable: scroll);
    final firstDigit = find.descendant(
      of: find.byType(KwOtpInput),
      matching: find.byType(TextField),
    );
    await tester.enterText(firstDigit.first, '918273');
    await tester.pumpAndSettle();

    expect(otpClosed, isTrue);
    expect(find.text('Repair closed with your OTP'), findsOneWidget);
  });
}
