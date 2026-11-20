import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_motion.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// 6-phase ticket lifecycle stepper (Design Spec §6).
class KwStatusStepper extends StatelessWidget {
  const KwStatusStepper({
    super.key,
    required this.currentStep,
    this.stepLabels,
    this.axis,
  }) : assert(currentStep >= 0 && currentStep <= 5);

  /// Zero-based index of the active step (`0` = Intake .. `5` = Closed).
  final int currentStep;

  /// Optional custom labels (must have length 6 if provided).
  final List<String>? stepLabels;

  /// Forces horizontal or vertical layout; defaults to responsive based on width.
  final Axis? axis;

  @override
  Widget build(BuildContext context) {
    final strings = KwStrings.of(context);
    final labels = stepLabels ??
        <String>[
          strings.stepIntake,
          strings.stepTriage,
          strings.stepSelfFix,
          strings.stepAssigned,
          strings.stepVisit,
          strings.stepClosed,
        ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final effectiveAxis =
            axis ?? (constraints.maxWidth < 460 ? Axis.vertical : Axis.horizontal);
        final activeLabel = labels[currentStep.clamp(0, labels.length - 1)];

        return Semantics(
          label: 'Step ${currentStep + 1} of ${labels.length}: $activeLabel',
          child: effectiveAxis == Axis.horizontal
              ? _HorizontalStepper(labels: labels, currentStep: currentStep)
              : _VerticalStepper(labels: labels, currentStep: currentStep),
        );
      },
    );
  }
}

class _HorizontalStepper extends StatelessWidget {
  const _HorizontalStepper({
    required this.labels,
    required this.currentStep,
  });

  final List<String> labels;
  final int currentStep;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < labels.length; i++) ...[
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: i == 0
                          ? const SizedBox.shrink()
                          : Container(
                              height: 2.5,
                              color: i <= currentStep
                                  ? kw.verified.accent
                                  : cs.outlineVariant,
                            ),
                    ),
                    _StepDot(
                      index: i,
                      currentStep: currentStep,
                    ),
                    Expanded(
                      child: i == labels.length - 1
                          ? const SizedBox.shrink()
                          : Container(
                              height: 2.5,
                              color: i < currentStep
                                  ? kw.verified.accent
                                  : cs.outlineVariant,
                            ),
                    ),
                  ],
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  labels[i],
                  textAlign: TextAlign.center,
                  style: theme.textTheme.labelSmall?.copyWith(
                    fontWeight:
                        i == currentStep ? FontWeight.w700 : FontWeight.w500,
                    color: i <= currentStep
                        ? cs.onSurface
                        : cs.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _VerticalStepper extends StatelessWidget {
  const _VerticalStepper({
    required this.labels,
    required this.currentStep,
  });

  final List<String> labels;
  final int currentStep;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < labels.length; i++)
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Column(
                  children: [
                    _StepDot(index: i, currentStep: currentStep),
                    if (i < labels.length - 1)
                      Expanded(
                        child: Container(
                          width: 2.5,
                          margin: const EdgeInsets.symmetric(vertical: 2),
                          color: i < currentStep
                              ? kw.verified.accent
                              : cs.outlineVariant,
                        ),
                      ),
                  ],
                ),
                const SizedBox(width: KwSpacing.sm),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: KwSpacing.sm),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        labels[i],
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: i == currentStep
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: i <= currentStep
                              ? cs.onSurface
                              : cs.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _StepDot extends StatelessWidget {
  const _StepDot({
    required this.index,
    required this.currentStep,
  });

  final int index;
  final int currentStep;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    final isDone = index < currentStep;
    final isActive = index == currentStep;

    final bgColor = isDone
        ? kw.verified.accent
        : isActive
            ? cs.primary
            : cs.surfaceContainerHighest;

    final fgColor = isDone
        ? cs.surface
        : isActive
            ? cs.onPrimary
            : cs.onSurfaceVariant;

    return AnimatedContainer(
      duration: KwMotion.durationFor(context, KwMotion.defaultDuration),
      curve: KwMotion.curveFor(context),
      width: isActive ? 28 : 24,
      height: isActive ? 28 : 24,
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: isActive ? KwShapes.radiusSmall : KwShapes.radiusFull,
      ),
      alignment: Alignment.center,
      child: isDone
          ? Icon(Icons.check_rounded, size: 16, color: fgColor)
          : Text(
              '${index + 1}',
              style: theme.textTheme.labelSmall?.copyWith(
                color: fgColor,
                fontWeight: FontWeight.w700,
              ),
            ),
    );
  }
}
