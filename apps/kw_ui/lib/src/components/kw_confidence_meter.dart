import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// PAIR-compliant diagnostic probability bar with honest abstention banner.
class KwConfidenceMeter extends StatelessWidget {
  const KwConfidenceMeter({
    super.key,
    required this.probability,
    this.label,
    this.abstained = false,
    this.abstentionReason,
    this.evidenceCount,
    this.onInspectEvidence,
  });

  /// Probability between `0.0` and `1.0`.
  final double probability;
  final String? label;
  final bool abstained;
  final String? abstentionReason;
  final int? evidenceCount;
  final VoidCallback? onInspectEvidence;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final clamped = probability.clamp(0.0, 1.0);
    final percent = (clamped * 100).round();
    final title = label ?? strings.confidenceLabel;

    final role = abstained
        ? kw.needsChecking
        : clamped >= 0.75
            ? kw.verified
            : clamped >= 0.45
                ? kw.standard
                : kw.needsChecking;

    return Semantics(
      label: abstained
          ? '$title: ${strings.abstainedTitle}'
          : '$title: $percent%',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                '$percent%',
                style: KwTheme.monoStyle(
                  context,
                  fontSize: theme.textTheme.labelLarge?.fontSize,
                  fontWeight: FontWeight.w700,
                  color: role.accent,
                ),
              ),
              if (onInspectEvidence != null) ...[
                const SizedBox(width: KwSpacing.xs),
                IconButton(
                  onPressed: onInspectEvidence,
                  icon: const Icon(Icons.info_outline_rounded, size: 20),
                  tooltip: evidenceCount != null
                      ? '$evidenceCount evidence'
                      : title,
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: KwShapes.radiusFull,
            child: Container(
              height: 10,
              width: double.infinity,
              color: cs.surfaceContainerHighest,
              alignment: Alignment.centerLeft,
              child: KwSpringValueBuilder(
                value: clamped,
                spring: KwMotion.effectsDefault,
                builder: (context, animatedValue, _) {
                  return FractionallySizedBox(
                    widthFactor: animatedValue.clamp(0.0, 1.0),
                    child: Container(
                      decoration: BoxDecoration(
                        color: role.accent,
                        borderRadius: KwShapes.radiusFull,
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          if (abstained) ...[
            const SizedBox(height: KwSpacing.sm),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(KwSpacing.sm),
              decoration: BoxDecoration(
                color: kw.needsChecking.container,
                borderRadius: KwShapes.radiusMedium,
                border: Border.all(
                  color: kw.needsChecking.accent.withValues(alpha: 0.6),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.help_outline_rounded,
                    size: 18,
                    color: kw.needsChecking.onContainer,
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          strings.abstainedTitle,
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: kw.needsChecking.onContainer,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          abstentionReason ?? strings.abstainedDefaultReason,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: kw.needsChecking.onContainer,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
