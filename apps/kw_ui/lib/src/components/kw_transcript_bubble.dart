import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_formatters.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

enum KwTranscriptSpeaker { agent, household }

enum KwTranscriptModality { voice, video, text }

/// Live call / conversation transcript bubble with speaker identity,
/// language chip (`en`/`hi`/`te`), modality badge, interim state, and
/// screen-reader live-region support.
class KwTranscriptBubble extends StatelessWidget {
  const KwTranscriptBubble({
    super.key,
    required this.speaker,
    required this.text,
    required this.languageCode,
    this.modality = KwTranscriptModality.voice,
    this.isFinal = true,
    this.timestamp,
    this.speakerNameOverride,
    this.liveRegion = false,
  });

  final KwTranscriptSpeaker speaker;
  final String text;
  final String languageCode;
  final KwTranscriptModality modality;
  final bool isFinal;
  final DateTime? timestamp;
  final String? speakerNameOverride;
  final bool liveRegion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final isAgent = speaker == KwTranscriptSpeaker.agent;
    final speakerLabel = speakerNameOverride ??
        (isAgent ? strings.speakerAgent : strings.speakerHousehold);

    final (modalityIcon, modalityLabel) = switch (modality) {
      KwTranscriptModality.voice => (Icons.mic_rounded, strings.modalityVoice),
      KwTranscriptModality.video =>
        (Icons.videocam_rounded, strings.modalityVideo),
      KwTranscriptModality.text =>
        (Icons.chat_bubble_outline_rounded, strings.modalityText),
    };

    final bubbleColor = isAgent
        ? cs.primaryContainer.withValues(alpha: 0.45)
        : cs.surfaceContainerHigh;
    final fgColor = cs.onSurface;
    final langChipText = languageCode.toUpperCase();

    return Semantics(
      liveRegion: liveRegion,
      label: '$speakerLabel ($modalityLabel, $langChipText): $text',
      child: Align(
        alignment: isAgent ? Alignment.centerLeft : Alignment.centerRight,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Container(
            padding: const EdgeInsets.all(KwSpacing.sm),
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(KwShapes.medium),
                topRight: const Radius.circular(KwShapes.medium),
                bottomLeft: Radius.circular(
                  isAgent ? KwShapes.extraSmall : KwShapes.medium,
                ),
                bottomRight: Radius.circular(
                  isAgent ? KwShapes.medium : KwShapes.extraSmall,
                ),
              ),
              border: Border.all(
                color: modality == KwTranscriptModality.video
                    ? kw.liveVideo.accent.withValues(alpha: 0.5)
                    : cs.outlineVariant,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: KwSpacing.xs,
                  runSpacing: KwSpacing.xxs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    CircleAvatar(
                      radius: 12,
                      backgroundColor:
                          isAgent ? cs.primary : cs.secondaryContainer,
                      child: Icon(
                        isAgent
                            ? Icons.support_agent_rounded
                            : Icons.home_rounded,
                        size: 14,
                        color: isAgent ? cs.onPrimary : cs.onSecondaryContainer,
                      ),
                    ),
                    Text(
                      speakerLabel,
                      style: theme.textTheme.labelMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: cs.surface,
                        borderRadius: KwShapes.radiusExtraSmall,
                      ),
                      child: Text(
                        langChipText,
                        style: KwTheme.monoStyle(
                          context,
                          fontSize: 11,
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          modalityIcon,
                          size: 13,
                          color: modality == KwTranscriptModality.video
                              ? kw.liveVideo.accent
                              : cs.onSurfaceVariant,
                        ),
                        const SizedBox(width: 3),
                        Text(
                          modalityLabel,
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                    if (timestamp != null)
                      Text(
                        formatIstDateTime(
                          timestamp!,
                          includeDate: false,
                          includeTzLabel: false,
                        ),
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  text,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: isFinal ? fgColor : cs.onSurfaceVariant,
                    fontStyle: isFinal ? FontStyle.normal : FontStyle.italic,
                  ),
                ),
                if (!isFinal) ...[
                  const SizedBox(height: KwSpacing.xxs),
                  Text(
                    strings.transcriptInterim,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: cs.primary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
