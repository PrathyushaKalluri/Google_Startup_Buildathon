import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_formatters.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';
import 'kw_urgency_chip.dart';

/// Ticket summary card for the centre case board and brand/field lists.
///
/// Supports tap and keyboard focus with a visible 3 dp high-contrast ring,
/// distinct safety border highlight, unread indicator, and zero-overflow
/// wrapping at 200% text scale.
class KwCaseCard extends StatefulWidget {
  const KwCaseCard({
    super.key,
    required this.ticketId,
    required this.urgency,
    required this.triggerLabel,
    required this.householdName,
    required this.summary,
    this.applianceLabel,
    this.locality,
    this.neededBy,
    this.statusLabel,
    this.unread = false,
    this.selected = false,
    this.safetyBannerText,
    this.onTap,
  });

  final String ticketId;
  final KwUrgencyClass urgency;
  final String triggerLabel;
  final String householdName;
  final String summary;
  final String? applianceLabel;
  final String? locality;
  final DateTime? neededBy;
  final String? statusLabel;
  final bool unread;
  final bool selected;
  final String? safetyBannerText;
  final VoidCallback? onTap;

  @override
  State<KwCaseCard> createState() => _KwCaseCardState();
}

class _KwCaseCardState extends State<KwCaseCard> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);
    final isSafety = widget.urgency == KwUrgencyClass.safety;

    final borderColor = _focused
        ? kw.focusRing
        : isSafety
            ? kw.safety.accent
            : widget.selected
                ? cs.primary
                : cs.outlineVariant;

    final borderWidth = _focused
        ? 3.0
        : isSafety || widget.selected
            ? 2.0
            : 1.0;

    final bgColor = widget.selected
        ? cs.primaryContainer.withValues(alpha: 0.35)
        : isSafety
            ? kw.safety.container.withValues(alpha: 0.28)
            : cs.surfaceContainerLow;

    final neededByText = widget.neededBy != null
        ? '${strings.neededByPrefix}: ${formatIstDateTime(widget.neededBy!)}'
        : null;

    final semanticsParts = <String>[
      widget.householdName,
      if (widget.applianceLabel != null) widget.applianceLabel!,
      widget.summary,
      widget.triggerLabel,
      if (neededByText != null) neededByText,
      if (widget.unread) strings.unreadLabel,
    ];

    return Semantics(
      button: widget.onTap != null,
      selected: widget.selected,
      label: semanticsParts.join(', '),
      child: AnimatedContainer(
        duration: KwMotion.durationFor(context, KwMotion.fastDuration),
        curve: KwMotion.curveFor(context),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(color: borderColor, width: borderWidth),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: KwShapes.radiusMedium,
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: widget.onTap,
            onFocusChange: (focused) {
              if (_focused != focused) {
                setState(() => _focused = focused);
              }
            },
            child: Padding(
              padding: const EdgeInsets.all(KwSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: KwSpacing.xs,
                    runSpacing: KwSpacing.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      KwUrgencyChip(urgency: widget.urgency, compact: true),
                      _TriggerBadge(label: widget.triggerLabel),
                      if (widget.statusLabel != null)
                        Text(
                          widget.statusLabel!,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      if (widget.unread)
                        Tooltip(
                          message: strings.unreadLabel,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: cs.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          widget.householdName,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      if (widget.locality != null) ...[
                        const SizedBox(width: KwSpacing.xs),
                        Flexible(
                          child: Text(
                            widget.locality!,
                            textAlign: TextAlign.end,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (widget.applianceLabel != null) ...[
                    const SizedBox(height: KwSpacing.xxs),
                    Text(
                      widget.applianceLabel!,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: cs.primary,
                      ),
                    ),
                  ],
                  const SizedBox(height: KwSpacing.xs),
                  Text(
                    widget.summary,
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (isSafety) ...[
                    const SizedBox(height: KwSpacing.sm),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(KwSpacing.sm),
                      decoration: BoxDecoration(
                        color: kw.safety.container,
                        borderRadius: KwShapes.radiusSmall,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.health_and_safety_rounded,
                            size: 18,
                            color: kw.safety.onContainer,
                          ),
                          const SizedBox(width: KwSpacing.xs),
                          Expanded(
                            child: Text(
                              widget.safetyBannerText ??
                                  strings.safetyStopNotice,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: kw.safety.onContainer,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (neededByText != null) ...[
                    const SizedBox(height: KwSpacing.sm),
                    Row(
                      children: [
                        Icon(
                          Icons.access_time_rounded,
                          size: 16,
                          color: cs.onSurfaceVariant,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            neededByText,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TriggerBadge extends StatelessWidget {
  const _TriggerBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: KwSpacing.xs, vertical: 4),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest,
        borderRadius: KwShapes.radiusSmall,
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: cs.onSurfaceVariant,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
