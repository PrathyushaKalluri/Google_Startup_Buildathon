import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Exact 6-factor technician assignment score breakdown (Shared Contract §0 & §5.1).
///
/// Weights:
/// - `fixConfidence`: max 30
/// - `partsReadiness`: max 25
/// - `timeToVisit`: max 20
/// - `routeCost`: max 15
/// - `reliability`: max 5
/// - `householdFit`: max 5
///
/// Price is never scored.
@immutable
class KwCandidateScoreBreakdown {
  const KwCandidateScoreBreakdown({
    required this.fixConfidence,
    required this.partsReadiness,
    required this.timeToVisit,
    required this.routeCost,
    required this.reliability,
    required this.householdFit,
  });

  final double fixConfidence;
  final double partsReadiness;
  final double timeToVisit;
  final double routeCost;
  final double reliability;
  final double householdFit;

  double get total =>
      fixConfidence +
      partsReadiness +
      timeToVisit +
      routeCost +
      reliability +
      householdFit;
}

/// 6-factor stacked score bar with an accessible expandable breakdown table.
class KwCandidateScoreBar extends StatefulWidget {
  const KwCandidateScoreBar({
    super.key,
    required this.breakdown,
    this.totalScoreOverride,
    this.initiallyExpanded = false,
  });

  final KwCandidateScoreBreakdown breakdown;
  final double? totalScoreOverride;
  final bool initiallyExpanded;

  @override
  State<KwCandidateScoreBar> createState() => _KwCandidateScoreBarState();
}

class _KwCandidateScoreBarState extends State<KwCandidateScoreBar> {
  late bool _expanded = widget.initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final total = (widget.totalScoreOverride ?? widget.breakdown.total)
        .clamp(0.0, 100.0);

    final factors = <_ScoreFactor>[
      _ScoreFactor(
        label: strings.factorFixConfidence,
        score: widget.breakdown.fixConfidence.clamp(0.0, 30.0),
        max: 30,
        color: cs.primary,
      ),
      _ScoreFactor(
        label: strings.factorPartsReadiness,
        score: widget.breakdown.partsReadiness.clamp(0.0, 25.0),
        max: 25,
        color: kw.verified.accent,
      ),
      _ScoreFactor(
        label: strings.factorTimeToVisit,
        score: widget.breakdown.timeToVisit.clamp(0.0, 20.0),
        max: 20,
        color: kw.liveVideo.accent,
      ),
      _ScoreFactor(
        label: strings.factorRouteCost,
        score: widget.breakdown.routeCost.clamp(0.0, 15.0),
        max: 15,
        color: kw.urgent.accent,
      ),
      _ScoreFactor(
        label: strings.factorReliability,
        score: widget.breakdown.reliability.clamp(0.0, 5.0),
        max: 5,
        color: cs.tertiary,
      ),
      _ScoreFactor(
        label: strings.factorHouseholdFit,
        score: widget.breakdown.householdFit.clamp(0.0, 5.0),
        max: 5,
        color: cs.secondary,
      ),
    ];

    final semanticsSummary =
        '${strings.scoreTotalLabel}: ${total.toStringAsFixed(0)} out of 100. '
        '${factors.map((f) => '${f.label} ${f.score.toStringAsFixed(0)} of ${f.max}').join(', ')}.';

    return Semantics(
      container: true,
      label: semanticsSummary,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  strings.scoreTotalLabel,
                  style: theme.textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                '${total.toStringAsFixed(0)} / 100',
                style: KwTheme.monoStyle(
                  context,
                  fontSize: theme.textTheme.labelLarge?.fontSize,
                  fontWeight: FontWeight.w700,
                  color: cs.primary,
                ),
              ),
              const SizedBox(width: KwSpacing.xs),
              TextButton.icon(
                onPressed: () => setState(() => _expanded = !_expanded),
                icon: Icon(
                  _expanded
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.keyboard_arrow_down_rounded,
                  size: 18,
                ),
                label: Text(strings.scoreBreakdownToggle),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: KwShapes.radiusFull,
            child: Container(
              height: 12,
              color: cs.surfaceContainerHighest,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth;
                  return Row(
                    children: [
                      for (final factor in factors)
                        if (factor.score > 0)
                          Tooltip(
                            message:
                                '${factor.label}: ${factor.score.toStringAsFixed(1)}/${factor.max}',
                            child: Container(
                              width: width * (factor.score / 100.0),
                              height: 12,
                              color: factor.color,
                            ),
                          ),
                    ],
                  );
                },
              ),
            ),
          ),
          if (_expanded) ...[
            const SizedBox(height: KwSpacing.sm),
            Container(
              padding: const EdgeInsets.all(KwSpacing.sm),
              decoration: BoxDecoration(
                color: cs.surfaceContainerLow,
                borderRadius: KwShapes.radiusMedium,
                border: Border.all(color: cs.outlineVariant),
              ),
              child: Column(
                children: [
                  for (final factor in factors)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: factor.color,
                              borderRadius: KwShapes.radiusExtraSmall,
                            ),
                          ),
                          const SizedBox(width: KwSpacing.xs),
                          Expanded(
                            child: Text(
                              factor.label,
                              style: theme.textTheme.bodySmall,
                            ),
                          ),
                          Text(
                            '${factor.score.toStringAsFixed(0)} / ${factor.max}',
                            style: KwTheme.monoStyle(
                              context,
                              fontSize: theme.textTheme.bodySmall?.fontSize,
                              color: cs.onSurfaceVariant,
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

class _ScoreFactor {
  const _ScoreFactor({
    required this.label,
    required this.score,
    required this.max,
    required this.color,
  });

  final String label;
  final double score;
  final int max;
  final Color color;
}
