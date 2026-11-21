import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_formatters.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// A candidate appointment slot window with an `en-IN` paise price range.
@immutable
class KwSlotOption {
  const KwSlotOption({
    required this.id,
    required this.start,
    required this.end,
    required this.priceLowPaise,
    required this.priceHighPaise,
    this.recommended = false,
    this.technicianName,
  });

  final String id;
  final DateTime start;
  final DateTime end;
  final int priceLowPaise;
  final int priceHighPaise;
  final bool recommended;
  final String? technicianName;
}

/// Slot picker displaying 1 recommended + up to 2 alternative windows
/// with `en-IN` price ranges and accessible radio semantics.
class KwSlotPicker extends StatelessWidget {
  const KwSlotPicker({
    super.key,
    required this.options,
    this.selectedId,
    this.onSelected,
  });

  final List<KwSlotOption> options;
  final String? selectedId;
  final ValueChanged<KwSlotOption>? onSelected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final visible = options.take(3).toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < visible.length; i++) ...[
          if (i > 0) const SizedBox(height: KwSpacing.xs),
          _SlotCard(
            option: visible[i],
            selected: visible[i].id == selectedId,
            badgeText: visible[i].recommended
                ? strings.recommendedSlotBadge
                : strings.alternativeSlotBadge,
            onTap: onSelected != null ? () => onSelected!(visible[i]) : null,
            theme: theme,
            cs: cs,
            kw: kw,
          ),
        ],
      ],
    );
  }
}

class _SlotCard extends StatelessWidget {
  const _SlotCard({
    required this.option,
    required this.selected,
    required this.badgeText,
    required this.onTap,
    required this.theme,
    required this.cs,
    required this.kw,
  });

  final KwSlotOption option;
  final bool selected;
  final String badgeText;
  final VoidCallback? onTap;
  final ThemeData theme;
  final ColorScheme cs;
  final KwSemanticColors kw;

  @override
  Widget build(BuildContext context) {
    final windowText = formatIstSlotWindow(option.start, option.end);
    final priceText = formatInrRange(option.priceLowPaise, option.priceHighPaise);

    return Semantics(
      button: onTap != null,
      selected: selected,
      label: '$badgeText slot: $windowText, estimate $priceText'
          '${option.technicianName != null ? ', ${option.technicianName}' : ''}',
      child: AnimatedContainer(
        duration: KwMotion.durationFor(context, KwMotion.fastDuration),
        curve: KwMotion.curveFor(context),
        decoration: BoxDecoration(
          color: selected
              ? cs.primaryContainer.withValues(alpha: 0.45)
              : cs.surfaceContainerLow,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(
            color: selected
                ? cs.primary
                : option.recommended
                    ? kw.standard.accent.withValues(alpha: 0.6)
                    : cs.outlineVariant,
            width: selected ? 2.0 : 1.0,
          ),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: KwShapes.radiusMedium,
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                minHeight: KwSpacing.minTouchTarget,
              ),
              child: Padding(
                padding: const EdgeInsets.all(KwSpacing.md),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Icon(
                        selected
                            ? Icons.radio_button_checked_rounded
                            : Icons.radio_button_off_rounded,
                        color: selected ? cs.primary : cs.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(width: KwSpacing.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: KwSpacing.xs,
                            runSpacing: KwSpacing.xxs,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: KwSpacing.xs,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: option.recommended
                                      ? kw.verified.container
                                      : cs.surfaceContainerHighest,
                                  borderRadius: KwShapes.radiusExtraSmall,
                                ),
                                child: Text(
                                  badgeText,
                                  style: theme.textTheme.labelSmall?.copyWith(
                                    color: option.recommended
                                        ? kw.verified.onContainer
                                        : cs.onSurfaceVariant,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              if (option.technicianName != null)
                                Text(
                                  option.technicianName!,
                                  style: theme.textTheme.labelMedium?.copyWith(
                                    color: cs.onSurfaceVariant,
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: KwSpacing.xs),
                          Text(
                            windowText,
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            priceText,
                            style: KwTheme.monoStyle(
                              context,
                              fontSize: theme.textTheme.bodyMedium?.fontSize,
                              color: cs.primary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
