import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kw_ui/kw_ui.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();
  runApp(const KwGalleryApp());
}

class KwGalleryApp extends StatefulWidget {
  const KwGalleryApp({super.key});

  @override
  State<KwGalleryApp> createState() => _KwGalleryAppState();
}

class _KwGalleryAppState extends State<KwGalleryApp> {
  KwThemePreset _preset = KwThemePreset.light;
  String _lang = 'en';
  double _textScale = 1.0;
  bool _reduceMotion = false;

  @override
  Widget build(BuildContext context) {
    final locale = Locale(_lang);
    return MaterialApp(
      title: 'Keepwell UI Gallery',
      debugShowCheckedModeBanner: false,
      theme: KwTheme.fromPreset(_preset, locale: locale),
      locale: locale,
      supportedLocales: const [Locale('en'), Locale('hi'), Locale('te')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) {
        final mq = MediaQuery.of(context);
        return MediaQuery(
          data: mq.copyWith(
            textScaler: TextScaler.linear(_textScale),
            disableAnimations: _reduceMotion,
          ),
          child: KwLocaleScope(
            languageCode: _lang,
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
      home: _GalleryHome(
        preset: _preset,
        lang: _lang,
        textScale: _textScale,
        reduceMotion: _reduceMotion,
        onPresetChanged: (v) => setState(() => _preset = v),
        onLangChanged: (v) => setState(() => _lang = v),
        onTextScaleChanged: (v) => setState(() => _textScale = v),
        onReduceMotionChanged: (v) => setState(() => _reduceMotion = v),
      ),
    );
  }
}

class _GalleryHome extends StatefulWidget {
  const _GalleryHome({
    required this.preset,
    required this.lang,
    required this.textScale,
    required this.reduceMotion,
    required this.onPresetChanged,
    required this.onLangChanged,
    required this.onTextScaleChanged,
    required this.onReduceMotionChanged,
  });

  final KwThemePreset preset;
  final String lang;
  final double textScale;
  final bool reduceMotion;
  final ValueChanged<KwThemePreset> onPresetChanged;
  final ValueChanged<String> onLangChanged;
  final ValueChanged<double> onTextScaleChanged;
  final ValueChanged<bool> onReduceMotionChanged;

  @override
  State<_GalleryHome> createState() => _GalleryHomeState();
}

class _GalleryHomeState extends State<_GalleryHome> {
  int _stepperIndex = 3;
  bool _muted = false;
  bool _speakerOn = true;
  bool _videoActive = true;
  String _selectedSlot = 'slot_1';
  double _fvrRate = 0.88;
  String _otpValue = '';
  bool _showAll34Events = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final sampleStart = DateTime.utc(2026, 11, 21, 5, 30); // 11:00 AM IST

    return Scaffold(
      appBar: AppBar(
        title: const Text('Keepwell UI Gallery'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(68),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(
              KwSpacing.md,
              0,
              KwSpacing.md,
              KwSpacing.sm,
            ),
            child: Row(
              children: [
                DropdownButton<KwThemePreset>(
                  value: widget.preset,
                  onChanged: (v) {
                    if (v != null) widget.onPresetChanged(v);
                  },
                  items: const [
                    DropdownMenuItem(
                      value: KwThemePreset.light,
                      child: Text('Light'),
                    ),
                    DropdownMenuItem(
                      value: KwThemePreset.dark,
                      child: Text('Dark'),
                    ),
                    DropdownMenuItem(
                      value: KwThemePreset.highContrastLight,
                      child: Text('High-Contrast Light'),
                    ),
                    DropdownMenuItem(
                      value: KwThemePreset.highContrastDark,
                      child: Text('High-Contrast Dark'),
                    ),
                    DropdownMenuItem(
                      value: KwThemePreset.projector,
                      child: Text('Projector (Stage)'),
                    ),
                  ],
                ),
                const SizedBox(width: KwSpacing.md),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'en', label: Text('EN')),
                    ButtonSegment(value: 'hi', label: Text('हिन्दी')),
                    ButtonSegment(value: 'te', label: Text('తెలుగు')),
                  ],
                  selected: {widget.lang},
                  onSelectionChanged: (s) => widget.onLangChanged(s.first),
                ),
                const SizedBox(width: KwSpacing.md),
                SegmentedButton<double>(
                  segments: const [
                    ButtonSegment(value: 1.0, label: Text('100%')),
                    ButtonSegment(value: 2.0, label: Text('200%')),
                  ],
                  selected: {widget.textScale},
                  onSelectionChanged: (s) => widget.onTextScaleChanged(s.first),
                ),
                const SizedBox(width: KwSpacing.md),
                FilterChip(
                  label: const Text('Reduce motion'),
                  selected: widget.reduceMotion,
                  onSelected: widget.onReduceMotionChanged,
                ),
              ],
            ),
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(KwSpacing.md),
        children: [
          const _Section(
            title: '1. Urgency Chips (Colour + Icon + Label)',
            child: Wrap(
              spacing: KwSpacing.sm,
              runSpacing: KwSpacing.sm,
              children: [
                KwUrgencyChip(urgency: KwUrgencyClass.safety),
                KwUrgencyChip(urgency: KwUrgencyClass.urgent),
                KwUrgencyChip(urgency: KwUrgencyClass.standard),
                KwUrgencyChip(urgency: KwUrgencyClass.planned),
              ],
            ),
          ),
          _Section(
            title: '2. Case Cards',
            child: Column(
              children: [
                KwCaseCard(
                  ticketId: 't_safety',
                  urgency: KwUrgencyClass.safety,
                  triggerLabel: 'Household call',
                  householdName: 'Srinivas Rao',
                  locality: 'Banjara Hills, 500034',
                  applianceLabel: 'Heatwell HW-G25 · Storage Geyser',
                  summary: 'Burning smell near power socket when switched on.',
                  neededBy: sampleStart,
                  statusLabel: 'Immediate dispatch',
                  unread: true,
                  onTap: () {},
                ),
                const SizedBox(height: KwSpacing.sm),
                KwCaseCard(
                  ticketId: 't_c03',
                  urgency: KwUrgencyClass.urgent,
                  triggerLabel: 'Household call · HI',
                  householdName: 'Priya Sharma',
                  locality: 'Kukatpally, 500072',
                  applianceLabel: 'Wavecrest WC-FL70 · Front-load Washer',
                  summary: 'Error E21; water not draining after rinse cycle.',
                  neededBy: sampleStart.add(const Duration(hours: 4)),
                  statusLabel: 'Technician assigned',
                  selected: true,
                  onTap: () {},
                ),
              ],
            ),
          ),
          _Section(
            title: '3. Status Stepper (6 Phases)',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                KwStatusStepper(currentStep: _stepperIndex),
                const SizedBox(height: KwSpacing.sm),
                Wrap(
                  spacing: KwSpacing.xs,
                  children: [
                    for (var i = 0; i < 6; i++)
                      ChoiceChip(
                        label: Text('Step ${i + 1}'),
                        selected: _stepperIndex == i,
                        onSelected: (_) => setState(() => _stepperIndex = i),
                      ),
                  ],
                ),
              ],
            ),
          ),
          const _Section(
            title: '4. Consent Gate Cards',
            child: Column(
              children: [
                KwConsentGateCard(
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
                SizedBox(height: KwSpacing.sm),
                KwConsentGateCard(
                  gate1: KwConsentGateState(
                    gate: 1,
                    answer: KwConsentAnswer.notAsked,
                    notAskedReason: 'safety_flag',
                  ),
                  gate2: KwConsentGateState(
                    gate: 2,
                    answer: KwConsentAnswer.notAsked,
                    notAskedReason: 'safety_flag',
                  ),
                ),
                SizedBox(height: KwSpacing.sm),
                KwConsentGateCard(
                  gate1: KwConsentGateState(
                    gate: 1,
                    answer: KwConsentAnswer.silence,
                  ),
                  gate2: KwConsentGateState(
                    gate: 2,
                    answer: KwConsentAnswer.notAsked,
                    notAskedReason: 'gate_1_declined',
                  ),
                ),
              ],
            ),
          ),
          _Section(
            title: '5. Confidence Meter & PAIR Abstention',
            child: Column(
              children: [
                KwConfidenceMeter(
                  probability: 0.86,
                  label: 'Drain pump impeller blockage (E21)',
                  evidenceCount: 3,
                  onInspectEvidence: () {},
                ),
                const SizedBox(height: KwSpacing.md),
                const KwConfidenceMeter(
                  probability: 0.32,
                  label: 'Control board fault',
                  abstained: true,
                  abstentionReason:
                      'Symptom matches two separate wiring faults; on-site multimeter check required.',
                ),
              ],
            ),
          ),
          const _Section(
            title: '6. Source Citation Chips',
            child: Wrap(
              spacing: KwSpacing.sm,
              runSpacing: KwSpacing.sm,
              children: [
                KwSourceCitationChip(
                  docTitle: 'Wavecrest WC-FL70 Service Manual',
                  page: 42,
                  uri: 'kb://wavecrest/wc-fl70-manual.pdf#page=42',
                  snippet:
                      'Error E21 indicates drain timeout (> 180 s). Inspect coin trap first; if clear, test drain pump coil resistance (140–180 Ω).',
                ),
                KwSourceCitationChip(
                  docTitle: 'Safe-Fix Catalogue · SF-DRN-01',
                  snippet:
                      'Unplug machine, place shallow tray under lower front flap, slowly unscrew drain filter cap counter-clockwise.',
                ),
              ],
            ),
          ),
          const _Section(
            title: '7. Candidate Score Bar (6 Factors — Never Price)',
            child: KwCandidateScoreBar(
              initiallyExpanded: true,
              breakdown: KwCandidateScoreBreakdown(
                fixConfidence: 27,
                partsReadiness: 24,
                timeToVisit: 17,
                routeCost: 13,
                reliability: 4.5,
                householdFit: 4.5,
              ),
            ),
          ),
          _Section(
            title: '8. Transcript Bubbles',
            child: Column(
              children: [
                KwTranscriptBubble(
                  speaker: KwTranscriptSpeaker.agent,
                  languageCode: 'hi',
                  modality: KwTranscriptModality.voice,
                  timestamp: sampleStart,
                  text:
                      'नमस्ते, यह फ्रॉस्ट एंड वेव सर्विस पॉइंट है। यह कॉल आपकी सहायता के लिए रिकॉर्ड की जा सकती है।',
                ),
                const SizedBox(height: KwSpacing.xs),
                KwTranscriptBubble(
                  speaker: KwTranscriptSpeaker.household,
                  languageCode: 'hi',
                  modality: KwTranscriptModality.video,
                  timestamp: sampleStart.add(const Duration(minutes: 1)),
                  text: 'हाँ, मैंने वीडियो चालू कर दिया है — डिस्प्ले पर E21 दिख रहा है।',
                ),
                const SizedBox(height: KwSpacing.xs),
                const KwTranscriptBubble(
                  speaker: KwTranscriptSpeaker.household,
                  languageCode: 'te',
                  modality: KwTranscriptModality.voice,
                  isFinal: false,
                  text: 'డ్రైన్ ఫిల్టర్ శుభ్రం చేశాను కానీ...',
                ),
              ],
            ),
          ),
          _Section(
            title: '9. Waveform Call Controls',
            child: KwWaveformControls(
              isMuted: _muted,
              isSpeakerOn: _speakerOn,
              isVideoActive: _videoActive,
              audioLevel: 0.72,
              statusText: _videoActive ? 'Live video · 02:14' : 'Voice · 02:14',
              onToggleMute: () => setState(() => _muted = !_muted),
              onToggleSpeaker: () => setState(() => _speakerOn = !_speakerOn),
              onToggleVideo: () => setState(() => _videoActive = !_videoActive),
              onEndCall: () {},
            ),
          ),
          _Section(
            title: '10. Event Rows (34 Contract §8 Types + Unknown Fallback)',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                FilterChip(
                  label: Text(
                    _showAll34Events
                        ? 'Showing all 34 + fallback'
                        : 'Show all 34 Contract types',
                  ),
                  selected: _showAll34Events,
                  onSelected: (v) => setState(() => _showAll34Events = v),
                ),
                const SizedBox(height: KwSpacing.xs),
                for (final type in _showAll34Events
                    ? [
                        ...KwEventVisualMeta.allContractTypes,
                        'custom_future_event',
                      ]
                    : const [
                        'conversation_started',
                        'safety_stop_sent',
                        'modality_changed',
                        'candidates_scored',
                        'reassigned',
                        'ticket_closed',
                        'custom_future_event',
                      ])
                  KwEventRow(
                    type: type,
                    title: 'Sample event for $type',
                    detail: 'Contract §8 treatment verification',
                    actor: 'agent',
                    at: sampleStart,
                  ),
              ],
            ),
          ),
          _Section(
            title: '11. Slot Picker (en-IN Price Ranges)',
            child: KwSlotPicker(
              selectedId: _selectedSlot,
              onSelected: (opt) => setState(() => _selectedSlot = opt.id),
              options: [
                KwSlotOption(
                  id: 'slot_1',
                  start: sampleStart,
                  end: sampleStart.add(const Duration(hours: 2)),
                  priceLowPaise: 65000,
                  priceHighPaise: 145000,
                  recommended: true,
                  technicianName: 'Ramesh Kumar',
                ),
                KwSlotOption(
                  id: 'slot_2',
                  start: sampleStart.add(const Duration(hours: 3)),
                  end: sampleStart.add(const Duration(hours: 5)),
                  priceLowPaise: 65000,
                  priceHighPaise: 145000,
                  technicianName: 'Anil Verma',
                ),
                KwSlotOption(
                  id: 'slot_3',
                  start: sampleStart.add(const Duration(hours: 24)),
                  end: sampleStart.add(const Duration(hours: 26)),
                  priceLowPaise: 55000,
                  priceHighPaise: 125000,
                  technicianName: 'Kiran Reddy',
                ),
              ],
            ),
          ),
          const _Section(
            title: '12. Route ETA Bars (Live + Static Fallback)',
            child: Wrap(
              spacing: KwSpacing.sm,
              runSpacing: KwSpacing.sm,
              children: [
                KwRouteEtaBar(
                  driveMinutes: 18,
                  distanceKm: 6.4,
                  destinationLabel: 'Kukatpally',
                ),
                KwRouteEtaBar(
                  driveMinutes: 24,
                  distanceKm: 8.2,
                  destinationLabel: 'Gachibowli',
                  isStaticFallback: true,
                ),
              ],
            ),
          ),
          _Section(
            title: '13. Money Lines & "Needs checking" Invariant',
            child: Column(
              children: [
                const KwMoneyLine(
                  description: 'Drain pump assembly (WC-DP-210)',
                  partNo: 'WC-DP-210',
                  amountPaise: 125050,
                  payer: KwPayer.household,
                ),
                const SizedBox(height: KwSpacing.xs),
                const KwMoneyLine(
                  description: 'Authorised warranty labour',
                  amountPaise: 45000,
                  payer: KwPayer.brand,
                  showZeroDecimals: false,
                ),
                const SizedBox(height: KwSpacing.xs),
                const KwMoneyLine(
                  description: 'Unmatched rubber inlet hose',
                  partNo: 'UNVERIFIED-HOSE',
                  payer: KwPayer.household,
                  needsChecking: true,
                ),
                const SizedBox(height: KwSpacing.xs),
                Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    'Lakh grouping check: ${formatInrPaise(12540000)}',
                    style: KwTheme.monoStyle(context, color: cs.primary),
                  ),
                ),
              ],
            ),
          ),
          _Section(
            title: '14. OTP Input',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                KwOtpInput(
                  onChanged: (v) => setState(() => _otpValue = v),
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  'Entered: ${_otpValue.isEmpty ? '—' : _otpValue}',
                  style: KwTheme.monoStyle(context),
                ),
              ],
            ),
          ),
          _Section(
            title: '15. FVR-14 Radial Gauge',
            child: Column(
              children: [
                KwFvrGauge(rate: _fvrRate),
                Slider(
                  value: _fvrRate,
                  onChanged: (v) => setState(() => _fvrRate = v),
                ),
              ],
            ),
          ),
          _Section(
            title: '16. Empty, Error & Skeleton States',
            child: Column(
              children: [
                const KwEmptyState(),
                const Divider(),
                KwErrorState(onRetry: () {}),
                const Divider(),
                const Padding(
                  padding: EdgeInsets.all(KwSpacing.sm),
                  child: KwSkeletonLoader(lines: 3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: KwSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: KwSpacing.sm),
          child,
        ],
      ),
    );
  }
}
