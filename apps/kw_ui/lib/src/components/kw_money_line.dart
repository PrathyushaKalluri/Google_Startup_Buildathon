import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_formatters.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Payer entity on a quote or settlement line (Shared Contract §5.1).
enum KwPayer {
  brand,
  plan,
  household;

  static KwPayer fromWire(String? value) {
    return switch (value?.toLowerCase()) {
      'brand' => KwPayer.brand,
      'plan' => KwPayer.plan,
      _ => KwPayer.household,
    };
  }
}

/// Quote or parts line item displaying paise-to-rupee formatting, payer chip
/// (`Brand`, `Plan`, `Household`), and an amber `"Needs checking"` treatment
/// for unmatched / `compatibility_unverified` parts (Shared Contract §11).
class KwMoneyLine extends StatelessWidget {
  const KwMoneyLine({
    super.key,
    required this.description,
    this.amountPaise,
    required this.payer,
    this.partNo,
    this.needsChecking = false,
    this.showZeroDecimals = true,
  });

  final String description;

  /// Amount in integer paise. Ignored visually when [needsChecking] is `true`.
  final int? amountPaise;
  final KwPayer payer;
  final String? partNo;

  /// When `true`, renders the amber `"Needs checking"` treatment and does NOT
  /// display a normal quote amount (Shared Contract §11).
  final bool needsChecking;
  final bool showZeroDecimals;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final (payerLabel, payerRole) = switch (payer) {
      KwPayer.brand => (strings.payerBrand, kw.verified),
      KwPayer.plan => (strings.payerPlan, kw.standard),
      KwPayer.household => (strings.payerHousehold, kw.urgent),
    };

    final amountText = needsChecking
        ? strings.needsChecking
        : formatInrPaise(
            amountPaise ?? 0,
            showZeroDecimals: showZeroDecimals,
          );

    return Semantics(
      label: needsChecking
          ? '$description, ${strings.needsChecking}, ${strings.needsCheckingExcludedHint}'
          : '$description, $amountText, paid by $payerLabel',
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.sm),
        decoration: BoxDecoration(
          color: needsChecking
              ? kw.needsChecking.container.withValues(alpha: 0.45)
              : cs.surfaceContainerLow,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(
            color: needsChecking
                ? kw.needsChecking.accent
                : cs.outlineVariant,
            width: needsChecking ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        description,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (partNo != null && partNo!.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          partNo!,
                          style: KwTheme.monoStyle(
                            context,
                            fontSize: theme.textTheme.labelSmall?.fontSize,
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: KwSpacing.sm),
                if (needsChecking)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: kw.needsChecking.container,
                      borderRadius: KwShapes.radiusSmall,
                      border: Border.all(
                        color: kw.needsChecking.accent.withValues(alpha: 0.7),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.warning_amber_rounded,
                          size: 16,
                          color: kw.needsChecking.onContainer,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          strings.needsChecking,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: kw.needsChecking.onContainer,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  Text(
                    amountText,
                    style: KwTheme.monoStyle(
                      context,
                      fontSize: theme.textTheme.titleSmall?.fontSize,
                      fontWeight: FontWeight.w700,
                      color: cs.onSurface,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
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
                    color: payerRole.container,
                    borderRadius: KwShapes.radiusSmall,
                  ),
                  child: Text(
                    payerLabel,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: payerRole.onContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (needsChecking)
                  Text(
                    strings.needsCheckingExcludedHint,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: kw.needsChecking.onContainer,
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
