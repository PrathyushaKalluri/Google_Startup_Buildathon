import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'household_l10n.dart';

/// Surface 4: Zero-Sign-In Home Memory Page (route `/home/<token>`).
///
/// Loads `GET /v1/public/home/{token}` and renders each appliance card with
/// brand, model, age, warranty status, explainable Care Index (0–100) with
/// reasons, per-appliance append-only timeline, next due services, and
/// recorded advice notes.
class HomeMemoryScreen extends StatefulWidget {
  const HomeMemoryScreen({
    super.key,
    required this.token,
    required this.apiClient,
    required this.activeCentre,
  });

  final String token;
  final KwApiClient apiClient;
  final KwCentreIdentity activeCentre;

  @override
  State<HomeMemoryScreen> createState() => _HomeMemoryScreenState();
}

class _HomeMemoryScreenState extends State<HomeMemoryScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _data;

  @override
  void initState() {
    super.initState();
    unawaited(_loadHome());
  }

  @override
  void didUpdateWidget(covariant HomeMemoryScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.token != widget.token) {
      unawaited(_loadHome());
    }
  }

  Future<void> _loadHome() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await widget.apiClient.getPublicHome(widget.token);
      if (!mounted) return;
      setState(() {
        _data = result;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not load Home Memory for this link. Please try again.';
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> _asMapList(dynamic raw) {
    if (raw is List) {
      return raw
          .whereType<Map<dynamic, dynamic>>()
          .map((m) => m.map((k, v) => MapEntry(k.toString(), v)))
          .toList();
    }
    return const <Map<String, dynamic>>[];
  }

  List<String> _asStringList(dynamic raw) {
    if (raw is List) {
      return raw.map((e) => e.toString()).toList();
    }
    return const <String>[];
  }

  String _formatAge(Map<String, dynamic> appliance) {
    final explicitAge = appliance['age_label'] ?? appliance['age'];
    if (explicitAge != null && explicitAge.toString().trim().isNotEmpty) {
      return explicitAge.toString();
    }
    final purchaseDateRaw = appliance['purchase_date']?.toString();
    if (purchaseDateRaw == null || purchaseDateRaw.isEmpty) {
      return 'Age unrecorded';
    }
    final parsed = DateTime.tryParse(purchaseDateRaw);
    if (parsed == null) return 'Purchased $purchaseDateRaw';
    final months = DateTime.now().difference(parsed).inDays ~/ 30;
    if (months < 12) return '$months months old';
    final years = months ~/ 12;
    final remMonths = months % 12;
    return remMonths == 0 ? '$years yr old' : '$years yr $remMonths mo old';
  }

  @override
  Widget build(BuildContext context) {
    final hStrings = HouseholdStrings.of(context);

    if (_loading) {
      return Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: const Padding(
            padding: EdgeInsets.all(KwSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                KwSkeletonLoader(lines: 3, height: 18),
                SizedBox(height: KwSpacing.md),
                KwSkeletonLoader(lines: 4, height: 16),
              ],
            ),
          ),
        ),
      );
    }

    if (_error != null) {
      return KwErrorState(
        title: 'Home Memory unavailable',
        body: _error,
        onRetry: _loadHome,
      );
    }

    final data = _data ?? const <String, dynamic>{};
    final householdMap = data['household'] is Map
        ? (data['household'] as Map<dynamic, dynamic>)
            .map((k, v) => MapEntry(k.toString(), v))
        : const <String, dynamic>{};
    final appliances = _asMapList(data['appliances']);
    final nextDueServices = _asMapList(data['next_due_services']);
    final adviceNotes = _asMapList(data['advice_notes']);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: ListView(
          padding: const EdgeInsets.all(KwSpacing.md),
          children: [
            _buildHouseholdBanner(context, hStrings, householdMap),
            const SizedBox(height: KwSpacing.md),
            if (appliances.isEmpty)
              const KwEmptyState(
                icon: Icons.kitchen_outlined,
                title: 'No appliances recorded yet',
                body:
                    'Appliances inspected or serviced by your centre will appear here automatically.',
              )
            else
              for (final appliance in appliances) ...[
                _buildApplianceCard(context, hStrings, appliance),
                const SizedBox(height: KwSpacing.md),
              ],
            if (nextDueServices.isNotEmpty) ...[
              _buildNextDueServicesCard(context, hStrings, nextDueServices),
              const SizedBox(height: KwSpacing.md),
            ],
            if (adviceNotes.isNotEmpty)
              _buildAdviceNotesCard(context, hStrings, adviceNotes),
          ],
        ),
      ),
    );
  }

  Widget _buildHouseholdBanner(
    BuildContext context,
    HouseholdStrings hStrings,
    Map<String, dynamic> household,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final displayName =
        (household['display_name'] ?? 'Your Household').toString();
    final locality =
        (household['locality'] ?? widget.activeCentre.locality).toString();
    final centreName =
        (_data?['centre_name'] ?? widget.activeCentre.name).toString();

    return Card(
      color: cs.primaryContainer.withValues(alpha: 0.4),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: cs.primary,
              foregroundColor: cs.onPrimary,
              child: const Icon(Icons.home_rounded),
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$displayName · ${hStrings.homeMemoryTitle}',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '$locality · Maintained with $centreName',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: KwSpacing.xs,
                vertical: 4,
              ),
              decoration: BoxDecoration(
                color: kw.verified.container,
                borderRadius: KwShapes.radiusFull,
              ),
              child: Text(
                hStrings.zeroSignInBadge,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: kw.verified.onContainer,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildApplianceCard(
    BuildContext context,
    HouseholdStrings hStrings,
    Map<String, dynamic> appliance,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    final brand = (appliance['brand'] ?? 'Appliance').toString();
    final model = (appliance['model_code'] ??
            appliance['model'] ??
            'Model pending check')
        .toString();
    final category = (appliance['category_code'] ?? '').toString();
    final warrantyStatus = (appliance['warranty_status'] ??
            (appliance['warranty_end'] != null
                ? 'Warranty until ${appliance['warranty_end']}'
                : 'Out of warranty'))
        .toString();
    final ageText = _formatAge(appliance);

    final rawScore = appliance['care_index'] ?? appliance['care_index_score'];
    final careIndex = rawScore is num
        ? rawScore.toInt().clamp(0, 100)
        : int.tryParse('$rawScore')?.clamp(0, 100) ?? 78;
    final careReasons = _asStringList(
      appliance['care_index_reasons'] ?? appliance['care_reasons'],
    );
    final timeline = _asMapList(appliance['timeline']);

    final scoreRole = careIndex >= 75
        ? kw.verified
        : careIndex >= 45
            ? kw.needsChecking
            : kw.safety;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
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
                        '$brand $model',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        [
                          if (category.isNotEmpty) category,
                          ageText,
                        ].join(' · '),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: KwSpacing.xs,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: kw.standard.container,
                    borderRadius: KwShapes.radiusSmall,
                  ),
                  child: Text(
                    warrantyStatus,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: kw.standard.onContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            // Explainable Care Index (0-100) with reasons
            Container(
              padding: const EdgeInsets.all(KwSpacing.sm),
              decoration: BoxDecoration(
                color: scoreRole.container.withValues(alpha: 0.45),
                borderRadius: KwShapes.radiusMedium,
                border: Border.all(
                  color: scoreRole.accent.withValues(alpha: 0.45),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        hStrings.careIndexLabel,
                        style: theme.textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: scoreRole.onContainer,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '$careIndex / 100',
                        style: KwTheme.monoStyle(
                          context,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: scoreRole.onContainer,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.xs),
                  ClipRRect(
                    borderRadius: KwShapes.radiusFull,
                    child: LinearProgressIndicator(
                      value: careIndex / 100.0,
                      minHeight: 8,
                      color: scoreRole.accent,
                      backgroundColor: cs.surfaceContainerHighest,
                    ),
                  ),
                  if (careReasons.isNotEmpty) ...[
                    const SizedBox(height: KwSpacing.xs),
                    for (final reason in careReasons)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '• ',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: scoreRole.onContainer,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Expanded(
                              child: Text(
                                reason,
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: scoreRole.onContainer,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ],
              ),
            ),
            if (timeline.isNotEmpty) ...[
              const SizedBox(height: KwSpacing.md),
              Text(
                hStrings.serviceTimelineTitle,
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: KwSpacing.xs),
              for (final ev in timeline)
                KwEventRow(
                  type: (ev['type'] ?? 'ticket_closed').toString(),
                  title: (ev['title'] ?? 'Service record').toString(),
                  detail: ev['detail']?.toString(),
                  actor: ev['actor']?.toString(),
                  at: ev['at'] != null
                      ? DateTime.tryParse(ev['at'].toString())
                      : null,
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildNextDueServicesCard(
    BuildContext context,
    HouseholdStrings hStrings,
    List<Map<String, dynamic>> services,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.event_repeat_rounded, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  hStrings.nextDueServicesTitle,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            for (final svc in services)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.calendar_today_rounded, color: cs.primary),
                title: Text(
                  (svc['title'] ?? svc['service'] ?? 'Scheduled maintenance')
                      .toString(),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                subtitle: Text(
                  (svc['appliance'] ?? svc['reason'] ?? '').toString(),
                ),
                trailing: Text(
                  (svc['due_date'] ?? svc['due_at'] ?? '').toString(),
                  style: KwTheme.monoStyle(context, fontSize: 12),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdviceNotesCard(
    BuildContext context,
    HouseholdStrings hStrings,
    List<Map<String, dynamic>> notes,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.tips_and_updates_outlined, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  hStrings.recordedAdviceTitle,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            for (final note in notes)
              Padding(
                padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(KwSpacing.sm),
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHigh,
                    borderRadius: KwShapes.radiusMedium,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        (note['text'] ?? note['advice'] ?? '').toString(),
                        style: theme.textTheme.bodyMedium,
                      ),
                      if (note['by'] != null || note['at'] != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (note['by'] != null) note['by'].toString(),
                            if (note['at'] != null) note['at'].toString(),
                          ].join(' · '),
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
