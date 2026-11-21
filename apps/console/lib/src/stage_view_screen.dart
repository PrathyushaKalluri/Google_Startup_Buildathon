import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';
import 'test_call_sheet.dart';

/// Live Stage View (`/stage`) — the Demo Hero screen readable from the back
/// of an auditorium.
///
/// Includes Projector Mode toggle, calm idle state, and a built-in
/// "Play C03 Stage Call" button that connects directly to [LiveCallClient]
/// (`ws://localhost:8082/v1/live/call`) and animates every beat live even
/// without Firestore emulator.
class StageViewScreen extends StatefulWidget {
  const StageViewScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<StageViewScreen> createState() => _StageViewScreenState();
}

class _StageViewScreenState extends State<StageViewScreen> {
  LiveCallClient? _liveClient;
  StreamSubscription<LiveServerMessage>? _wsSub;
  Timer? _fallbackBeatTimer;
  int _fallbackStepIndex = 0;

  bool _isActive = false;
  bool _isConnecting = false;
  String _modality = 'voice';
  String _centreName = 'Frost and Wave Service Point, Kukatpally';
  String _householdLabel = 'Meera Rao · Kukatpally, 500072';
  String _applianceLabel = 'Wavecrest Front-Load Washer · WC-FL700-IN';
  String _authorityLabel = 'Authorised (Wavecrest) → Proceed';
  KwUrgencyClass _urgency = KwUrgencyClass.standard;
  List<String> _ruleCodes = const ['RULE_WATER_LEAK_CONTAINED'];

  KwConsentGateState _gate1 = const KwConsentGateState(
    gate: 1,
    answer: KwConsentAnswer.notAsked,
  );
  KwConsentGateState _gate2 = const KwConsentGateState(
    gate: 2,
    answer: KwConsentAnswer.notAsked,
  );

  int _fixStep = 0;
  final int _fixTotalSteps = 4;
  String _fixOutcome = 'Not started';

  // Diagnosis Before vs After re-run
  double _beforeDrainFilterProb = 0.0;
  double _beforeDrainPumpProb = 0.0;
  double _afterDrainFilterProb = 0.0;
  double _afterDrainPumpProb = 0.0;
  bool _diagnosisRerunDone = false;

  List<AssignmentCandidate> _candidates = const [];
  String _quoteStatus = 'Pending diagnosis';
  String _paymentStatus = 'Not initiated';
  String _otpStatus = 'Pending visit';

  final List<_StageTurn> _turns = [];
  final List<LiveEvent> _events = [];

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onControllerUpdated);
    _syncFromFirestoreFeed();
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onControllerUpdated);
    _fallbackBeatTimer?.cancel();
    _wsSub?.cancel();
    unawaited(_liveClient?.dispose());
    super.dispose();
  }

  void _onControllerUpdated() {
    if (!mounted) return;
    _syncFromFirestoreFeed();
  }

  void _syncFromFirestoreFeed() {
    // Live data path: Firestore `centres/{id}/feed` via kw_client LiveFeedRepository.
    if (!widget.controller.liveFeedRepository.shouldUseFirestore) return;
    final feed = widget.controller.liveFeed;
    if (feed.isEmpty) return;
    final existingIds = _events.map((e) => e.id).toSet();
    final incoming = feed.where((e) => !existingIds.contains(e.id)).toList();
    if (incoming.isEmpty) return;
    setState(() {
      _isActive = true;
      for (final ev in incoming.reversed) {
        _events.insert(0, ev);
        _applyLiveEventToStage(ev);
      }
    });
  }

  void _applyLiveEventToStage(LiveEvent ev) {
    final type = ev.type.toLowerCase();
    if (type == 'video_stream_started' || type == 'video_link_sent') {
      _modality = 'video';
    } else if (type == 'urgency_assessed') {
      final cls = ev.payload['urgency_class']?.toString();
      if (cls != null && cls.isNotEmpty) {
        _urgency = KwUrgencyClass.fromWire(cls);
      }
    } else if (type == 'consent_captured') {
      final gate = ev.payload['gate'] == 2 ? 2 : 1;
      final ans = ev.payload['answer']?.toString() ?? 'yes';
      final state = KwConsentGateState(
        gate: gate,
        answer: ans == 'no' ? KwConsentAnswer.no : KwConsentAnswer.yes,
      );
      if (gate == 1) {
        _gate1 = state;
      } else {
        _gate2 = state;
      }
    } else if (type == 'quote_approved') {
      _quoteStatus = 'Approved';
    } else if (type == 'payment_confirmed') {
      _paymentStatus = 'Paid (awaiting OTP)';
    } else if (type == 'otp_verified' || type == 'visit_closed') {
      _otpStatus = 'Verified · Closed';
    }
  }

  Future<void> _playC03StageCall() async {
    _resetStageState();
    setState(() {
      _isActive = true;
      _isConnecting = true;
    });

    await _wsSub?.cancel();
    await _liveClient?.dispose();
    final client = widget.controller.createLiveCallClient();
    _liveClient = client;

    var receivedAnyServerFrame = false;
    _wsSub = client.messages.listen((msg) {
      receivedAnyServerFrame = true;
      _handleLiveMessage(msg);
    });

    try {
      await client
          .start(
            centreKey: 'c_fw',
            callerNumber: '+919848011223',
            languageHint: 'en',
            authToken: widget.controller.session?.idToken,
          )
          .timeout(const Duration(seconds: 2));
      if (mounted) {
        setState(() => _isConnecting = false);
      }
      // If server connects but does not emit beats quickly, seed the C03 sequence.
      Future<void>.delayed(const Duration(milliseconds: 900), () {
        if (mounted && !receivedAnyServerFrame) {
          _startLocalC03BeatPlayback();
        }
      });
    } catch (_) {
      // Smoothly run the live C03 stage beat animation even without WS/Firestore.
      if (mounted) {
        setState(() => _isConnecting = false);
        _startLocalC03BeatPlayback();
      }
    }
  }

  void _resetStageState() {
    _fallbackBeatTimer?.cancel();
    _fallbackStepIndex = 0;
    _modality = 'voice';
    _urgency = KwUrgencyClass.standard;
    _ruleCodes = const ['RULE_WATER_LEAK_CONTAINED'];
    _gate1 = const KwConsentGateState(gate: 1, answer: KwConsentAnswer.notAsked);
    _gate2 = const KwConsentGateState(gate: 2, answer: KwConsentAnswer.notAsked);
    _fixStep = 0;
    _fixOutcome = 'Not started';
    _beforeDrainFilterProb = 0.0;
    _beforeDrainPumpProb = 0.0;
    _afterDrainFilterProb = 0.0;
    _afterDrainPumpProb = 0.0;
    _diagnosisRerunDone = false;
    _candidates = const [];
    _quoteStatus = 'Pending diagnosis';
    _paymentStatus = 'Not initiated';
    _otpStatus = 'Pending visit';
    _turns.clear();
    _events.clear();
  }

  void _handleLiveMessage(LiveServerMessage msg) {
    if (!mounted) return;
    setState(() {
      switch (msg) {
        case LiveReadyMessage():
          _isConnecting = false;
          if (msg.centreName.isNotEmpty) _centreName = msg.centreName;
          _events.insert(
            0,
            LiveEvent(
              id: 'ready_${DateTime.now().millisecondsSinceEpoch}',
              at: DateTime.now().toIso8601String(),
              centreId: 'c_fw',
              type: 'conversation_started',
              actor: 'agent',
              title: 'Live call connected · $_centreName',
              detail: msg.recordingNotice,
              payload: const {},
            ),
          );
        case LiveTranscriptMessage():
          _turns.add(
            _StageTurn(
              speaker: msg.speaker == 'household'
                  ? KwTranscriptSpeaker.household
                  : KwTranscriptSpeaker.agent,
              text: msg.text,
              lang: msg.lang,
              modality: _modality == 'video'
                  ? KwTranscriptModality.video
                  : KwTranscriptModality.voice,
              isFinal: msg.isFinal,
              at: DateTime.now(),
            ),
          );
        case LiveModalityMessage():
          _modality = msg.value;
        case LiveEventMessage():
          _applyEventToStage(msg.event);
        case LiveEndedMessage():
          _events.insert(
            0,
            LiveEvent(
              id: 'ended_${DateTime.now().millisecondsSinceEpoch}',
              at: DateTime.now().toIso8601String(),
              centreId: 'c_fw',
              type: 'ticket_closed',
              actor: 'system',
              title: 'Call completed (${msg.reason})',
              detail: msg.ticketId ?? '',
              payload: const {},
            ),
          );
        case LiveErrorMessage():
        case LiveUiHintMessage():
        case LiveAudioChunkMessage():
        case LiveVideoLinkMessage():
        case LiveGoAwayMessage():
        case LiveUnknownMessage():
          break;
      }
    });
  }

  void _applyEventToStage(LiveEvent ev) {
    _events.insert(0, ev);
    switch (ev.type) {
      case 'household_identified':
        if (ev.detail.isNotEmpty) _householdLabel = ev.detail;
      case 'appliance_identified':
        if (ev.detail.isNotEmpty) _applianceLabel = ev.detail;
      case 'authority_checked':
        if (ev.detail.isNotEmpty) _authorityLabel = ev.detail;
      case 'urgency_assessed':
        _urgency = KwUrgencyClass.fromWire(
          ev.payload['urgency_class']?.toString() ?? 'urgent',
        );
      case 'gate_answered':
        final gateNum = ev.payload['gate'] == 2 ? 2 : 1;
        if (gateNum == 1) {
          _gate1 = KwConsentGateState(
            gate: 1,
            answer: KwConsentAnswer.fromWire(
              ev.payload['answer']?.toString() ?? 'yes',
            ),
          );
        } else {
          _gate2 = KwConsentGateState(
            gate: 2,
            answer: KwConsentAnswer.fromWire(
              ev.payload['answer']?.toString() ?? 'yes',
            ),
            choice: KwConsentChoice.fromWire(
              ev.payload['choice']?.toString() ?? 'switch_to_video',
            ),
          );
        }
      case 'modality_changed':
        _modality = ev.payload['value']?.toString() ?? 'video';
      case 'fix_step':
        _fixStep = (_fixStep + 1).clamp(1, _fixTotalSteps);
        _fixOutcome = 'In progress ($_fixStep/$_fixTotalSteps)';
      case 'fix_result':
        _fixStep = _fixTotalSteps;
        _fixOutcome = ev.detail.isNotEmpty
            ? ev.detail
            : 'Failed — drain filter clear, water still standing';
      case 'diagnosis_updated':
        if (!_diagnosisRerunDone && _beforeDrainFilterProb == 0.0) {
          _beforeDrainFilterProb = 0.68;
          _beforeDrainPumpProb = 0.24;
        } else {
          _diagnosisRerunDone = true;
          _afterDrainFilterProb = 0.08;
          _afterDrainPumpProb = 0.86;
        }
      case 'candidates_scored':
        _candidates = _c03SampleCandidates;
      case 'quote_issued':
        _quoteStatus = 'Firm quote ₹1,450 issued';
      case 'quote_approved':
        _quoteStatus = 'Approved by household (₹1,450)';
      case 'payment_confirmed':
        _paymentStatus = 'Paid ₹1,450 via UPI Intent';
      case 'otp_sent':
        _otpStatus = 'Closure OTP verified (4821)';
      default:
        break;
    }
  }

  void _startLocalC03BeatPlayback() {
    _fallbackBeatTimer?.cancel();
    _fallbackStepIndex = 0;
    final beats = <VoidCallback>[
      () {
        _turns.add(
          _StageTurn(
            speaker: KwTranscriptSpeaker.household,
            text:
                'Hello, my Wavecrest washing machine is showing E20 and won’t drain water.',
            lang: 'en',
            modality: KwTranscriptModality.voice,
            isFinal: true,
            at: DateTime.now(),
          ),
        );
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_1',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'conversation_started',
            actor: 'agent',
            title: 'Inbound voice call · Frost & Wave',
            detail: 'Recording notice logged; caller matched to Meera Rao',
            payload: const {},
          ),
        );
        _urgency = KwUrgencyClass.urgent;
        _ruleCodes = const ['E20_STANDING_WATER', 'SAME_DAY_TARGET'];
      },
      () {
        _turns.add(
          _StageTurn(
            speaker: KwTranscriptSpeaker.agent,
            text:
                'I see your Wavecrest WC-FL700-IN is under our authorised service. Before booking a visit, would you like to try a safe 4-step drain filter check together?',
            lang: 'en',
            modality: KwTranscriptModality.voice,
            isFinal: true,
            at: DateTime.now(),
          ),
        );
        _gate1 = const KwConsentGateState(
          gate: 1,
          answer: KwConsentAnswer.yes,
        );
        _beforeDrainFilterProb = 0.68;
        _beforeDrainPumpProb = 0.24;
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_2',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'gate_answered',
            actor: 'household',
            title: 'Gate 1 accepted · Initial diagnosis ready',
            detail: 'Drain filter blockage 68% vs Drain pump motor 24%',
            payload: const {'gate': 1, 'answer': 'yes'},
          ),
        );
      },
      () {
        _modality = 'switching_to_video';
        _gate2 = const KwConsentGateState(
          gate: 2,
          answer: KwConsentAnswer.yes,
          choice: KwConsentChoice.switchToVideo,
        );
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_3',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'modality_changed',
            actor: 'household',
            title: 'Gate 2: Switching to live video',
            detail: 'Secure video link opened on household phone',
            payload: const {'value': 'switching_to_video'},
          ),
        );
      },
      () {
        _modality = 'video';
        _fixStep = 4;
        _fixOutcome = 'Failed on video — filter clean, pump hums without draining';
        _turns.add(
          _StageTurn(
            speaker: KwTranscriptSpeaker.household,
            text:
                'I opened the bottom filter on video — it is completely clean, still humming and E20 stays on.',
            lang: 'en',
            modality: KwTranscriptModality.video,
            isFinal: true,
            at: DateTime.now(),
          ),
        );
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_4',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'fix_result',
            actor: 'agent',
            title: 'Safe fix completed (4/4) — did not resolve',
            detail: 'Observed clean filter on video; triggering diagnosis re-run',
            payload: const {},
          ),
        );
      },
      () {
        _diagnosisRerunDone = true;
        _afterDrainFilterProb = 0.08;
        _afterDrainPumpProb = 0.86;
        _candidates = _c03SampleCandidates;
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_5',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'diagnosis_updated',
            actor: 'agent',
            title: 'Re-run diagnosis: Drain Pump Motor 86% (+62%)',
            detail: 'Visit plan updated with WC-DP-402 pump; top 3 technicians scored',
            payload: const {},
          ),
        );
      },
      () {
        _quoteStatus = 'Approved ₹1,450 (Pump + Labour)';
        _paymentStatus = 'Paid ₹1,450 via UPI Intent';
        _otpStatus = 'Closure OTP ready (4821)';
        _events.insert(
          0,
          LiveEvent(
            id: 'c03_6',
            at: DateTime.now().toIso8601String(),
            centreId: 'c_fw',
            type: 'technician_assigned',
            actor: 'agent',
            title: 'Assigned Ravi Kumar (#1 · 92/100) · Today 2:00–4:00 PM IST',
            detail: 'Carrying WC-DP-402 drain pump in van stock',
            payload: const {},
          ),
        );
      },
    ];

    // Emit first beat immediately so UI reacts right away.
    setState(() {
      beats[0]();
      _fallbackStepIndex = 1;
    });

    _fallbackBeatTimer = Timer.periodic(
      const Duration(milliseconds: 950),
      (timer) {
        if (!mounted || _fallbackStepIndex >= beats.length) {
          timer.cancel();
          return;
        }
        setState(() {
          beats[_fallbackStepIndex]();
          _fallbackStepIndex++;
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final ctrl = widget.controller;
    final size = KwWindowSize.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Stage header bar (always visible, compact in projector mode)
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: KwSpacing.md,
            vertical: KwSpacing.sm,
          ),
          color: cs.surfaceContainerLow,
          child: Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.xs,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.live_tv_rounded, color: cs.primary),
                  const SizedBox(width: KwSpacing.xs),
                  Text(
                    'Live Stage View',
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(width: KwSpacing.sm),
                  _ModalityPill(modality: _modality),
                ],
              ),
              Wrap(
                spacing: KwSpacing.xs,
                runSpacing: KwSpacing.xs,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  FilledButton.icon(
                    key: const Key('stage_play_c03_button'),
                    onPressed: _isConnecting ? null : _playC03StageCall,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: Text(
                      _isConnecting ? 'Connecting…' : 'Play C03 Stage Call',
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => showTestCallSheet(
                      context,
                      controller: ctrl,
                    ),
                    icon: const Icon(Icons.call_rounded),
                    label: const Text('Test Call'),
                  ),
                  FilterChip(
                    key: const Key('stage_projector_toggle'),
                    avatar: Icon(
                      ctrl.projectorMode
                          ? Icons.cast_connected_rounded
                          : Icons.cast_rounded,
                      size: 18,
                    ),
                    label: Text(
                      ctrl.projectorMode ? 'Exit Projector' : 'Projector Mode',
                    ),
                    selected: ctrl.projectorMode,
                    onSelected: ctrl.setProjectorMode,
                  ),
                ],
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: !_isActive
              ? KwEmptyState(
                  icon: Icons.sensors_rounded,
                  title:
                      'Nothing happening — start a C03 Stage Demo or Test Call',
                  body:
                      'Watch the agent work a live case: transcript, consent questions, safe fix, diagnosis re-run and technician scoring.',
                  action: FilledButton.icon(
                    onPressed: _playC03StageCall,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Play C03 Stage Call'),
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(KwSpacing.md),
                  child: size.isWide
                      ? Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 5,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  _buildTranscriptCard(context),
                                  const SizedBox(height: KwSpacing.md),
                                  _buildLiveFeedCard(context),
                                ],
                              ),
                            ),
                            const SizedBox(width: KwSpacing.md),
                            Expanded(
                              flex: 6,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  _buildAgentKnowsCard(context),
                                  const SizedBox(height: KwSpacing.md),
                                  KwConsentGateCard(
                                    gate1: _gate1,
                                    gate2: _gate2,
                                  ),
                                  const SizedBox(height: KwSpacing.md),
                                  _buildSelfFixCard(context),
                                  const SizedBox(height: KwSpacing.md),
                                  _buildDiagnosisBeforeAfterCard(context),
                                  const SizedBox(height: KwSpacing.md),
                                  _buildCandidatesCard(context),
                                  const SizedBox(height: KwSpacing.md),
                                  _buildSettlementCard(context),
                                ],
                              ),
                            ),
                          ],
                        )
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _buildAgentKnowsCard(context),
                            const SizedBox(height: KwSpacing.md),
                            _buildTranscriptCard(context),
                            const SizedBox(height: KwSpacing.md),
                            KwConsentGateCard(gate1: _gate1, gate2: _gate2),
                            const SizedBox(height: KwSpacing.md),
                            _buildSelfFixCard(context),
                            const SizedBox(height: KwSpacing.md),
                            _buildDiagnosisBeforeAfterCard(context),
                            const SizedBox(height: KwSpacing.md),
                            _buildCandidatesCard(context),
                            const SizedBox(height: KwSpacing.md),
                            _buildSettlementCard(context),
                            const SizedBox(height: KwSpacing.md),
                            _buildLiveFeedCard(context),
                          ],
                        ),
                ),
        ),
      ],
    );
  }

  Widget _buildTranscriptCard(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Live Conversation Transcript',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            if (_turns.isEmpty)
              const Text('Waiting for first voice turn…')
            else
              for (var i = 0; i < _turns.length; i++) ...[
                if (i > 0) const SizedBox(height: KwSpacing.xs),
                KwTranscriptBubble(
                  speaker: _turns[i].speaker,
                  text: _turns[i].text,
                  languageCode: _turns[i].lang,
                  modality: _turns[i].modality,
                  isFinal: _turns[i].isFinal,
                  timestamp: _turns[i].at,
                  liveRegion: i == _turns.length - 1,
                ),
              ],
          ],
        ),
      ),
    );
  }

  Widget _buildAgentKnowsCard(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'What the agent knows',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                KwUrgencyChip(urgency: _urgency, liveRegion: true),
                for (final code in _ruleCodes)
                  Chip(label: Text(code, style: KwTheme.monoStyle(context))),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            Text('Centre: $_centreName', style: theme.textTheme.bodyMedium),
            Text('Household: $_householdLabel', style: theme.textTheme.bodyMedium),
            Text('Appliance: $_applianceLabel', style: theme.textTheme.bodyMedium),
            Text('Authority: $_authorityLabel', style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }

  Widget _buildSelfFixCard(BuildContext context) {
    final theme = Theme.of(context);
    final progress = _fixTotalSteps == 0 ? 0.0 : _fixStep / _fixTotalSteps;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Guided Safe Fix · Drain Filter Check',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Text(
                  '$_fixStep / $_fixTotalSteps steps',
                  style: KwTheme.monoStyle(context),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            LinearProgressIndicator(value: progress),
            const SizedBox(height: KwSpacing.xs),
            Text(_fixOutcome, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagnosisBeforeAfterCard(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Diagnosis Probability · Before vs After Re-run',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            Text(
              'Before safe fix (initial)',
              style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            KwConfidenceMeter(
              probability: _beforeDrainFilterProb,
              label: 'Blocked drain filter',
            ),
            const SizedBox(height: KwSpacing.xs),
            KwConfidenceMeter(
              probability: _beforeDrainPumpProb,
              label: 'Faulty drain pump motor',
            ),
            if (_diagnosisRerunDone) ...[
              const SizedBox(height: KwSpacing.md),
              Text(
                'After failed drain-filter fix (re-run)',
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: KwSpacing.xs),
              KwConfidenceMeter(
                probability: _afterDrainPumpProb,
                label: 'Faulty drain pump motor (promoted)',
              ),
              const SizedBox(height: KwSpacing.xs),
              KwConfidenceMeter(
                probability: _afterDrainFilterProb,
                label: 'Blocked drain filter (ruled out)',
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCandidatesCard(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Top 3 Technician Candidates (6-Factor Score)',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            if (_candidates.isEmpty)
              const Text('Awaiting visit plan to score technicians…')
            else
              for (final cand in _candidates) ...[
                Container(
                  margin: const EdgeInsets.only(bottom: KwSpacing.sm),
                  padding: const EdgeInsets.all(KwSpacing.sm),
                  decoration: BoxDecoration(
                    color: cs.surface,
                    borderRadius: KwShapes.radiusMedium,
                    border: Border.all(
                      color: cand.rank == 1 ? cs.primary : cs.outlineVariant,
                      width: cand.rank == 1 ? 2 : 1,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: KwSpacing.xs,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            '#${cand.rank} ${cand.name}',
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (cand.rank == 1)
                            Chip(
                              backgroundColor: cs.primaryContainer,
                              label: Text(
                                'WINNER',
                                style: theme.textTheme.labelSmall?.copyWith(
                                  color: cs.onPrimaryContainer,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                        ],
                      ),
                      Text(cand.why, style: theme.textTheme.bodySmall),
                      const SizedBox(height: KwSpacing.xs),
                      KwCandidateScoreBar(
                        totalScoreOverride: cand.score,
                        breakdown: KwCandidateScoreBreakdown(
                          fixConfidence: cand.scoreBreakdown.fixConfidence,
                          partsReadiness: cand.scoreBreakdown.partsReadiness,
                          timeToVisit: cand.scoreBreakdown.timeToVisit,
                          routeCost: cand.scoreBreakdown.routeCost,
                          reliability: cand.scoreBreakdown.reliability,
                          householdFit: cand.scoreBreakdown.householdFit,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
          ],
        ),
      ),
    );
  }

  Widget _buildSettlementCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Wrap(
          spacing: KwSpacing.lg,
          runSpacing: KwSpacing.sm,
          children: [
            _StatusBadge(label: 'Quote', value: _quoteStatus),
            _StatusBadge(label: 'Payment', value: _paymentStatus),
            _StatusBadge(label: 'Closure OTP', value: _otpStatus),
          ],
        ),
      ),
    );
  }

  Widget _buildLiveFeedCard(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Live Event Feed (${_events.length})',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            for (final ev in _events.take(12))
              KwEventRow(
                type: ev.type,
                title: ev.title,
                detail: ev.detail,
                actor: ev.actor,
                at: ConsoleController.parseIsoDate(ev.at),
                liveRegion: ev == _events.first,
              ),
          ],
        ),
      ),
    );
  }
}

class _ModalityPill extends StatelessWidget {
  const _ModalityPill({required this.modality});

  final String modality;

  @override
  Widget build(BuildContext context) {
    final kw = Theme.of(context).kwColors;
    final isVideo = modality == 'video';
    final isSwitching = modality == 'switching_to_video';
    final role = isVideo
        ? kw.liveVideo
        : isSwitching
            ? kw.needsChecking
            : kw.standard;
    final icon = isVideo
        ? Icons.videocam_rounded
        : isSwitching
            ? Icons.sync_rounded
            : Icons.mic_rounded;
    final label = isVideo
        ? 'VIDEO'
        : isSwitching
            ? 'SWITCHING TO VIDEO'
            : 'VOICE';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: KwSpacing.sm, vertical: 6),
      decoration: BoxDecoration(
        color: role.container,
        borderRadius: KwShapes.radiusFull,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: role.onContainer),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: role.onContainer,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _StageTurn {
  const _StageTurn({
    required this.speaker,
    required this.text,
    required this.lang,
    required this.modality,
    required this.isFinal,
    required this.at,
  });

  final KwTranscriptSpeaker speaker;
  final String text;
  final String lang;
  final KwTranscriptModality modality;
  final bool isFinal;
  final DateTime at;
}

const List<AssignmentCandidate> _c03SampleCandidates = [
  AssignmentCandidate(
    technicianId: 'tech_ravi_fw',
    name: 'Ravi Kumar',
    rank: 1,
    score: 92,
    scoreBreakdown: ScoreBreakdown(
      fixConfidence: 29,
      partsReadiness: 25,
      timeToVisit: 18,
      routeCost: 11,
      reliability: 5,
      householdFit: 4,
    ),
    slotStart: '2026-11-21T08:30:00Z',
    slotEnd: '2026-11-21T10:30:00Z',
    outcome: 'assigned',
    chosenBy: 'agent',
    why: 'Wavecrest certified, carrying WC-DP-402 pump in van, 14 min away',
  ),
  AssignmentCandidate(
    technicianId: 'tech_anitha_fw',
    name: 'Anitha Reddy',
    rank: 2,
    score: 81,
    scoreBreakdown: ScoreBreakdown(
      fixConfidence: 26,
      partsReadiness: 19,
      timeToVisit: 15,
      routeCost: 12,
      reliability: 5,
      householdFit: 4,
    ),
    slotStart: '2026-11-21T10:30:00Z',
    slotEnd: '2026-11-21T12:30:00Z',
    outcome: 'proposed',
    chosenBy: 'agent',
    why: 'Strong front-load skill, needs centre pickup for pump',
  ),
  AssignmentCandidate(
    technicianId: 'tech_suresh_fw',
    name: 'Suresh Naik',
    rank: 3,
    score: 69,
    scoreBreakdown: ScoreBreakdown(
      fixConfidence: 20,
      partsReadiness: 16,
      timeToVisit: 13,
      routeCost: 11,
      reliability: 5,
      householdFit: 4,
    ),
    slotStart: '2026-11-21T12:00:00Z',
    slotEnd: '2026-11-21T14:00:00Z',
    outcome: 'proposed',
    chosenBy: 'agent',
    why: 'Available afternoon window in Miyapur corridor',
  ),
];
