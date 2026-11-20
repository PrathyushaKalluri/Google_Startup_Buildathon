import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kw_ui/kw_ui.dart';

Widget _wrap({
  required Widget child,
  KwThemePreset preset = KwThemePreset.light,
  String lang = 'en',
  double textScale = 1.0,
  bool disableAnimations = false,
}) {
  final locale = Locale(lang);
  return MaterialApp(
    theme: KwTheme.fromPreset(preset, locale: locale),
    locale: locale,
    builder: (context, inner) {
      final mq = MediaQuery.of(context);
      return MediaQuery(
        data: mq.copyWith(
          textScaler: TextScaler.linear(textScale),
          disableAnimations: disableAnimations,
        ),
        child: KwLocaleScope(
          languageCode: lang,
          child: inner ?? const SizedBox.shrink(),
        ),
      );
    },
    home: Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: child,
      ),
    ),
  );
}

void main() {
  group('Formatters & Tokens', () {
    test('formatInrPaise uses Indian lakh grouping', () {
      expect(formatInrPaise(12540000), '₹1,25,400');
      expect(formatInrPaise(125050), '₹1,250.50');
      expect(formatInrPaise(125000, showZeroDecimals: true), '₹1,250.00');
      expect(formatInrPaise(0), '₹0');
      expect(formatInrPaise(-50000), '-₹500');
      expect(formatInrRange(45000, 85000), '₹450 – ₹850');
    });

    test('formatIstDateTime converts UTC to +05:30 IST', () {
      final utc = DateTime.utc(2026, 11, 21, 5, 30);
      expect(formatIstDateTime(utc), '21 Nov, 11:00 AM IST');
    });

    test('KwWindowSize maps adaptive breakpoints accurately', () {
      expect(KwWindowSize.fromWidth(390), KwWindowSize.compact);
      expect(KwWindowSize.fromWidth(720), KwWindowSize.medium);
      expect(KwWindowSize.fromWidth(1024), KwWindowSize.expanded);
      expect(KwWindowSize.fromWidth(1440), KwWindowSize.large);
    });

    test('All 34 Contract §8 event types resolve cleanly + unknown fallback', () {
      expect(KwEventVisualMeta.allContractTypes.length, 34);
      for (final type in KwEventVisualMeta.allContractTypes) {
        final meta = KwEventVisualMeta.resolve(type);
        expect(meta.category.isNotEmpty, isTrue);
      }
      final fallback = KwEventVisualMeta.resolve('unknown_future_event');
      expect(fallback.category, 'Event');
      expect(fallback.tone, KwEventTone.neutral);
    });
  });

  group('All 16+ Components across themes, locales & 200% text scale', () {
    Widget buildAllComponents() {
      final start = DateTime.utc(2026, 11, 21, 5, 30);
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Wrap(
            spacing: KwSpacing.xs,
            runSpacing: KwSpacing.xs,
            children: [
              KwUrgencyChip(urgency: KwUrgencyClass.safety),
              KwUrgencyChip(urgency: KwUrgencyClass.urgent),
              KwUrgencyChip(urgency: KwUrgencyClass.standard),
              KwUrgencyChip(urgency: KwUrgencyClass.planned),
            ],
          ),
          const SizedBox(height: KwSpacing.sm),
          KwCaseCard(
            ticketId: 't_1',
            urgency: KwUrgencyClass.safety,
            triggerLabel: 'Household call',
            householdName: 'Srinivas Rao',
            applianceLabel: 'Heatwell HW-G25',
            locality: 'Banjara Hills',
            summary: 'Burning smell near wall socket.',
            neededBy: start,
            unread: true,
            onTap: () {},
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwStatusStepper(currentStep: 2),
          const SizedBox(height: KwSpacing.sm),
          const KwConsentGateCard(
            gate1: KwConsentGateState(
              gate: 1,
              answer: KwConsentAnswer.yes,
            ),
            gate2: KwConsentGateState(
              gate: 2,
              answer: KwConsentAnswer.yes,
              choice: KwConsentChoice.switchToVideo,
            ),
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwConfidenceMeter(
            probability: 0.4,
            abstained: true,
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwSourceCitationChip(
            docTitle: 'Wavecrest Manual',
            page: 42,
            snippet: 'Inspect drain filter first.',
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwCandidateScoreBar(
            initiallyExpanded: true,
            breakdown: KwCandidateScoreBreakdown(
              fixConfidence: 27,
              partsReadiness: 22,
              timeToVisit: 18,
              routeCost: 12,
              reliability: 4,
              householdFit: 5,
            ),
          ),
          const SizedBox(height: KwSpacing.sm),
          KwTranscriptBubble(
            speaker: KwTranscriptSpeaker.agent,
            text: 'Checking your appliance details.',
            languageCode: 'en',
            modality: KwTranscriptModality.video,
            timestamp: start,
            liveRegion: true,
          ),
          const SizedBox(height: KwSpacing.sm),
          KwWaveformControls(
            isMuted: false,
            isSpeakerOn: true,
            isVideoActive: true,
            audioLevel: 0.6,
            onToggleMute: () {},
            onToggleSpeaker: () {},
            onToggleVideo: () {},
            onEndCall: () {},
          ),
          const SizedBox(height: KwSpacing.sm),
          KwEventRow(
            type: 'safety_stop_sent',
            title: 'Stop-use notice sent to household',
            actor: 'agent',
            at: start,
          ),
          const SizedBox(height: KwSpacing.sm),
          KwSlotPicker(
            selectedId: 's1',
            onSelected: (_) {},
            options: [
              KwSlotOption(
                id: 's1',
                start: start,
                end: start.add(const Duration(hours: 2)),
                priceLowPaise: 50000,
                priceHighPaise: 95000,
                recommended: true,
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwRouteEtaBar(
            driveMinutes: 15,
            distanceKm: 4.5,
            isStaticFallback: true,
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwMoneyLine(
            description: 'Drain pump assembly',
            amountPaise: 125050,
            payer: KwPayer.household,
          ),
          const SizedBox(height: KwSpacing.xs),
          const KwMoneyLine(
            description: 'Unmatched part',
            payer: KwPayer.household,
            needsChecking: true,
          ),
          const SizedBox(height: KwSpacing.sm),
          const KwOtpInput(),
          const SizedBox(height: KwSpacing.sm),
          const KwFvrGauge(rate: 0.88),
          const SizedBox(height: KwSpacing.sm),
          const KwEmptyState(),
          KwErrorState(onRetry: () {}),
          const KwSkeletonLoader(lines: 2),
        ],
      );
    }

    for (final preset in [
      KwThemePreset.light,
      KwThemePreset.dark,
      KwThemePreset.highContrastLight,
      KwThemePreset.projector,
    ]) {
      testWidgets('renders all components cleanly in $preset', (tester) async {
        await tester.pumpWidget(
          _wrap(
            preset: preset,
            disableAnimations: true,
            child: buildAllComponents(),
          ),
        );
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull);
      });
    }

    for (final lang in ['en', 'hi', 'te']) {
      testWidgets('renders all components cleanly in locale $lang at 200% scale',
          (tester) async {
        await tester.pumpWidget(
          _wrap(
            lang: lang,
            textScale: 2.0,
            disableAnimations: true,
            child: buildAllComponents(),
          ),
        );
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull);

        final strings = KwStrings.forLanguageCode(lang);
        expect(find.text(strings.urgencySafety), findsAtLeastNWidgets(1));
        expect(find.text(strings.needsChecking), findsAtLeastNWidgets(1));
      });
    }
  });

  group('Interaction & Semantics', () {
    testWidgets('KwSourceCitationChip opens snippet bottom sheet on tap',
        (tester) async {
      await tester.pumpWidget(
        _wrap(
          child: const KwSourceCitationChip(
            docTitle: 'Wavecrest Manual',
            page: 42,
            snippet: 'Check coin trap before replacing pump.',
          ),
        ),
      );

      await tester.tap(find.text('Wavecrest Manual'));
      await tester.pumpAndSettle();
      expect(find.text('Check coin trap before replacing pump.'), findsOneWidget);
    });

    testWidgets('KwOtpInput handles 6-digit paste and fires onCompleted',
        (tester) async {
      String? completed;
      await tester.pumpWidget(
        _wrap(
          child: KwOtpInput(
            onCompleted: (code) => completed = code,
          ),
        ),
      );

      await tester.enterText(find.byType(TextField).first, '482910');
      await tester.pump();
      expect(completed, '482910');
    });

    testWidgets('KwWaveformControls enforces >= 48dp touch targets',
        (tester) async {
      await tester.pumpWidget(
        _wrap(
          child: KwWaveformControls(
            isMuted: false,
            isSpeakerOn: true,
            isVideoActive: false,
            audioLevel: 0.5,
            onToggleMute: () {},
            onToggleSpeaker: () {},
            onToggleVideo: () {},
            onEndCall: () {},
          ),
        ),
      );

      final inkWells = tester.widgetList<InkWell>(find.byType(InkWell));
      expect(inkWells.length, 4);
      for (final finder in [
        find.byIcon(Icons.mic_rounded),
        find.byIcon(Icons.volume_up_rounded),
        find.byIcon(Icons.videocam_outlined),
        find.byIcon(Icons.call_end_rounded),
      ]) {
        final size = tester.getSize(
          find.ancestor(of: finder, matching: find.byType(InkWell)).first,
        );
        expect(size.width, greaterThanOrEqualTo(48));
        expect(size.height, greaterThanOrEqualTo(48));
      }
    });

    testWidgets('KwFvrGauge exposes accessible numeric semantics',
        (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _wrap(
          disableAnimations: true,
          child: const KwFvrGauge(rate: 0.88),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.bySemanticsLabel(RegExp(r'FVR-14: 88%')),
        findsOneWidget,
      );
      handle.dispose();
    });
  });
}
