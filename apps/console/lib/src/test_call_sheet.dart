import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Opens the Test-Call modal sheet for placing a live WebSocket call to
/// the Keepwell Live Call bridge directly from the Centre Console.
Future<void> showTestCallSheet(
  BuildContext context, {
  required ConsoleController controller,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (sheetContext) {
      return SizedBox(
        height: MediaQuery.sizeOf(sheetContext).height * 0.85,
        child: TestCallSheet(controller: controller),
      );
    },
  );
}

class TestCallSheet extends StatefulWidget {
  const TestCallSheet({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<TestCallSheet> createState() => _TestCallSheetState();
}

class _TestCallSheetState extends State<TestCallSheet> {
  late final LiveCallClient _liveClient;
  StreamSubscription<LiveServerMessage>? _sub;
  late String _centreKey;
  final TextEditingController _callerController =
      TextEditingController(text: '+919848011223');
  String _languageHint = 'en';

  bool _connected = false;
  bool _connecting = false;
  bool _muted = false;
  bool _speakerOn = true;
  bool _videoActive = false;
  double _audioLevel = 0.25;
  String _statusText = 'Ready to connect';
  String? _recordingNotice;

  final List<_CaptionItem> _captions = [];
  final List<LiveEvent> _events = [];

  @override
  void initState() {
    super.initState();
    _centreKey = widget.controller.activeCentreKey;
    _liveClient = widget.controller.createLiveCallClient();
    _sub = _liveClient.messages.listen(_onMessage);
  }

  @override
  void dispose() {
    _sub?.cancel();
    unawaited(_liveClient.dispose());
    _callerController.dispose();
    super.dispose();
  }

  void _onMessage(LiveServerMessage msg) {
    if (!mounted) return;
    setState(() {
      switch (msg) {
        case LiveReadyMessage():
          _connected = true;
          _connecting = false;
          _statusText = 'Connected · ${msg.centreName}';
          _recordingNotice = msg.recordingNotice;
          _audioLevel = 0.6;
        case LiveTranscriptMessage():
          _captions.add(
            _CaptionItem(
              speaker: msg.speaker == 'household'
                  ? KwTranscriptSpeaker.household
                  : KwTranscriptSpeaker.agent,
              text: msg.text,
              lang: msg.lang,
              modality: _videoActive
                  ? KwTranscriptModality.video
                  : KwTranscriptModality.voice,
              isFinal: msg.isFinal,
              at: DateTime.now(),
            ),
          );
          _audioLevel = msg.isFinal ? 0.35 : 0.85;
        case LiveModalityMessage():
          _videoActive = msg.value == 'video';
          _statusText = 'Modality: ${msg.value}';
        case LiveEventMessage():
          _events.insert(0, msg.event);
        case LiveUiHintMessage():
          _statusText = 'Hint (${msg.kind}): ${msg.text}';
        case LiveEndedMessage():
          _connected = false;
          _connecting = false;
          _audioLevel = 0.0;
          _statusText = 'Call ended (${msg.reason})';
        case LiveErrorMessage():
          _connecting = false;
          _statusText = 'Notice: ${msg.message}';
        case LiveAudioChunkMessage():
          _audioLevel = 0.72;
        case LiveVideoLinkMessage():
          _statusText = 'Video link issued';
        case LiveGoAwayMessage():
          _statusText = 'Reconnecting (${msg.seconds}s)…';
        case LiveUnknownMessage():
          break;
      }
    });
  }

  Future<void> _startCall() async {
    setState(() {
      _connecting = true;
      _statusText = 'Dialing ${widget.controller.config.liveWsUrl}…';
      _captions.clear();
      _events.clear();
    });
    try {
      await _liveClient.start(
        centreKey: _centreKey,
        callerNumber: _callerController.text.trim(),
        languageHint: _languageHint,
        authToken: widget.controller.session?.idToken,
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _connecting = false;
          _connected = false;
          _statusText = 'Could not connect to Live WS: $e';
        });
      }
    }
  }

  Future<void> _endCall() async {
    await _liveClient.end();
    if (mounted) {
      setState(() {
        _connected = false;
        _audioLevel = 0.0;
        _statusText = 'Call ended';
      });
    }
  }

  void _toggleMute() {
    setState(() => _muted = !_muted);
    _liveClient.sendClientState(
      modality: _videoActive ? 'video' : 'voice',
      muted: _muted,
    );
  }

  void _toggleVideo() {
    setState(() => _videoActive = !_videoActive);
    _liveClient.sendClientState(
      modality: _videoActive ? 'video' : 'voice',
      muted: _muted,
    );
  }

  void _sendSampleSticker() {
    final sample = base64Encode(utf8.encode('keepwell-demo-model-sticker'));
    _liveClient.sendImage(sample, caption: 'Model sticker: WC-FL700-IN');
    setState(() {
      _statusText = 'Sent model sticker frame to agent';
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        KwSpacing.lg,
        KwSpacing.xs,
        KwSpacing.lg,
        KwSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.phone_in_talk_rounded, color: cs.primary),
              const SizedBox(width: KwSpacing.xs),
              Expanded(
                child: Text(
                  'Live Test Call',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Close',
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close_rounded),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.sm),
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SizedBox(
                width: 210,
                child: DropdownButtonFormField<String>(
                  value: _centreKey,
                  decoration: const InputDecoration(
                    labelText: 'Service Centre',
                    isDense: true,
                  ),
                  items: [
                    for (final c in KwAuthHelper.demoCentres)
                      DropdownMenuItem(
                        value: c.key,
                        child: Text('${c.key} · ${c.locality}'),
                      ),
                  ],
                  onChanged: _connected
                      ? null
                      : (v) {
                          if (v != null) setState(() => _centreKey = v);
                        },
                ),
              ),
              SizedBox(
                width: 190,
                child: TextField(
                  controller: _callerController,
                  enabled: !_connected,
                  decoration: const InputDecoration(
                    labelText: 'Caller Number',
                    isDense: true,
                  ),
                ),
              ),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'en', label: Text('EN')),
                  ButtonSegment(value: 'hi', label: Text('HI')),
                  ButtonSegment(value: 'te', label: Text('TE')),
                ],
                selected: {_languageHint},
                onSelectionChanged: _connected
                    ? null
                    : (s) => setState(() => _languageHint = s.first),
              ),
              if (!_connected)
                FilledButton.icon(
                  onPressed: _connecting ? null : _startCall,
                  icon: const Icon(Icons.call_rounded),
                  label: Text(_connecting ? 'Connecting…' : 'Start Call'),
                )
              else
                OutlinedButton.icon(
                  onPressed: _sendSampleSticker,
                  icon: const Icon(Icons.photo_camera_rounded),
                  label: const Text('Send Model Sticker'),
                ),
            ],
          ),
          if (_recordingNotice != null && _recordingNotice!.isNotEmpty) ...[
            const SizedBox(height: KwSpacing.xs),
            Container(
              padding: const EdgeInsets.all(KwSpacing.xs),
              decoration: BoxDecoration(
                color: cs.secondaryContainer.withValues(alpha: 0.45),
                borderRadius: KwShapes.radiusSmall,
              ),
              child: Text(
                _recordingNotice!,
                style: theme.textTheme.bodySmall,
              ),
            ),
          ],
          const SizedBox(height: KwSpacing.sm),
          Expanded(
            child: _captions.isEmpty
                ? KwEmptyState(
                    icon: Icons.graphic_eq_rounded,
                    title: _connected
                        ? 'Listening for live captions…'
                        : 'Place a live test call',
                    body:
                        'Connects to ${widget.controller.config.liveWsUrl} for real-time voice/video triage.',
                  )
                : ListView.separated(
                    itemCount: _captions.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: KwSpacing.xs),
                    itemBuilder: (context, index) {
                      final cap = _captions[index];
                      return KwTranscriptBubble(
                        speaker: cap.speaker,
                        text: cap.text,
                        languageCode: cap.lang,
                        modality: cap.modality,
                        isFinal: cap.isFinal,
                        timestamp: cap.at,
                        liveRegion: index == _captions.length - 1,
                      );
                    },
                  ),
          ),
          if (_events.isNotEmpty) ...[
            const SizedBox(height: KwSpacing.xs),
            SizedBox(
              height: 40,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _events.length,
                separatorBuilder: (_, __) =>
                    const SizedBox(width: KwSpacing.xs),
                itemBuilder: (context, index) {
                  final ev = _events[index];
                  return Chip(
                    label: Text('${ev.type}: ${ev.title}'),
                  );
                },
              ),
            ),
          ],
          const SizedBox(height: KwSpacing.sm),
          KwWaveformControls(
            isMuted: _muted,
            isSpeakerOn: _speakerOn,
            isVideoActive: _videoActive,
            audioLevel: _connected ? _audioLevel : 0.0,
            statusText: _statusText,
            onToggleMute: _connected ? _toggleMute : null,
            onToggleSpeaker: () => setState(() => _speakerOn = !_speakerOn),
            onToggleVideo: _connected ? _toggleVideo : null,
            onEndCall: _connected ? _endCall : () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}

class _CaptionItem {
  const _CaptionItem({
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
