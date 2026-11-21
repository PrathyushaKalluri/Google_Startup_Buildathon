import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'household_l10n.dart';
import 'media/kw_media_bridge.dart';

class _CaptionEntry {
  const _CaptionEntry({
    required this.speaker,
    required this.text,
    required this.lang,
    required this.isFinal,
    required this.at,
  });

  final KwTranscriptSpeaker speaker;
  final String text;
  final String lang;
  final bool isFinal;
  final DateTime at;
}

/// Surface 2: Google Meet-inspired Voice Call Dialer.
///
/// Connects to [LiveCallClient] (`ws://localhost:8082/v1/live/call`), displays
/// the plain-language microphone banner, verbatim [LiveReadyMessage.recordingNotice],
/// live bilingual captions (`KwTranscriptBubble`), `KwWaveformControls`,
/// a prominent "Switching to video..." transition card on [LiveVideoLinkMessage],
/// and graceful reconnect state on [LiveGoAwayMessage] or stream errors.
class CallDialerScreen extends StatefulWidget {
  const CallDialerScreen({
    super.key,
    required this.liveCallClient,
    required this.activeCentre,
    this.callerNumber = '+919848000001',
    this.languageHint = 'en',
    this.autoConnect = false,
    this.onSwitchToVideoToken,
    this.mediaBridge,
  });

  final LiveCallClient liveCallClient;
  final KwCentreIdentity activeCentre;
  final String callerNumber;
  final String languageHint;
  final bool autoConnect;
  final ValueChanged<String>? onSwitchToVideoToken;
  final KwMediaBridge? mediaBridge;

  @override
  State<CallDialerScreen> createState() => _CallDialerScreenState();
}

class _CallDialerScreenState extends State<CallDialerScreen> {
  StreamSubscription<LiveServerMessage>? _sub;
  late final KwMediaBridge _media;

  bool _micAllowed = false;
  bool _micBannerDismissed = false;
  bool _connecting = false;
  bool _inCall = false;
  bool _isMuted = false;
  bool _isSpeakerOn = true;
  bool _isReconnecting = false;
  double _audioLevel = 0.0;

  String? _centreName;
  String? _recordingNotice;
  LiveVideoLinkMessage? _videoLink;
  LiveEndedMessage? _endedMessage;
  String? _errorNotice;

  final List<_CaptionEntry> _captions = <_CaptionEntry>[];

  @override
  void initState() {
    super.initState();
    _media = widget.mediaBridge ?? KwMediaBridge();
    _centreName = widget.activeCentre.name;
    _sub = widget.liveCallClient.messages.listen(_onServerMessage);
    if (widget.autoConnect) {
      _micAllowed = true;
      unawaited(_startCall());
    }
  }

  @override
  void didUpdateWidget(covariant CallDialerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.activeCentre.key != widget.activeCentre.key && !_inCall) {
      _centreName = widget.activeCentre.name;
    }
  }

  @override
  void dispose() {
    _media.stopAudioCapture();
    _media.flushPlayback();
    unawaited(_sub?.cancel());
    super.dispose();
  }

  Future<void> _startCall() async {
    setState(() {
      _connecting = true;
      _errorNotice = null;
      _endedMessage = null;
      _isReconnecting = false;
    });
    try {
      await widget.liveCallClient.start(
        centreKey: widget.activeCentre.key,
        callerNumber: widget.callerNumber,
        languageHint: widget.languageHint,
      );
      try {
        _media.setMuted(_isMuted);
        _media.setSpeaker(_isSpeakerOn);
        await _media.startAudioCapture(
          onChunk: (pcm16Chunk) {
            if (_inCall && !_isMuted) {
              widget.liveCallClient.sendAudioPcm16(pcm16Chunk);
            }
          },
          onRms: (rms) {
            if (!mounted) return;
            if ((rms - _audioLevel).abs() > 0.06) {
              setState(() => _audioLevel = rms.clamp(0.05, 1.0));
            }
          },
          onBargeIn: () {
            _media.flushPlayback();
          },
        );
      } catch (_) {
        // Keep WebSocket call active even if browser mic capture is denied.
      }
      if (!mounted) return;
      setState(() {
        _connecting = false;
        _inCall = true;
        _audioLevel = 0.35;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _connecting = false;
        _inCall = false;
        _errorNotice =
            'Could not connect voice call (${widget.liveCallClient.config.liveWsUrl}). Tap Reconnect to try again.';
      });
    }
  }

  void _onServerMessage(LiveServerMessage msg) {
    if (!mounted) return;
    switch (msg) {
      case LiveReadyMessage():
        setState(() {
          _inCall = true;
          _connecting = false;
          _isReconnecting = false;
          _errorNotice = null;
          if (msg.centreName.isNotEmpty) {
            _centreName = msg.centreName;
          }
          _recordingNotice = msg.recordingNotice;
          _audioLevel = 0.45;
        });
      case LiveTranscriptMessage():
        if (msg.speaker.toLowerCase() == 'household' ||
            msg.speaker.toLowerCase() == 'caller') {
          _media.flushPlayback();
        }
        setState(() {
          final speaker = msg.speaker.toLowerCase() == 'household' ||
                  msg.speaker.toLowerCase() == 'caller'
              ? KwTranscriptSpeaker.household
              : KwTranscriptSpeaker.agent;
          final entry = _CaptionEntry(
            speaker: speaker,
            text: msg.text,
            lang: msg.lang,
            isFinal: msg.isFinal,
            at: DateTime.now(),
          );
          if (_captions.isNotEmpty &&
              !_captions.last.isFinal &&
              _captions.last.speaker == speaker) {
            _captions[_captions.length - 1] = entry;
          } else {
            _captions.add(entry);
          }
          _audioLevel = msg.isFinal ? 0.3 : 0.72;
        });
      case LiveVideoLinkMessage():
        setState(() {
          _videoLink = msg;
        });
      case LiveGoAwayMessage():
        setState(() {
          _isReconnecting = true;
          _errorNotice =
              'Session refreshing in ${msg.seconds}s — reconnecting seamlessly…';
        });
      case LiveErrorMessage():
        setState(() {
          _isReconnecting = false;
          _errorNotice = '${msg.code}: ${msg.message}';
        });
      case LiveEndedMessage():
        _media.stopAudioCapture();
        _media.flushPlayback();
        setState(() {
          _inCall = false;
          _connecting = false;
          _isReconnecting = false;
          _audioLevel = 0.0;
          _endedMessage = msg;
        });
      case LiveAudioChunkMessage():
        _media.playPcm24k(msg.pcm16Bytes);
        setState(() {
          _audioLevel = 0.78;
        });
      case LiveEventMessage():
        final t = msg.event.type.toLowerCase();
        if (t.contains('interrupt') || t.contains('barge')) {
          _media.flushPlayback();
        }
      case LiveUnknownMessage():
        final t = msg.type.toLowerCase();
        if (t == 'interrupted' || t == 'barge_in' || msg.raw['interrupted'] == true) {
          _media.flushPlayback();
        }
      case LiveModalityMessage():
      case LiveUiHintMessage():
        break;
    }
  }

  String _extractVideoToken(String url) {
    final uri = Uri.tryParse(url);
    final segments = uri?.pathSegments ?? const <String>[];
    final vIdx = segments.indexOf('v');
    if (vIdx != -1 && vIdx + 1 < segments.length) {
      return segments[vIdx + 1];
    }
    return segments.isNotEmpty ? segments.last : 'demo-video-token';
  }

  void _toggleMute() {
    setState(() {
      _isMuted = !_isMuted;
    });
    _media.setMuted(_isMuted);
    widget.liveCallClient.sendClientState(
      modality: 'voice',
      muted: _isMuted,
    );
  }

  void _toggleSpeaker() {
    setState(() {
      _isSpeakerOn = !_isSpeakerOn;
    });
    _media.setSpeaker(_isSpeakerOn);
  }

  void _handleSwitchToVideoTap() {
    final token = _videoLink != null
        ? _extractVideoToken(_videoLink!.url)
        : 'demo-video-token';
    widget.liveCallClient.sendClientState(
      modality: 'video',
      muted: _isMuted,
    );
    widget.onSwitchToVideoToken?.call(token);
  }

  Future<void> _endCall() async {
    _media.stopAudioCapture();
    _media.flushPlayback();
    await widget.liveCallClient.end();
    if (!mounted) return;
    setState(() {
      _inCall = false;
      _audioLevel = 0.0;
      _endedMessage = const LiveEndedMessage(reason: 'ended_by_caller');
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final hStrings = HouseholdStrings.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680),
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: ListView(
                  children: [
                    _buildCallHeader(context, cs, kw),
                    const SizedBox(height: KwSpacing.sm),
                    if (!_micAllowed && !_micBannerDismissed)
                      _buildMicPermissionBanner(context, hStrings),
                    if (_recordingNotice != null &&
                        _recordingNotice!.isNotEmpty) ...[
                      const SizedBox(height: KwSpacing.sm),
                      _buildRecordingNoticeCard(context, hStrings, kw),
                    ],
                    if (_videoLink != null) ...[
                      const SizedBox(height: KwSpacing.sm),
                      _buildVideoTransitionCard(context, hStrings, kw),
                    ],
                    if (_errorNotice != null) ...[
                      const SizedBox(height: KwSpacing.sm),
                      _buildDegradedBanner(context, hStrings, kw),
                    ],
                    if (_endedMessage != null) ...[
                      const SizedBox(height: KwSpacing.sm),
                      _buildEndedCard(context, kw),
                    ],
                    const SizedBox(height: KwSpacing.sm),
                    Card(
                      child: _captions.isEmpty
                          ? Padding(
                              padding: const EdgeInsets.all(KwSpacing.md),
                              child: KwEmptyState(
                                icon: Icons.subtitles_outlined,
                                title: _inCall
                                    ? 'Live bilingual captions ready'
                                    : hStrings.startCallLabel,
                                body: _inCall
                                    ? 'Speak in English, Hindi, or Telugu. Captions will appear here in real time.'
                                    : 'Connect directly to ${_centreName ?? widget.activeCentre.name} with zero sign-in.',
                                action: !_inCall
                                    ? FilledButton.icon(
                                        onPressed:
                                            _connecting ? null : _startCall,
                                        icon: const Icon(Icons.call_rounded),
                                        label: Text(
                                          _connecting
                                              ? 'Connecting…'
                                              : hStrings.startCallLabel,
                                        ),
                                      )
                                    : null,
                              ),
                            )
                          : ListView.separated(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              padding: const EdgeInsets.all(KwSpacing.md),
                              itemCount: _captions.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: KwSpacing.xs),
                              itemBuilder: (context, index) {
                                final item = _captions[index];
                                return KwTranscriptBubble(
                                  speaker: item.speaker,
                                  text: item.text,
                                  languageCode: item.lang,
                                  modality: KwTranscriptModality.voice,
                                  isFinal: item.isFinal,
                                  timestamp: item.at,
                                  speakerNameOverride:
                                      item.speaker == KwTranscriptSpeaker.agent
                                          ? _centreName
                                          : null,
                                  liveRegion: index == _captions.length - 1,
                                );
                              },
                            ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: KwSpacing.sm),
              KwWaveformControls(
                isMuted: _isMuted,
                isSpeakerOn: _isSpeakerOn,
                isVideoActive: _videoLink != null,
                audioLevel: _inCall ? _audioLevel : 0.0,
                statusText: _isReconnecting
                    ? hStrings.reconnectingLabel
                    : _inCall
                        ? 'Connected · ${_centreName ?? widget.activeCentre.name}'
                        : 'Ready to call',
                onToggleMute: _toggleMute,
                onToggleSpeaker: _toggleSpeaker,
                onToggleVideo: _handleSwitchToVideoTap,
                onEndCall: _inCall ? _endCall : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCallHeader(
    BuildContext context,
    ColorScheme cs,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Card(
      color: cs.primaryContainer.withValues(alpha: 0.45),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: cs.primary,
              foregroundColor: cs.onPrimary,
              child: const Icon(Icons.support_agent_rounded),
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _centreName ?? widget.activeCentre.name,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '${widget.activeCentre.locality} · ${widget.activeCentre.brandsSummary}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: KwSpacing.sm,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: _inCall
                    ? kw.verified.container
                    : cs.surfaceContainerHighest,
                borderRadius: KwShapes.radiusFull,
              ),
              child: Text(
                _inCall ? 'LIVE' : 'STANDBY',
                style: KwTheme.monoStyle(
                  context,
                  fontSize: 12,
                  color: _inCall
                      ? kw.verified.onContainer
                      : cs.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMicPermissionBanner(
    BuildContext context,
    HouseholdStrings hStrings,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Card(
      color: cs.secondaryContainer.withValues(alpha: 0.55),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.mic_rounded, color: cs.onSecondaryContainer),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    hStrings.micPermissionTitle,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xxs),
            Text(
              hStrings.micPermissionBody,
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              children: [
                FilledButton.icon(
                  onPressed: () {
                    setState(() {
                      _micAllowed = true;
                    });
                    if (!_inCall && !_connecting) {
                      unawaited(_startCall());
                    }
                  },
                  icon: const Icon(Icons.check_rounded, size: 18),
                  label: Text(hStrings.allowMicLabel),
                ),
                TextButton(
                  onPressed: () {
                    setState(() {
                      _micBannerDismissed = true;
                    });
                  },
                  child: const Text('Not now'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecordingNoticeCard(
    BuildContext context,
    HouseholdStrings hStrings,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Semantics(
      liveRegion: true,
      label: '${hStrings.recordingNoticeLabel}: ${_recordingNotice!}',
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.sm),
        decoration: BoxDecoration(
          color: kw.standard.container,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(color: kw.standard.accent, width: 1.5),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.record_voice_over_rounded,
              color: kw.standard.onContainer,
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    hStrings.recordingNoticeLabel,
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: kw.standard.onContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _recordingNotice!,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: kw.standard.onContainer,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoTransitionCard(
    BuildContext context,
    HouseholdStrings hStrings,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    final token = _extractVideoToken(_videoLink!.url);
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.md),
        decoration: BoxDecoration(
          color: kw.liveVideo.container,
          borderRadius: KwShapes.radiusLarge,
          border: Border.all(color: kw.liveVideo.accent, width: 2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.videocam_rounded, color: kw.liveVideo.onContainer),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    hStrings.switchingToVideoTitle,
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: kw.liveVideo.onContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xxs),
            Text(
              'A short guided video check is ready for your appliance. Tap below to open /v/$token.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: kw.liveVideo.onContainer,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            FilledButton.icon(
              onPressed: () => widget.onSwitchToVideoToken?.call(token),
              icon: const Icon(Icons.videocam_rounded),
              label: Text(hStrings.openVideoNowLabel),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDegradedBanner(
    BuildContext context,
    HouseholdStrings hStrings,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(KwSpacing.sm),
      decoration: BoxDecoration(
        color: kw.needsChecking.container,
        borderRadius: KwShapes.radiusMedium,
        border: Border.all(color: kw.needsChecking.accent),
      ),
      child: Row(
        children: [
          Icon(
            _isReconnecting
                ? Icons.sync_rounded
                : Icons.wifi_tethering_error_rounded,
            color: kw.needsChecking.onContainer,
          ),
          const SizedBox(width: KwSpacing.sm),
          Expanded(
            child: Text(
              _errorNotice!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: kw.needsChecking.onContainer,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: KwSpacing.xs),
          TextButton(
            onPressed: _connecting ? null : _startCall,
            child: Text(hStrings.reconnectNowLabel),
          ),
        ],
      ),
    );
  }

  Widget _buildEndedCard(BuildContext context, KwSemanticColors kw) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(KwSpacing.sm),
      decoration: BoxDecoration(
        color: kw.verified.container,
        borderRadius: KwShapes.radiusMedium,
      ),
      child: Row(
        children: [
          Icon(Icons.check_circle_outline_rounded,
              color: kw.verified.onContainer),
          const SizedBox(width: KwSpacing.sm),
          Expanded(
            child: Text(
              _endedMessage!.ticketId != null
                  ? 'Call completed · Ticket ${_endedMessage!.ticketId}'
                  : 'Call ended (${_endedMessage!.reason}).',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: kw.verified.onContainer,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
