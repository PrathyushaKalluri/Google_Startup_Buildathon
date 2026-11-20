import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Centre KPI Overview screen with [KwFvrGauge] (FVR-14), KPI cards, and
/// accessible bar charts with a Chart / Table toggle (WCAG 2.2 AA).
class OverviewScreen extends StatefulWidget {
  const OverviewScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<OverviewScreen> createState() => _OverviewScreenState();
}

class _OverviewScreenState extends State<OverviewScreen> {
  CentreOverview? _overview;
  bool _loading = true;
  String? _error;
  bool _showAsTable = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final ctrl = widget.controller;
      final isPlatform = ctrl.session?.role == KwRole.platform;
      final data = await ctrl.apiClient.getCentreOverview(
        centreId: isPlatform ? null : ctrl.activeCentreId,
        centreKey: isPlatform ? null : ctrl.activeCentreKey,
      );
      if (mounted) {
        setState(() {
          _overview = data;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(KwSpacing.lg),
        child: KwSkeletonLoader(lines: 8),
      );
    }
    if (_error != null || _overview == null) {
      return KwErrorState(
        title: 'Could not load overview metrics',
        body: _error,
        onRetry: _load,
      );
    }

    final data = _overview!;
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(KwSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.xs,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.centreName.isNotEmpty
                        ? data.centreName
                        : 'Centre Overview',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    'Operational quality, consent funnel, and autonomous assignment metrics',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(
                        value: false,
                        icon: Icon(Icons.bar_chart_rounded, size: 18),
                        label: Text('Charts'),
                      ),
                      ButtonSegment(
                        value: true,
                        icon: Icon(Icons.table_rows_rounded, size: 18),
                        label: Text('Table'),
                      ),
                    ],
                    selected: {_showAsTable},
                    onSelectionChanged: (s) =>
                        setState(() => _showAsTable = s.first),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  IconButton.filledTonal(
                    tooltip: 'Refresh overview',
                    onPressed: _load,
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),
          Wrap(
            spacing: KwSpacing.md,
            runSpacing: KwSpacing.md,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(KwSpacing.lg),
                  child: KwFvrGauge(rate: data.fvr14d, size: 172),
                ),
              ),
              _KpiTile(
                title: 'First-Time Fix (FTF)',
                value: '${(data.firstTimeFix * 100).round()}%',
                subtitle: 'Resolved on initial technician visit',
                icon: Icons.verified_rounded,
              ),
              _KpiTile(
                title: 'Self-Fix Resolution',
                value: '${(data.selfFixResolution * 100).round()}%',
                subtitle: 'Safely resolved without rolling a truck',
                icon: Icons.build_circle_outlined,
              ),
              _KpiTile(
                title: 'Urgency Agreement',
                value: '${(data.urgencyAgreement * 100).round()}%',
                subtitle: 'Centre agreement with agent urgency class',
                icon: Icons.speed_rounded,
              ),
              _KpiTile(
                title: 'Override Rate',
                value: '${(data.overrideRate * 100).round()}%',
                subtitle: 'Assignments adjusted by centre ops',
                icon: Icons.swap_horiz_rounded,
              ),
              _KpiTile(
                title: 'Parts Ready at Visit',
                value: '${(data.partsReadyAtVisit * 100).round()}%',
                subtitle: 'Verified parts in van or counter before visit',
                icon: Icons.inventory_2_outlined,
              ),
              _KpiTile(
                title: 'Jobs / Tech-Day',
                value: data.jobsPerTechDay.toStringAsFixed(1),
                subtitle: 'Completed visits per active technician day',
                icon: Icons.engineering_outlined,
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),
          _MetricSeriesCard(
            title: 'Open Cases by Urgency Class',
            entries: data.openByClass,
            showAsTable: _showAsTable,
          ),
          const SizedBox(height: KwSpacing.md),
          _MetricSeriesCard(
            title: 'Self-Fix Consent Gate Funnel',
            entries: data.gateFunnel,
            showAsTable: _showAsTable,
          ),
        ],
      ),
    );
  }
}

class _KpiTile extends StatelessWidget {
  const _KpiTile({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String value;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return SizedBox(
      width: 240,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 20, color: cs.primary),
                  const SizedBox(width: KwSpacing.xs),
                  Expanded(
                    child: Text(
                      title,
                      style: theme.textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.sm),
              Text(
                value,
                style: KwTheme.monoStyle(
                  context,
                  fontSize: 30,
                  fontWeight: FontWeight.w800,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: KwSpacing.xxs),
              Text(
                subtitle,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricSeriesCard extends StatelessWidget {
  const _MetricSeriesCard({
    required this.title,
    required this.entries,
    required this.showAsTable,
  });

  final String title;
  final Map<String, int> entries;
  final bool showAsTable;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final maxVal = entries.values.fold<int>(1, (a, b) => a > b ? a : b);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            if (entries.isEmpty)
              const Text('No records yet.')
            else if (showAsTable)
              DataTable(
                columns: const [
                  DataColumn(label: Text('Category')),
                  DataColumn(label: Text('Count'), numeric: true),
                ],
                rows: [
                  for (final entry in entries.entries)
                    DataRow(
                      cells: [
                        DataCell(Text(entry.key)),
                        DataCell(Text('${entry.value}')),
                      ],
                    ),
                ],
              )
            else
              Column(
                children: [
                  for (final entry in entries.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                      child: Semantics(
                        label: '${entry.key}: ${entry.value}',
                        child: Row(
                          children: [
                            SizedBox(
                              width: 160,
                              child: Text(
                                entry.key,
                                style: theme.textTheme.bodyMedium,
                              ),
                            ),
                            Expanded(
                              child: ClipRRect(
                                borderRadius: KwShapes.radiusFull,
                                child: LinearProgressIndicator(
                                  minHeight: 12,
                                  value: (entry.value / maxVal).clamp(0.0, 1.0),
                                  backgroundColor: cs.surfaceContainerHighest,
                                ),
                              ),
                            ),
                            const SizedBox(width: KwSpacing.sm),
                            SizedBox(
                              width: 44,
                              child: Text(
                                '${entry.value}',
                                textAlign: TextAlign.end,
                                style: KwTheme.monoStyle(
                                  context,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
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
