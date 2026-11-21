import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Wire values for `ConsentGate.answer` (Shared Contract §5.1).
enum KwConsentAnswer {
  yes,
  no,
  silence,
  notAsked;

  static KwConsentAnswer fromWire(String? value) {
    return switch (value?.toLowerCase()) {
      'yes' => KwConsentAnswer.yes,
      'no' => KwConsentAnswer.no,
      'silence' => KwConsentAnswer.silence,
      _ => KwConsentAnswer.notAsked,
    };
  }
}

/// Wire values for `ConsentGate.choice` (Shared Contract §5.1).
enum KwConsentChoice {
  continueHere,
  switchToVideo;

  static KwConsentChoice? fromWire(String? value) {
    return switch (value?.toLowerCase()) {
      'continue_here' => KwConsentChoice.continueHere,
      'switch_to_video' => KwConsentChoice.switchToVideo,
      _ => null,
    };
  }
}

/// Data model for one consent gate step (Gate 1 or Gate 2).
@immutable
class KwConsentGateState {
  const KwConsentGateState({
    required this.gate,
    required this.answer,
    this.choice,
    this.notAskedReason,
  });

  /// `1` (safe self-fix) or `2` (continue here vs switch to video).
  final int gate;
  final KwConsentAnswer answer;
  final KwConsentChoice? choice;

  /// E.g. `safety_flag`, `non_repair`, `gate_1_declined`.
  final String? notAskedReason;
}

/// Visualizes the two-step Keepwell self-fix consent gates (Gate 1 & Gate 2).
class KwConsentGateCard extends StatelessWidget {
  const KwConsentGateCard({
    super.key,
    required this.gate1,
    required this.gate2,
    this.titleOverride,
  });

  final KwConsentGateState gate1;
  final KwConsentGateState gate2;
  final String? titleOverride;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = KwStrings.of(context);

    return Semantics(
      container: true,
      label: titleOverride ?? strings.consentGateTitle,
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.md),
        decoration: BoxDecoration(
          color: cs.surfaceContainerLow,
          borderRadius: KwShapes.radiusLarge,
          border: Border.all(color: cs.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.verified_user_outlined, size: 20, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    titleOverride ?? strings.consentGateTitle,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            _GateRow(
              label: strings.gate1Label,
              state: gate1,
            ),
            const SizedBox(height: KwSpacing.xs),
            _GateRow(
              label: strings.gate2Label,
              state: gate2,
            ),
          ],
        ),
      ),
    );
  }
}

class _GateRow extends StatelessWidget {
  const _GateRow({
    required this.label,
    required this.state,
  });

  final String label;
  final KwConsentGateState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);

    final (role, icon, answerText) = switch (state.answer) {
      KwConsentAnswer.yes => (
          state.choice == KwConsentChoice.switchToVideo
              ? kw.liveVideo
              : kw.verified,
          state.choice == KwConsentChoice.switchToVideo
              ? Icons.videocam_rounded
              : Icons.check_circle_rounded,
          state.choice == KwConsentChoice.switchToVideo
              ? strings.gateChoiceSwitchToVideo
              : state.choice == KwConsentChoice.continueHere
                  ? strings.gateChoiceContinueHere
                  : strings.gateAnswerYes,
        ),
      KwConsentAnswer.no => (
          kw.declined,
          Icons.cancel_rounded,
          strings.gateAnswerNo,
        ),
      KwConsentAnswer.silence => (
          kw.needsChecking,
          Icons.hearing_disabled_rounded,
          strings.gateAnswerSilence,
        ),
      KwConsentAnswer.notAsked => (
          state.notAskedReason == 'safety_flag' ? kw.safety : kw.standard,
          state.notAskedReason == 'safety_flag'
              ? Icons.report_rounded
              : Icons.remove_circle_outline_rounded,
          strings.gateAnswerNotAsked,
        ),
    };

    final reasonText = _formatNotAskedReason(state.notAskedReason, strings);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(KwSpacing.sm),
      decoration: BoxDecoration(
        color: cs.surface,
        borderRadius: KwShapes.radiusMedium,
        border: Border.all(color: cs.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: KwSpacing.xs,
            runSpacing: KwSpacing.xs,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                label,
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: KwSpacing.xs,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: role.container,
                  borderRadius: KwShapes.radiusSmall,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(icon, size: 15, color: role.onContainer),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        answerText,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: role.onContainer,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (reasonText != null) ...[
            const SizedBox(height: KwSpacing.xxs),
            Text(
              reasonText,
              style: theme.textTheme.bodySmall?.copyWith(
                color: state.notAskedReason == 'safety_flag'
                    ? kw.safety.accent
                    : cs.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }

  String? _formatNotAskedReason(String? reason, KwStrings strings) {
    if (reason == null || reason.isEmpty) return null;
    return switch (reason) {
      'safety_flag' => strings.gateSkippedSafetyReason,
      'non_repair' => strings.gateSkippedNonRepairReason,
      _ => reason.replaceAll('_', ' '),
    };
  }
}
