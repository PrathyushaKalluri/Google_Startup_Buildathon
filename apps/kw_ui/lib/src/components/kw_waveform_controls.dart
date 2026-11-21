import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Google Meet-style live call control bar with mute, speaker, video switch,
/// end call, and an animated audio level meter respecting reduce-motion.
class KwWaveformControls extends StatelessWidget {
  const KwWaveformControls({
    super.key,
    required this.isMuted,
    required this.isSpeakerOn,
    required this.isVideoActive,
    required this.audioLevel,
    this.onToggleMute,
    this.onToggleSpeaker,
    this.onToggleVideo,
    this.onEndCall,
    this.statusText,
  });

  final bool isMuted;
  final bool isSpeakerOn;
  final bool isVideoActive;

  /// Normalized audio level from `0.0` to `1.0`.
  final double audioLevel;
  final VoidCallback? onToggleMute;
  final VoidCallback? onToggleSpeaker;
  final VoidCallback? onToggleVideo;
  final VoidCallback? onEndCall;
  final String? statusText;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final clampedLevel = isMuted ? 0.0 : audioLevel.clamp(0.0, 1.0);
    const barMultipliers = [0.4, 0.75, 1.0, 0.85, 0.55, 0.9, 0.45];
    final reduceMotion = KwMotion.shouldReduceMotion(context);

    return Container(
      padding: const EdgeInsets.all(KwSpacing.md),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHigh,
        borderRadius: KwShapes.radiusExtraLarge,
        border: Border.all(
          color: isVideoActive ? kw.liveVideo.accent : cs.outlineVariant,
          width: isVideoActive ? 1.5 : 1.0,
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Semantics(
                label: isMuted
                    ? strings.callMute
                    : 'Audio level ${(clampedLevel * 100).round()}%',
                child: SizedBox(
                  height: 28,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      for (final m in barMultipliers)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 2),
                          child: AnimatedContainer(
                            duration: reduceMotion
                                ? Duration.zero
                                : const Duration(milliseconds: 110),
                            width: 4,
                            height: 6 + (22 * clampedLevel * m),
                            decoration: BoxDecoration(
                              color: isMuted
                                  ? cs.outline
                                  : isVideoActive
                                      ? kw.liveVideo.accent
                                      : cs.primary,
                              borderRadius: KwShapes.radiusFull,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              if (statusText != null) ...[
                const SizedBox(width: KwSpacing.sm),
                Flexible(
                  child: Text(
                    statusText!,
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: cs.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: KwSpacing.sm),
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.xs,
            alignment: WrapAlignment.center,
            children: [
              _CallActionButton(
                icon: isMuted ? Icons.mic_off_rounded : Icons.mic_rounded,
                label: isMuted ? strings.callUnmute : strings.callMute,
                active: isMuted,
                activeBg: cs.secondaryContainer,
                activeFg: cs.onSecondaryContainer,
                onPressed: onToggleMute,
              ),
              _CallActionButton(
                icon: isSpeakerOn
                    ? Icons.volume_up_rounded
                    : Icons.volume_down_rounded,
                label: strings.callSpeaker,
                active: isSpeakerOn,
                activeBg: cs.secondaryContainer,
                activeFg: cs.onSecondaryContainer,
                onPressed: onToggleSpeaker,
              ),
              _CallActionButton(
                icon: isVideoActive
                    ? Icons.videocam_rounded
                    : Icons.videocam_outlined,
                label: strings.callSwitchToVideo,
                active: isVideoActive,
                activeBg: kw.liveVideo.container,
                activeFg: kw.liveVideo.onContainer,
                onPressed: onToggleVideo,
              ),
              _CallActionButton(
                icon: Icons.call_end_rounded,
                label: strings.callEnd,
                active: true,
                activeBg: kw.safety.accent,
                activeFg: cs.surface,
                onPressed: onEndCall,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CallActionButton extends StatelessWidget {
  const _CallActionButton({
    required this.icon,
    required this.label,
    required this.active,
    required this.activeBg,
    required this.activeFg,
    this.onPressed,
  });

  final IconData icon;
  final String label;
  final bool active;
  final Color activeBg;
  final Color activeFg;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: label,
      child: Tooltip(
        message: label,
        child: Material(
          color: active ? activeBg : cs.surface,
          borderRadius: KwShapes.radiusFull,
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onPressed,
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                minWidth: KwSpacing.minTouchTarget,
                minHeight: KwSpacing.minTouchTarget,
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: KwSpacing.md,
                  vertical: KwSpacing.sm,
                ),
                child: Icon(
                  icon,
                  color: active ? activeFg : cs.onSurface,
                  size: 22,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
