import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'household_l10n.dart';
import 'media/kw_media_bridge.dart';

enum _CameraPermissionState { prompting, granted, denied }

/// Surface 3: Guided Video-Link Page (route `/v/<token>`).
///
/// Explains camera permission in plain language, renders a live preview
/// surface with a dynamic framing overlay driven by [LiveUiHintMessage]
/// (`show_sticker`, `show_display`, `show_drain_filter`, `hold_steady`),
/// streams 1 fps JPEG frames with a visible frame counter, provides a
/// camera-denied degraded fallback to sending a still photo, displays live
/// captions, and always shows a calm ≥48dp "Stop video (continue on voice)"
/// button.
class VideoLinkScreen extends StatefulWidget {
  const VideoLinkScreen({
    super.key,
    required this.token,
    required this.liveCallClient,
    required this.activeCentre,
    this.onStopVideoToVoice,
    this.initialCameraDenied = false,
    this.mediaBridge,
  });

  final String token;
  final LiveCallClient liveCallClient;
  final KwCentreIdentity activeCentre;
  final VoidCallback? onStopVideoToVoice;
  final bool initialCameraDenied;
  final KwMediaBridge? mediaBridge;

  @override
  State<VideoLinkScreen> createState() => _VideoLinkScreenState();
}

class _VideoLinkScreenState extends State<VideoLinkScreen> {
  StreamSubscription<LiveServerMessage>? _sub;
  Timer? _frameTimer;
  late final KwMediaBridge _media;

  late _CameraPermissionState _cameraState;
  LiveUiHintMessage _activeHint = const LiveUiHintMessage(
    kind: 'show_sticker',
    text: 'Centre the appliance model sticker inside the frame.',
  );

  int _framesSent = 0;
  int _stillPhotosSent = 0;
  String? _latestCaption;
  String _latestCaptionLang = 'en';
  bool _latestCaptionFinal = true;
  bool _stoppedToVoice = false;

  @override
  void initState() {
    super.initState();
    _media = widget.mediaBridge ?? KwMediaBridge();
    _cameraState = widget.initialCameraDenied
        ? _CameraPermissionState.denied
        : _CameraPermissionState.prompting;
    _sub = widget.liveCallClient.messages.listen(_onServerMessage);
  }

  @override
  void dispose() {
    _frameTimer?.cancel();
    _media.stopVideoPreview();
    unawaited(_sub?.cancel());
    super.dispose();
  }

  void _onServerMessage(LiveServerMessage msg) {
    if (!mounted) return;
    switch (msg) {
      case LiveUiHintMessage():
        setState(() {
          _activeHint = msg;
        });
      case LiveTranscriptMessage():
        setState(() {
          _latestCaption = msg.text;
          _latestCaptionLang = msg.lang;
          _latestCaptionFinal = msg.isFinal;
        });
      case LiveReadyMessage():
      case LiveVideoLinkMessage():
      case LiveModalityMessage():
      case LiveEventMessage():
      case LiveGoAwayMessage():
      case LiveEndedMessage():
      case LiveErrorMessage():
      case LiveAudioChunkMessage():
      case LiveUnknownMessage():
        break;
    }
  }

  Future<void> _grantCamera() async {
    setState(() {
      _cameraState = _CameraPermissionState.granted;
      _stoppedToVoice = false;
    });
    try {
      final started = await _media.startVideoPreview();
      if (!started) {
        if (mounted) _denyCamera();
        return;
      }
    } catch (_) {
      if (mounted) _denyCamera();
      return;
    }
    if (!mounted) return;
    widget.liveCallClient.sendClientState(modality: 'video', muted: false);
    _startFrameStreaming();
  }

  void _denyCamera() {
    _frameTimer?.cancel();
    _media.stopVideoPreview();
    setState(() {
      _cameraState = _CameraPermissionState.denied;
    });
  }

  void _startFrameStreaming() {
    _frameTimer?.cancel();
    // Wait briefly for the <video> element to paint its first frame, then send at <= 1 fps.
    Future<void>.delayed(const Duration(milliseconds: 350), () {
      if (!mounted || _cameraState != _CameraPermissionState.granted) return;
      _sendSingleVideoFrame();
    });
    _frameTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted || _cameraState != _CameraPermissionState.granted) return;
      _sendSingleVideoFrame();
    });
  }

  void _sendSingleVideoFrame() {
    final jpeg = _media.captureVideoFrameJpeg(maxLongEdge: 640);
    if (jpeg == null || jpeg.isEmpty) return;
    final ts = DateTime.now().millisecondsSinceEpoch;
    widget.liveCallClient.sendVideoFrame(jpeg, ts);
    if (!mounted) return;
    setState(() {
      _framesSent += 1;
    });
  }

  void _sendStillPhoto(String caption) {
    final jpeg = _media.captureVideoFrameJpeg(maxLongEdge: 640, quality: 0.85);
    if (jpeg != null && jpeg.isNotEmpty) {
      widget.liveCallClient.sendImage(jpeg, caption: caption);
    }
    setState(() {
      _stillPhotosSent += 1;
    });
  }

  void _stopVideoAndContinueVoice() {
    _frameTimer?.cancel();
    _media.stopVideoPreview();
    widget.liveCallClient.sendClientState(modality: 'voice', muted: false);
    setState(() {
      _stoppedToVoice = true;
    });
    widget.onStopVideoToVoice?.call();
  }

  (String title, IconData icon) _hintMeta(String kind) {
    return switch (kind) {
      'show_sticker' => ('Frame model sticker', Icons.qr_code_scanner_rounded),
      'show_display' => ('Frame display panel', Icons.monitor_rounded),
      'show_drain_filter' => (
          'Frame lower drain filter',
          Icons.water_drop_outlined
        ),
      'hold_steady' => ('Hold phone steady', Icons.center_focus_strong_rounded),
      _ => ('Guided view', Icons.crop_free_rounded),
    };
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
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(context, cs, kw),
              const SizedBox(height: KwSpacing.sm),
              if (_cameraState == _CameraPermissionState.prompting)
                _buildPermissionCard(context, hStrings, cs),
              if (_cameraState == _CameraPermissionState.denied)
                _buildCameraDeniedFallback(context, hStrings, kw),
              if (_cameraState == _CameraPermissionState.granted)
                _buildLiveCameraSurface(context, cs, kw),
              if (_latestCaption != null) ...[
                const SizedBox(height: KwSpacing.sm),
                KwTranscriptBubble(
                  speaker: KwTranscriptSpeaker.agent,
                  text: _latestCaption!,
                  languageCode: _latestCaptionLang,
                  modality: KwTranscriptModality.video,
                  isFinal: _latestCaptionFinal,
                  speakerNameOverride: widget.activeCentre.name,
                  liveRegion: true,
                ),
              ],
              if (_stoppedToVoice) ...[
                const SizedBox(height: KwSpacing.sm),
                Container(
                  padding: const EdgeInsets.all(KwSpacing.sm),
                  decoration: BoxDecoration(
                    color: kw.verified.container,
                    borderRadius: KwShapes.radiusMedium,
                  ),
                  child: Text(
                    'Video stopped. Your voice call with ${widget.activeCentre.name} continues uninterrupted.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: kw.verified.onContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: KwSpacing.md),
              Semantics(
                button: true,
                label: hStrings.stopVideoLabel,
                child: SizedBox(
                  height: 52,
                  child: OutlinedButton.icon(
                    onPressed: _stopVideoAndContinueVoice,
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(
                        double.infinity,
                        KwSpacing.minTouchTarget,
                      ),
                      side: BorderSide(color: cs.primary, width: 1.5),
                    ),
                    icon: const Icon(Icons.videocam_off_rounded),
                    label: Text(
                      hStrings.stopVideoLabel,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    ColorScheme cs,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.sm),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: kw.liveVideo.container,
                borderRadius: KwShapes.radiusSmall,
              ),
              child: Icon(Icons.videocam_rounded, color: kw.liveVideo.onContainer),
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.activeCentre.name,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    'Guided video link · /v/${widget.token}',
                    style: KwTheme.monoStyle(
                      context,
                      fontSize: 12,
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: KwSpacing.xs,
                vertical: 4,
              ),
              decoration: BoxDecoration(
                color: kw.liveVideo.container,
                borderRadius: KwShapes.radiusFull,
              ),
              child: Text(
                '1 fps · $_framesSent frames',
                style: KwTheme.monoStyle(
                  context,
                  fontSize: 11,
                  color: kw.liveVideo.onContainer,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPermissionCard(
    BuildContext context,
    HouseholdStrings hStrings,
    ColorScheme cs,
  ) {
    final theme = Theme.of(context);
    return Card(
      color: cs.secondaryContainer.withValues(alpha: 0.45),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.camera_alt_rounded, color: cs.onSecondaryContainer),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    hStrings.cameraPermissionTitle,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            Text(
              hStrings.cameraPermissionBody,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: KwSpacing.md),
            Wrap(
              spacing: KwSpacing.sm,
              runSpacing: KwSpacing.xs,
              children: [
                FilledButton.icon(
                  onPressed: _grantCamera,
                  icon: const Icon(Icons.videocam_rounded),
                  label: Text(hStrings.allowCameraLabel),
                ),
                OutlinedButton.icon(
                  onPressed: _denyCamera,
                  icon: const Icon(Icons.no_photography_outlined),
                  label: Text(hStrings.denyCameraLabel),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraDeniedFallback(
    BuildContext context,
    HouseholdStrings hStrings,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(KwSpacing.md),
      decoration: BoxDecoration(
        color: kw.needsChecking.container,
        borderRadius: KwShapes.radiusLarge,
        border: Border.all(color: kw.needsChecking.accent, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.photo_camera_back_rounded,
                  color: kw.needsChecking.onContainer),
              const SizedBox(width: KwSpacing.xs),
              Expanded(
                child: Text(
                  hStrings.cameraUnavailableTitle,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: kw.needsChecking.onContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.xs),
          Text(
            'Camera permission was denied or unavailable on this browser. You can still send a clear still photo of the model sticker or error display.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: kw.needsChecking.onContainer,
            ),
          ),
          const SizedBox(height: KwSpacing.sm),
          Wrap(
            spacing: KwSpacing.xs,
            runSpacing: KwSpacing.xs,
            children: [
              FilledButton.icon(
                onPressed: () => _sendStillPhoto('model_sticker'),
                icon: const Icon(Icons.add_a_photo_rounded),
                label: Text(hStrings.sendStillPhotoLabel),
              ),
              OutlinedButton(
                onPressed: _grantCamera,
                child: Text(hStrings.allowCameraLabel),
              ),
            ],
          ),
          if (_stillPhotosSent > 0) ...[
            const SizedBox(height: KwSpacing.xs),
            Text(
              'Still photo sent ($_stillPhotosSent) — the service centre can read it now.',
              style: theme.textTheme.labelMedium?.copyWith(
                color: kw.needsChecking.onContainer,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLiveCameraSurface(
    BuildContext context,
    ColorScheme cs,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    final (hintTitle, hintIcon) = _hintMeta(_activeHint.kind);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: 320,
          decoration: BoxDecoration(
            color: const Color(0xFF101726),
            borderRadius: KwShapes.radiusLarge,
            border: Border.all(color: kw.liveVideo.accent, width: 2),
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Real MediaStream <video> preview bound via HtmlElementView on web.
              _media.buildVideoPreview(),
              // Dynamic ui_hint framing guide overlay on top of live video.
              IgnorePointer(
                child: CustomPaint(
                  painter: _FramingGuidePainter(
                    kind: _activeHint.kind,
                    accentColor: kw.liveVideo.accent,
                  ),
                ),
              ),
              Positioned(
                top: KwSpacing.sm,
                left: KwSpacing.sm,
                right: KwSpacing.sm,
                child: Wrap(
                  spacing: KwSpacing.xs,
                  runSpacing: KwSpacing.xs,
                  alignment: WrapAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: KwSpacing.xs,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: kw.liveVideo.container,
                        borderRadius: KwShapes.radiusFull,
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(hintIcon,
                              size: 15, color: kw.liveVideo.onContainer),
                          const SizedBox(width: 6),
                          Text(
                            hintTitle,
                            style: theme.textTheme.labelMedium?.copyWith(
                              color: kw.liveVideo.onContainer,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: KwSpacing.xs,
                        vertical: 4,
                      ),
                      decoration: const BoxDecoration(
                        color: Colors.black54,
                        borderRadius: KwShapes.radiusFull,
                      ),
                      child: Text(
                        'JPEG 1 fps · ≤640px · #$_framesSent',
                        style: KwTheme.monoStyle(
                          context,
                          fontSize: 11,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Positioned(
                bottom: KwSpacing.sm,
                left: KwSpacing.sm,
                right: KwSpacing.sm,
                child: Semantics(
                  liveRegion: true,
                  child: Container(
                    padding: const EdgeInsets.all(KwSpacing.sm),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.72),
                      borderRadius: KwShapes.radiusMedium,
                    ),
                    child: Text(
                      _activeHint.text.isNotEmpty
                          ? _activeHint.text
                          : hintTitle,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: KwSpacing.xs),
        Row(
          children: [
            Expanded(
              child: Text(
                'Active guide: ${_activeHint.kind}',
                style: KwTheme.monoStyle(
                  context,
                  fontSize: 12,
                  color: cs.onSurfaceVariant,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () => _sendStillPhoto(_activeHint.kind),
              icon: const Icon(Icons.camera_rounded, size: 18),
              label: const Text('Capture high-res still'),
            ),
          ],
        ),
      ],
    );
  }
}

class _FramingGuidePainter extends CustomPainter {
  const _FramingGuidePainter({
    required this.kind,
    required this.accentColor,
  });

  final String kind;
  final Color accentColor;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = switch (kind) {
      'show_sticker' => Rect.fromCenter(
          center: Offset(size.width / 2, size.height / 2),
          width: size.width * 0.68,
          height: size.height * 0.36,
        ),
      'show_display' => Rect.fromCenter(
          center: Offset(size.width / 2, size.height / 2),
          width: size.width * 0.56,
          height: size.height * 0.42,
        ),
      'show_drain_filter' => Rect.fromCenter(
          center: Offset(size.width / 2, size.height * 0.58),
          width: size.width * 0.44,
          height: size.width * 0.44,
        ),
      _ => Rect.fromCenter(
          center: Offset(size.width / 2, size.height / 2),
          width: size.width * 0.62,
          height: size.height * 0.5,
        ),
    };

    final guidePaint = Paint()
      ..color = accentColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    if (kind == 'show_drain_filter') {
      canvas.drawOval(rect, guidePaint);
    } else {
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(16)),
        guidePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FramingGuidePainter oldDelegate) {
    return oldDelegate.kind != kind || oldDelegate.accentColor != accentColor;
  }
}
