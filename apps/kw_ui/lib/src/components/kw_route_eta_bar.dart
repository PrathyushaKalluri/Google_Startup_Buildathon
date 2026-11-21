import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Drive-time and distance pill with a static fallback badge when
/// live Google Maps routing is unavailable.
class KwRouteEtaBar extends StatelessWidget {
  const KwRouteEtaBar({
    super.key,
    required this.driveMinutes,
    required this.distanceKm,
    this.isStaticFallback = false,
    this.destinationLabel,
  });

  final int driveMinutes;
  final double distanceKm;
  final bool isStaticFallback;
  final String? destinationLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final distanceText = '${distanceKm.toStringAsFixed(1)} km';
    final etaText = '$driveMinutes min';

    return Semantics(
      label: 'Route estimate: $etaText, $distanceText'
          '${destinationLabel != null ? ' to $destinationLabel' : ''}'
          '${isStaticFallback ? ', ${strings.routeStaticFallbackBadge}' : ''}',
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: KwSpacing.sm,
          vertical: KwSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: cs.surfaceContainerHigh,
          borderRadius: KwShapes.radiusFull,
          border: Border.all(color: cs.outlineVariant),
        ),
        child: Wrap(
          spacing: KwSpacing.xs,
          runSpacing: KwSpacing.xxs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Icon(
              Icons.directions_car_rounded,
              size: 18,
              color: cs.primary,
            ),
            Text(
              etaText,
              style: KwTheme.monoStyle(
                context,
                fontSize: theme.textTheme.labelLarge?.fontSize,
                fontWeight: FontWeight.w700,
                color: cs.onSurface,
              ),
            ),
            Text(
              '·',
              style: theme.textTheme.labelLarge?.copyWith(
                color: cs.onSurfaceVariant,
              ),
            ),
            Text(
              distanceText,
              style: KwTheme.monoStyle(
                context,
                fontSize: theme.textTheme.labelLarge?.fontSize,
                fontWeight: FontWeight.w500,
                color: cs.onSurfaceVariant,
              ),
            ),
            if (destinationLabel != null && destinationLabel!.isNotEmpty)
              Text(
                '· $destinationLabel',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              ),
            if (isStaticFallback)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: KwSpacing.xs,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: kw.needsChecking.container,
                  borderRadius: KwShapes.radiusFull,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.offline_pin_outlined,
                      size: 13,
                      color: kw.needsChecking.onContainer,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      strings.routeStaticFallbackBadge,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: kw.needsChecking.onContainer,
                        fontWeight: FontWeight.w600,
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
}
