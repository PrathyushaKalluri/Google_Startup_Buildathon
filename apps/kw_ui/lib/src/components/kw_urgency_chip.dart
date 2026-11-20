import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Urgency classes defined by Keepwell Shared Contract §5.1 & Design Spec §2.
enum KwUrgencyClass {
  safety,
  urgent,
  standard,
  planned;

  static KwUrgencyClass fromWire(String? value) {
    return switch (value?.toLowerCase()) {
      'safety' => KwUrgencyClass.safety,
      'urgent' => KwUrgencyClass.urgent,
      'planned' => KwUrgencyClass.planned,
      _ => KwUrgencyClass.standard,
    };
  }
}

/// Urgency indicator combining tonal colour, distinct icon shape, and text
/// label so urgency is never communicated by colour alone (WCAG 2.2 AA).
class KwUrgencyChip extends StatelessWidget {
  const KwUrgencyChip({
    super.key,
    required this.urgency,
    this.labelOverride,
    this.compact = false,
    this.liveRegion = false,
  });

  final KwUrgencyClass urgency;
  final String? labelOverride;
  final bool compact;
  final bool liveRegion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.kwColors;
    final strings = KwStrings.of(context);

    final (role, icon, defaultLabel, shapeRadius) = switch (urgency) {
      KwUrgencyClass.safety => (
          colors.safety,
          Icons.report_rounded,
          strings.urgencySafety,
          KwShapes.small,
        ),
      KwUrgencyClass.urgent => (
          colors.urgent,
          Icons.priority_high_rounded,
          strings.urgencyUrgent,
          KwShapes.small,
        ),
      KwUrgencyClass.standard => (
          colors.standard,
          Icons.schedule_rounded,
          strings.urgencyStandard,
          KwShapes.full,
        ),
      KwUrgencyClass.planned => (
          colors.planned,
          Icons.event_available_rounded,
          strings.urgencyPlanned,
          KwShapes.small,
        ),
    };

    final label = labelOverride ?? defaultLabel;
    final isSafety = urgency == KwUrgencyClass.safety;

    return Semantics(
      label: label,
      liveRegion: liveRegion || isSafety,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? KwSpacing.xs : KwSpacing.sm,
          vertical: compact ? KwSpacing.xxs : 6,
        ),
        decoration: BoxDecoration(
          color: role.container,
          borderRadius: BorderRadius.circular(shapeRadius),
          border: Border.all(
            color: role.accent.withValues(alpha: isSafety ? 0.85 : 0.45),
            width: isSafety ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: compact ? 15 : 18,
              color: role.onContainer,
              semanticLabel: null,
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: (compact
                        ? theme.textTheme.labelMedium
                        : theme.textTheme.labelLarge)
                    ?.copyWith(
                  color: role.onContainer,
                  fontWeight: isSafety ? FontWeight.w700 : FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
