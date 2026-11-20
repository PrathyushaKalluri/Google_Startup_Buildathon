import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Custom-painted radial FVR-14 (First-Visit Resolution, 14 days) gauge
/// with M3 Expressive spring animation and accessible numeric Semantics.
class KwFvrGauge extends StatelessWidget {
  const KwFvrGauge({
    super.key,
    required this.rate,
    this.size = 156,
    this.targetRate = 0.85,
    this.labelOverride,
    this.subtitleOverride,
  });

  /// Ratio from `0.0` to `1.0` (e.g. `0.88` renders `88%`).
  final double rate;
  final double size;
  final double targetRate;
  final String? labelOverride;
  final String? subtitleOverride;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final clamped = rate.clamp(0.0, 1.0);
    final percent = (clamped * 100).round();
    final targetPercent = (targetRate.clamp(0.0, 1.0) * 100).round();

    final arcColor = clamped >= targetRate
        ? kw.verified.accent
        : clamped >= 0.65
            ? kw.needsChecking.accent
            : kw.safety.accent;

    final label = labelOverride ?? strings.fvr14Label;
    final subtitle = subtitleOverride ?? strings.fvr14Subtitle;

    return Semantics(
      label: '$label: $percent%, target $targetPercent%. $subtitle',
      value: '$percent%',
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: KwSpringValueBuilder(
              value: clamped,
              spring: KwMotion.spatialSlow,
              builder: (context, animatedValue, _) {
                return CustomPaint(
                  painter: _FvrArcPainter(
                    progress: animatedValue.clamp(0.0, 1.0),
                    target: targetRate.clamp(0.0, 1.0),
                    trackColor: cs.surfaceContainerHighest,
                    arcColor: arcColor,
                    targetTickColor: cs.onSurfaceVariant,
                  ),
                  child: Center(
                    child: Padding(
                      padding: EdgeInsets.all(size * 0.16),
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              '$percent%',
                              style: KwTheme.monoStyle(
                                context,
                                fontSize: size * 0.2,
                                fontWeight: FontWeight.w800,
                                color: cs.onSurface,
                              ),
                            ),
                            Text(
                              label,
                              style: theme.textTheme.labelMedium?.copyWith(
                                color: arcColor,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: KwSpacing.xs),
          Text(
            subtitle,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall?.copyWith(
              color: cs.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _FvrArcPainter extends CustomPainter {
  const _FvrArcPainter({
    required this.progress,
    required this.target,
    required this.trackColor,
    required this.arcColor,
    required this.targetTickColor,
  });

  final double progress;
  final double target;
  final Color trackColor;
  final Color arcColor;
  final Color targetTickColor;

  @override
  void paint(Canvas canvas, Size size) {
    final strokeWidth = size.width * 0.095;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.shortestSide - strokeWidth) / 2;
    const startAngle = math.pi * 0.75;
    const sweepTotal = math.pi * 1.5;

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final arcPaint = Paint()
      ..color = arcColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final rect = Rect.fromCircle(center: center, radius: radius);
    canvas.drawArc(rect, startAngle, sweepTotal, false, trackPaint);
    if (progress > 0) {
      canvas.drawArc(
        rect,
        startAngle,
        sweepTotal * progress,
        false,
        arcPaint,
      );
    }

    // Target marker tick.
    final targetAngle = startAngle + sweepTotal * target;
    final inner = Offset(
      center.dx + (radius - strokeWidth * 0.65) * math.cos(targetAngle),
      center.dy + (radius - strokeWidth * 0.65) * math.sin(targetAngle),
    );
    final outer = Offset(
      center.dx + (radius + strokeWidth * 0.65) * math.cos(targetAngle),
      center.dy + (radius + strokeWidth * 0.65) * math.sin(targetAngle),
    );
    final tickPaint = Paint()
      ..color = targetTickColor
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(inner, outer, tickPaint);
  }

  @override
  bool shouldRepaint(covariant _FvrArcPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.target != target ||
        oldDelegate.trackColor != trackColor ||
        oldDelegate.arcColor != arcColor ||
        oldDelegate.targetTickColor != targetTickColor;
  }
}
