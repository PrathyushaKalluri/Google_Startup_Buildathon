import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Calm, purposeful empty state (Design Spec §1 & §6).
class KwEmptyState extends StatelessWidget {
  const KwEmptyState({
    super.key,
    this.icon = Icons.inbox_outlined,
    this.title,
    this.body,
    this.action,
  });

  final IconData icon;
  final String? title;
  final String? body;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = KwStrings.of(context);
    final effectiveTitle = title ?? strings.emptyDefaultTitle;
    final effectiveBody = body ?? strings.emptyDefaultBody;

    return Semantics(
      container: true,
      label: '$effectiveTitle. $effectiveBody',
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHighest,
                    borderRadius: KwShapes.radiusLarge,
                  ),
                  child: Icon(icon, size: 28, color: cs.onSurfaceVariant),
                ),
                const SizedBox(height: KwSpacing.md),
                Text(
                  effectiveTitle,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  effectiveBody,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: cs.onSurfaceVariant,
                  ),
                ),
                if (action != null) ...[
                  const SizedBox(height: KwSpacing.md),
                  action!,
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Calm, actionable error state with a retry button (≥ 48 dp touch target).
class KwErrorState extends StatelessWidget {
  const KwErrorState({
    super.key,
    this.title,
    this.body,
    this.onRetry,
    this.retryLabelOverride,
  });

  final String? title;
  final String? body;
  final VoidCallback? onRetry;
  final String? retryLabelOverride;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);
    final effectiveTitle = title ?? strings.errorDefaultTitle;
    final effectiveBody = body ?? strings.errorDefaultBody;

    return Semantics(
      container: true,
      liveRegion: true,
      label: '$effectiveTitle. $effectiveBody',
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: kw.declined.container,
                    borderRadius: KwShapes.radiusLarge,
                  ),
                  child: Icon(
                    Icons.error_outline_rounded,
                    size: 28,
                    color: kw.declined.onContainer,
                  ),
                ),
                const SizedBox(height: KwSpacing.md),
                Text(
                  effectiveTitle,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  effectiveBody,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                if (onRetry != null) ...[
                  const SizedBox(height: KwSpacing.md),
                  FilledButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(retryLabelOverride ?? strings.retryLabel),
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

/// Accessible placeholder skeleton loader that gently pulses unless
/// reduced motion is enabled.
class KwSkeletonLoader extends StatefulWidget {
  const KwSkeletonLoader({
    super.key,
    this.lines = 3,
    this.height = 14,
  });

  final int lines;
  final double height;

  @override
  State<KwSkeletonLoader> createState() => _KwSkeletonLoaderState();
}

class _KwSkeletonLoaderState extends State<KwSkeletonLoader>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final strings = KwStrings.of(context);
    final reduceMotion = KwMotion.shouldReduceMotion(context);

    Widget buildBars(double opacity) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var i = 0; i < widget.lines; i++) ...[
            if (i > 0) const SizedBox(height: KwSpacing.xs),
            FractionallySizedBox(
              widthFactor: i == widget.lines - 1 ? 0.65 : 1.0,
              child: Container(
                height: widget.height,
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest.withValues(alpha: opacity),
                  borderRadius: KwShapes.radiusSmall,
                ),
              ),
            ),
          ],
        ],
      );
    }

    return Semantics(
      label: strings.loadingLabel,
      child: reduceMotion
          ? buildBars(0.7)
          : AnimatedBuilder(
              animation: _controller,
              builder: (context, _) {
                final alpha = 0.45 + (_controller.value * 0.4);
                return buildBars(alpha);
              },
            ),
    );
  }
}
