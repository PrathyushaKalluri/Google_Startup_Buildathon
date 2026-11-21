import 'package:flutter/material.dart';

import '../theme/kw_formatters.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Semantic tone bucket for live timeline / feed events.
enum KwEventTone {
  neutral,
  standard,
  verified,
  needsChecking,
  urgent,
  safety,
  liveVideo,
}

/// Visual metadata resolved for each Contract §8 event type.
@immutable
class KwEventVisualMeta {
  const KwEventVisualMeta({
    required this.icon,
    required this.tone,
    required this.category,
  });

  final IconData icon;
  final KwEventTone tone;
  final String category;

  /// All 34 Shared Contract §8 event types.
  static const List<String> allContractTypes = <String>[
    'conversation_started',
    'recording_notice_logged',
    'household_identified',
    'appliance_identified',
    'authority_checked',
    'urgency_assessed',
    'safety_stop_sent',
    'clarifying_asked',
    'clarifying_answered',
    'gate_asked',
    'gate_answered',
    'modality_changed',
    'fix_offered',
    'fix_step',
    'fix_result',
    'diagnosis_updated',
    'visit_plan_ready',
    'candidates_scored',
    'slots_offered',
    'technician_assigned',
    'reassigned',
    'quote_issued',
    'quote_approved',
    'payment_initiated',
    'payment_confirmed',
    'payment_failed',
    'debrief_processed',
    'otp_sent',
    'ticket_closed',
    'brand_request_received',
    'brand_request_declined',
    'retailer_handover_received',
    'shared_history_read',
    'error_notice',
  ];

  /// Resolves a distinct visual treatment for all 34 Contract §8 event types,
  /// with a safe generic fallback for any unknown type.
  static KwEventVisualMeta resolve(String type) {
    return switch (type) {
      'conversation_started' => const KwEventVisualMeta(
          icon: Icons.call_received_rounded,
          tone: KwEventTone.standard,
          category: 'Intake',
        ),
      'recording_notice_logged' => const KwEventVisualMeta(
          icon: Icons.record_voice_over_rounded,
          tone: KwEventTone.neutral,
          category: 'Compliance',
        ),
      'household_identified' => const KwEventVisualMeta(
          icon: Icons.home_rounded,
          tone: KwEventTone.verified,
          category: 'Identity',
        ),
      'appliance_identified' => const KwEventVisualMeta(
          icon: Icons.kitchen_rounded,
          tone: KwEventTone.verified,
          category: 'Appliance',
        ),
      'authority_checked' => const KwEventVisualMeta(
          icon: Icons.verified_user_rounded,
          tone: KwEventTone.standard,
          category: 'Authority',
        ),
      'urgency_assessed' => const KwEventVisualMeta(
          icon: Icons.speed_rounded,
          tone: KwEventTone.urgent,
          category: 'Urgency',
        ),
      'safety_stop_sent' => const KwEventVisualMeta(
          icon: Icons.report_rounded,
          tone: KwEventTone.safety,
          category: 'Safety',
        ),
      'clarifying_asked' => const KwEventVisualMeta(
          icon: Icons.help_outline_rounded,
          tone: KwEventTone.standard,
          category: 'Triage',
        ),
      'clarifying_answered' => const KwEventVisualMeta(
          icon: Icons.question_answer_rounded,
          tone: KwEventTone.standard,
          category: 'Triage',
        ),
      'gate_asked' => const KwEventVisualMeta(
          icon: Icons.rule_rounded,
          tone: KwEventTone.standard,
          category: 'Consent',
        ),
      'gate_answered' => const KwEventVisualMeta(
          icon: Icons.fact_check_rounded,
          tone: KwEventTone.verified,
          category: 'Consent',
        ),
      'modality_changed' => const KwEventVisualMeta(
          icon: Icons.videocam_rounded,
          tone: KwEventTone.liveVideo,
          category: 'Video',
        ),
      'fix_offered' => const KwEventVisualMeta(
          icon: Icons.build_circle_outlined,
          tone: KwEventTone.standard,
          category: 'Self-fix',
        ),
      'fix_step' => const KwEventVisualMeta(
          icon: Icons.checklist_rounded,
          tone: KwEventTone.standard,
          category: 'Self-fix',
        ),
      'fix_result' => const KwEventVisualMeta(
          icon: Icons.task_alt_rounded,
          tone: KwEventTone.needsChecking,
          category: 'Self-fix',
        ),
      'diagnosis_updated' => const KwEventVisualMeta(
          icon: Icons.biotech_rounded,
          tone: KwEventTone.standard,
          category: 'Diagnosis',
        ),
      'visit_plan_ready' => const KwEventVisualMeta(
          icon: Icons.assignment_turned_in_rounded,
          tone: KwEventTone.verified,
          category: 'Visit plan',
        ),
      'candidates_scored' => const KwEventVisualMeta(
          icon: Icons.leaderboard_rounded,
          tone: KwEventTone.standard,
          category: 'Matching',
        ),
      'slots_offered' => const KwEventVisualMeta(
          icon: Icons.calendar_month_rounded,
          tone: KwEventTone.standard,
          category: 'Booking',
        ),
      'technician_assigned' => const KwEventVisualMeta(
          icon: Icons.engineering_rounded,
          tone: KwEventTone.verified,
          category: 'Assignment',
        ),
      'reassigned' => const KwEventVisualMeta(
          icon: Icons.swap_horiz_rounded,
          tone: KwEventTone.needsChecking,
          category: 'Override',
        ),
      'quote_issued' => const KwEventVisualMeta(
          icon: Icons.receipt_long_rounded,
          tone: KwEventTone.standard,
          category: 'Quote',
        ),
      'quote_approved' => const KwEventVisualMeta(
          icon: Icons.thumb_up_alt_rounded,
          tone: KwEventTone.verified,
          category: 'Quote',
        ),
      'payment_initiated' => const KwEventVisualMeta(
          icon: Icons.account_balance_wallet_outlined,
          tone: KwEventTone.standard,
          category: 'Payment',
        ),
      'payment_confirmed' => const KwEventVisualMeta(
          icon: Icons.payments_rounded,
          tone: KwEventTone.verified,
          category: 'Payment',
        ),
      'payment_failed' => const KwEventVisualMeta(
          icon: Icons.money_off_csred_rounded,
          tone: KwEventTone.safety,
          category: 'Payment',
        ),
      'debrief_processed' => const KwEventVisualMeta(
          icon: Icons.summarize_rounded,
          tone: KwEventTone.standard,
          category: 'Debrief',
        ),
      'otp_sent' => const KwEventVisualMeta(
          icon: Icons.pin_rounded,
          tone: KwEventTone.standard,
          category: 'Closure',
        ),
      'ticket_closed' => const KwEventVisualMeta(
          icon: Icons.verified_rounded,
          tone: KwEventTone.verified,
          category: 'Closed',
        ),
      'brand_request_received' => const KwEventVisualMeta(
          icon: Icons.business_rounded,
          tone: KwEventTone.standard,
          category: 'Brand',
        ),
      'brand_request_declined' => const KwEventVisualMeta(
          icon: Icons.block_rounded,
          tone: KwEventTone.safety,
          category: 'Brand',
        ),
      'retailer_handover_received' => const KwEventVisualMeta(
          icon: Icons.storefront_rounded,
          tone: KwEventTone.standard,
          category: 'Retailer',
        ),
      'shared_history_read' => const KwEventVisualMeta(
          icon: Icons.history_edu_rounded,
          tone: KwEventTone.neutral,
          category: 'History',
        ),
      'error_notice' => const KwEventVisualMeta(
          icon: Icons.error_outline_rounded,
          tone: KwEventTone.safety,
          category: 'Notice',
        ),
      _ => const KwEventVisualMeta(
          icon: Icons.bolt_rounded,
          tone: KwEventTone.neutral,
          category: 'Event',
        ),
    };
  }
}

/// Renders a single live feed or ticket timeline event row with distinct
/// icon/colour treatment for all 34 Contract §8 event types + unknown fallback.
class KwEventRow extends StatelessWidget {
  const KwEventRow({
    super.key,
    required this.type,
    required this.title,
    this.detail,
    this.actor,
    this.at,
    this.onTap,
    this.liveRegion = false,
  });

  final String type;
  final String title;
  final String? detail;
  final String? actor;
  final DateTime? at;
  final VoidCallback? onTap;
  final bool liveRegion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final meta = KwEventVisualMeta.resolve(type);

    final (bgColor, fgColor, accentColor) = switch (meta.tone) {
      KwEventTone.neutral => (
          cs.surfaceContainerHighest,
          cs.onSurfaceVariant,
          cs.outline,
        ),
      KwEventTone.standard => (
          kw.standard.container,
          kw.standard.onContainer,
          kw.standard.accent,
        ),
      KwEventTone.verified => (
          kw.verified.container,
          kw.verified.onContainer,
          kw.verified.accent,
        ),
      KwEventTone.needsChecking => (
          kw.needsChecking.container,
          kw.needsChecking.onContainer,
          kw.needsChecking.accent,
        ),
      KwEventTone.urgent => (
          kw.urgent.container,
          kw.urgent.onContainer,
          kw.urgent.accent,
        ),
      KwEventTone.safety => (
          kw.safety.container,
          kw.safety.onContainer,
          kw.safety.accent,
        ),
      KwEventTone.liveVideo => (
          kw.liveVideo.container,
          kw.liveVideo.onContainer,
          kw.liveVideo.accent,
        ),
    };

    final timeLabel = at != null
        ? formatIstDateTime(at!, includeDate: false, includeTzLabel: false)
        : null;

    return Semantics(
      button: onTap != null,
      liveRegion: liveRegion,
      label: '${meta.category}: $title'
          '${detail != null && detail!.isNotEmpty ? '. $detail' : ''}',
      child: Material(
        color: Colors.transparent,
        borderRadius: KwShapes.radiusMedium,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.sm,
              vertical: KwSpacing.xs,
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: bgColor,
                    borderRadius: KwShapes.radiusSmall,
                    border: Border.all(
                      color: accentColor.withValues(alpha: 0.35),
                    ),
                  ),
                  alignment: Alignment.center,
                  child: Icon(meta.icon, size: 19, color: fgColor),
                ),
                const SizedBox(width: KwSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: KwSpacing.xs,
                        runSpacing: 2,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            meta.category,
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: accentColor,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (actor != null && actor!.isNotEmpty)
                            Text(
                              '· $actor',
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: cs.onSurfaceVariant,
                              ),
                            ),
                          if (timeLabel != null)
                            Text(
                              '· $timeLabel',
                              style: KwTheme.monoStyle(
                                context,
                                fontSize: theme.textTheme.labelSmall?.fontSize,
                                color: cs.onSurfaceVariant,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        title,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (detail != null && detail!.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          detail!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
