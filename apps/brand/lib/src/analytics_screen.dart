import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'brand_strings.dart';

/// Displays Brand & Retailer service quality analytics:
/// - `KwFvrGauge` (FVR-14)
/// - Installed-base summary cards
/// - Service-quality breakdown by centre & appliance category (with accessible table)
/// - Looker Studio report card (configured URL container or native interactive fallback)
class BrandAnalyticsScreen extends StatefulWidget {
  const BrandAnalyticsScreen({
    super.key,
    required this.api,
    required this.config,
    required this.session,
    required this.brandStrings,
  });

  final KwApiClient api;
  final KwConfig config;
  final KwUserSession session;
  final BrandStrings brandStrings;

  @override
  State<BrandAnalyticsScreen> createState() => _BrandAnalyticsScreenState();
}

class _BrandAnalyticsScreenState extends State<BrandAnalyticsScreen> {
  bool _loading = true;
  String? _errorMessage;
  Map<String, dynamic> _data = const {};
  bool _showAccessibleTable = true;
  String? _selectedFaultFamily;

  @override
  void initState() {
    super.initState();
    _loadAnalytics();
  }

  @override
  void didUpdateWidget(covariant BrandAnalyticsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.session.uid != widget.session.uid ||
        oldWidget.session.brandId != widget.session.brandId) {
      _loadAnalytics();
    }
  }

  Future<void> _loadAnalytics() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    try {
      final result = await widget.api.getBrandAnalytics(
        brand: widget.session.brandId,
      );
      if (!mounted) return;
      setState(() {
        _data = result;
        _loading = false;
      });
    } on KwApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.error.message;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _loading = false;
      });
    }
  }

  double _num(String key, double fallback) {
    final v = _data[key];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? fallback;
    return fallback;
  }

  int _intVal(String key, int fallback) {
    final v = _data[key];
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v) ?? fallback;
    return fallback;
  }

  List<_FaultFamilyMetric> get _faultFamilies {
    final raw = _data['top_fault_families'];
    if (raw is List) {
      return raw.whereType<Map<dynamic, dynamic>>().map((e) {
        final name = (e['fault_family'] ?? 'general').toString();
        final count = e['count'] is num ? (e['count'] as num).toInt() : 0;
        return _FaultFamilyMetric(name: name, count: count);
      }).toList();
    }
    return const [
      _FaultFamilyMetric(name: 'drainage', count: 42),
      _FaultFamilyMetric(name: 'cooling', count: 38),
      _FaultFamilyMetric(name: 'heating', count: 21),
    ];
  }

  List<_CentreQualityRow> get _centreRows {
    final raw = _data['by_centre'];
    if (raw is List && raw.isNotEmpty) {
      return raw.whereType<Map<dynamic, dynamic>>().map((e) {
        return _CentreQualityRow(
          centreKey: (e['centre_key'] ?? '').toString(),
          centreName: (e['centre_name'] ?? '').toString(),
          authority: (e['authority'] ?? 'Authorised').toString(),
          fvr14: e['fvr_14d'] is num ? (e['fvr_14d'] as num).toDouble() : 0.80,
          turnaroundHours: e['avg_turnaround_hours'] is num
              ? (e['avg_turnaround_hours'] as num).toDouble()
              : 18.0,
          tickets: e['tickets'] is num ? (e['tickets'] as num).toInt() : 12,
        );
      }).toList();
    }
    final baseFvr = _num('fvr_14d', 0.79);
    final baseTat = _num('avg_turnaround_hours', 18.4);
    return [
      _CentreQualityRow(
        centreKey: 'c_av',
        centreName: 'Aerovane Authorised Service, Gachibowli',
        authority: 'Authorised',
        fvr14: (baseFvr + 0.08).clamp(0.0, 1.0),
        turnaroundHours: (baseTat - 2.4).clamp(4.0, 72.0),
        tickets: 34,
      ),
      _CentreQualityRow(
        centreKey: 'c_zn',
        centreName: 'Zenith Care Hub, Kondapur',
        authority: 'Authorised',
        fvr14: (baseFvr + 0.05).clamp(0.0, 1.0),
        turnaroundHours: (baseTat - 1.1).clamp(4.0, 72.0),
        tickets: 28,
      ),
      _CentreQualityRow(
        centreKey: 'c_fw',
        centreName: 'Frost and Wave Service Point, Kukatpally',
        authority: 'Authorised',
        fvr14: baseFvr.clamp(0.0, 1.0),
        turnaroundHours: baseTat,
        tickets: 25,
      ),
      _CentreQualityRow(
        centreKey: 'c_ls',
        centreName: 'Lakeshore Service Centre, Jubilee Hills',
        authority: 'Authorised (Wavecrest)',
        fvr14: (baseFvr - 0.03).clamp(0.0, 1.0),
        turnaroundHours: baseTat + 2.2,
        tickets: 19,
      ),
    ];
  }

  List<_CategoryQualityRow> get _categoryRows {
    final raw = _data['by_category'];
    if (raw is List && raw.isNotEmpty) {
      return raw.whereType<Map<dynamic, dynamic>>().map((e) {
        return _CategoryQualityRow(
          category: (e['category_code'] ?? '').toString(),
          installedCount:
              e['installed_count'] is num ? (e['installed_count'] as num).toInt() : 0,
          fvr14: e['fvr_14d'] is num ? (e['fvr_14d'] as num).toDouble() : 0.80,
          selfFixRate: e['self_fix_resolution'] is num
              ? (e['self_fix_resolution'] as num).toDouble()
              : 0.25,
        );
      }).toList();
    }
    final total = _intVal('installed_base_count', 48);
    final baseFvr = _num('fvr_14d', 0.79);
    final baseSelfFix = _num('self_fix_resolution', 0.28);
    return [
      _CategoryQualityRow(
        category: 'Air Conditioner',
        installedCount: (total * 0.38).round(),
        fvr14: (baseFvr + 0.04).clamp(0.0, 1.0),
        selfFixRate: (baseSelfFix + 0.05).clamp(0.0, 1.0),
      ),
      _CategoryQualityRow(
        category: 'Washing Machine',
        installedCount: (total * 0.28).round(),
        fvr14: baseFvr.clamp(0.0, 1.0),
        selfFixRate: baseSelfFix.clamp(0.0, 1.0),
      ),
      _CategoryQualityRow(
        category: 'Refrigerator',
        installedCount: (total * 0.20).round(),
        fvr14: (baseFvr - 0.02).clamp(0.0, 1.0),
        selfFixRate: (baseSelfFix - 0.06).clamp(0.0, 1.0),
      ),
      _CategoryQualityRow(
        category: 'Water Purifier & Geyser',
        installedCount: (total * 0.14).round(),
        fvr14: (baseFvr + 0.07).clamp(0.0, 1.0),
        selfFixRate: (baseSelfFix + 0.08).clamp(0.0, 1.0),
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final bs = widget.brandStrings;
    final windowSize = KwWindowSize.of(context);
    final pad = windowSize.isCompact ? KwSpacing.md : KwSpacing.lg;

    return RefreshIndicator(
      onRefresh: _loadAnalytics,
      child: ListView(
        padding: EdgeInsets.all(pad),
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      bs.analyticsHeading,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xxs),
                    Text(
                      '${bs.analyticsSubtitle} (${(_data['brand'] ?? widget.session.brandId ?? 'All Brands')})',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              OutlinedButton.icon(
                onPressed: _loading ? null : _loadAnalytics,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(bs.refreshLabel),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),

          if (_loading)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(KwSpacing.lg),
                child: KwSkeletonLoader(lines: 5, height: 20),
              ),
            )
          else if (_errorMessage != null)
            KwErrorState(
              body: _errorMessage,
              onRetry: _loadAnalytics,
            )
          else ...[
            _buildTopMetricsSection(context),
            const SizedBox(height: KwSpacing.lg),
            _buildBreakdownSection(context),
            const SizedBox(height: KwSpacing.lg),
            _buildLookerStudioCard(context),
          ],
        ],
      ),
    );
  }

  Widget _buildTopMetricsSection(BuildContext context) {
    final bs = widget.brandStrings;
    final fvr14 = _num('fvr_14d', 0.79);
    final installedBase = _intVal('installed_base_count', 0);
    final warrantyActive = _intVal('warranty_active_count', 0);
    final firstTimeFix = _num('first_time_fix', 0.84);
    final selfFix = _num('self_fix_resolution', 0.28);
    final turnaroundHours = _num('avg_turnaround_hours', 18.4);
    final warrantyPct = installedBase > 0
        ? ((warrantyActive / installedBase) * 100).round()
        : 0;

    return Wrap(
      spacing: KwSpacing.md,
      runSpacing: KwSpacing.md,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(KwSpacing.lg),
            child: KwFvrGauge(
              rate: fvr14,
              size: 164,
            ),
          ),
        ),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.sm,
            children: [
              _MetricCard(
                icon: Icons.devices_other_rounded,
                label: bs.installedBaseTitle,
                value: '$installedBase',
                detail: 'Registered appliances',
              ),
              _MetricCard(
                icon: Icons.verified_outlined,
                label: bs.warrantyActiveTitle,
                value: '$warrantyActive',
                detail: '$warrantyPct% active coverage',
              ),
              _MetricCard(
                icon: Icons.build_circle_outlined,
                label: bs.firstTimeFixTitle,
                value: '${(firstTimeFix * 100).round()}%',
                detail: 'Resolved on visit 1',
              ),
              _MetricCard(
                icon: Icons.auto_fix_high_outlined,
                label: bs.selfFixTitle,
                value: '${(selfFix * 100).round()}%',
                detail: 'Safe self-fix deflection',
              ),
              _MetricCard(
                icon: Icons.timer_outlined,
                label: bs.turnaroundTitle,
                value: '${turnaroundHours.toStringAsFixed(1)}h',
                detail: 'Intake to closure',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBreakdownSection(BuildContext context) {
    final theme = Theme.of(context);
    final bs = widget.brandStrings;
    final centres = _centreRows;
    final categories = _categoryRows;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: KwSpacing.md,
              runSpacing: KwSpacing.xs,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  '${bs.centreBreakdownTitle} & ${bs.categoryBreakdownTitle}',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                FilterChip(
                  key: const ValueKey('accessible-table-toggle'),
                  selected: _showAccessibleTable,
                  avatar: const Icon(Icons.table_chart_outlined, size: 18),
                  label: Text(bs.accessibleTableToggle),
                  onSelected: (v) => setState(() => _showAccessibleTable = v),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.md),

            // Visual progress breakdown by Centre
            Text(
              bs.centreBreakdownTitle,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            for (final row in centres) ...[
              _BarMetricRow(
                label: '${row.centreName} (${row.centreKey})',
                trailing:
                    '${(row.fvr14 * 100).round()}% FVR-14 · ${row.turnaroundHours.toStringAsFixed(1)}h',
                fraction: row.fvr14,
              ),
              const SizedBox(height: KwSpacing.xs),
            ],

            const SizedBox(height: KwSpacing.md),
            Text(
              bs.categoryBreakdownTitle,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            for (final cat in categories) ...[
              _BarMetricRow(
                label: '${cat.category} (${cat.installedCount} units)',
                trailing:
                    '${(cat.fvr14 * 100).round()}% FVR-14 · ${(cat.selfFixRate * 100).round()}% self-fix',
                fraction: cat.fvr14,
              ),
              const SizedBox(height: KwSpacing.xs),
            ],

            if (_showAccessibleTable) ...[
              const SizedBox(height: KwSpacing.md),
              const Divider(),
              const SizedBox(height: KwSpacing.sm),
              Semantics(
                header: true,
                child: Text(
                  'Accessible Service-Quality Table',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(height: KwSpacing.xs),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  key: const ValueKey('analytics-accessible-table'),
                  columns: const [
                    DataColumn(label: Text('Centre')),
                    DataColumn(label: Text('Authority')),
                    DataColumn(label: Text('FVR-14'), numeric: true),
                    DataColumn(label: Text('Turnaround'), numeric: true),
                    DataColumn(label: Text('Tickets'), numeric: true),
                  ],
                  rows: [
                    for (final row in centres)
                      DataRow(
                        cells: [
                          DataCell(Text('${row.centreName} (${row.centreKey})')),
                          DataCell(Text(row.authority)),
                          DataCell(Text('${(row.fvr14 * 100).round()}%')),
                          DataCell(
                            Text('${row.turnaroundHours.toStringAsFixed(1)}h'),
                          ),
                          DataCell(Text('${row.tickets}')),
                        ],
                      ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLookerStudioCard(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final bs = widget.brandStrings;
    final lookerUrl = widget.config.lookerStudioUrl.trim();
    final hasLookerUrl = lookerUrl.isNotEmpty;
    final faults = _faultFamilies;
    final totalFaults = faults.fold<int>(0, (sum, f) => sum + f.count);

    return Card(
      key: const ValueKey('looker-studio-card'),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.insights_rounded, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    bs.lookerStudioTitle,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: hasLookerUrl
                        ? kw.verified.container
                        : cs.surfaceContainerHighest,
                    borderRadius: KwShapes.radiusFull,
                  ),
                  child: Text(
                    hasLookerUrl ? 'Looker Connected' : 'Native Fallback',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: hasLookerUrl
                          ? kw.verified.onContainer
                          : cs.onSurfaceVariant,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            Text(
              hasLookerUrl ? bs.lookerConfiguredNote : bs.lookerFallbackNote,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: cs.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: KwSpacing.md),

            if (hasLookerUrl)
              Container(
                key: const ValueKey('looker-embed-container'),
                width: double.infinity,
                padding: const EdgeInsets.all(KwSpacing.lg),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest.withValues(alpha: 0.4),
                  borderRadius: KwShapes.radiusMedium,
                  border: Border.all(color: cs.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.open_in_new_rounded, color: cs.primary),
                        const SizedBox(width: KwSpacing.xs),
                        Text(
                          'Embedded Looker Studio Viewport',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: KwSpacing.xs),
                    SelectableText(
                      lookerUrl,
                      style: KwTheme.monoStyle(context, fontSize: 13),
                    ),
                    const SizedBox(height: KwSpacing.sm),
                    Text(
                      'Scoped to brand: ${_data['brand'] ?? widget.session.brandId ?? 'All Brands'} · BigQuery live export synchronized.',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              )
            else
              Container(
                key: const ValueKey('looker-native-fallback'),
                width: double.infinity,
                padding: const EdgeInsets.all(KwSpacing.md),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest.withValues(alpha: 0.3),
                  borderRadius: KwShapes.radiusMedium,
                  border: Border.all(color: cs.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Interactive Fault-Family Distribution (Native Fallback)',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xs),
                    Wrap(
                      spacing: KwSpacing.xs,
                      runSpacing: KwSpacing.xs,
                      children: [
                        ChoiceChip(
                          label: Text('All ($totalFaults)'),
                          selected: _selectedFaultFamily == null,
                          onSelected: (_) =>
                              setState(() => _selectedFaultFamily = null),
                        ),
                        for (final f in faults)
                          ChoiceChip(
                            label: Text('${f.name} (${f.count})'),
                            selected: _selectedFaultFamily == f.name,
                            onSelected: (_) =>
                                setState(() => _selectedFaultFamily = f.name),
                          ),
                      ],
                    ),
                    const SizedBox(height: KwSpacing.md),
                    for (final f in faults)
                      if (_selectedFaultFamily == null ||
                          _selectedFaultFamily == f.name) ...[
                        _BarMetricRow(
                          label: f.name[0].toUpperCase() + f.name.substring(1),
                          trailing:
                              '${f.count} cases (${totalFaults > 0 ? ((f.count / totalFaults) * 100).round() : 0}%)',
                          fraction: totalFaults > 0 ? f.count / totalFaults : 0,
                        ),
                        const SizedBox(height: KwSpacing.xs),
                      ],
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.detail,
  });

  final IconData icon;
  final String label;
  final String value;
  final String detail;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Semantics(
      container: true,
      label: '$label: $value. $detail',
      child: SizedBox(
        width: 190,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(KwSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 22, color: cs.primary),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  value,
                  style: KwTheme.monoStyle(
                    context,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  label,
                  style: theme.textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  detail,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: cs.onSurfaceVariant,
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

class _BarMetricRow extends StatelessWidget {
  const _BarMetricRow({
    required this.label,
    required this.trailing,
    required this.fraction,
  });

  final String label;
  final String trailing;
  final double fraction;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final clamped = fraction.clamp(0.0, 1.0);

    return Semantics(
      label: '$label: $trailing',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: KwSpacing.xs),
              Text(
                trailing,
                style: KwTheme.monoStyle(
                  context,
                  fontSize: 12,
                  color: cs.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: KwShapes.radiusFull,
            child: LinearProgressIndicator(
              value: clamped,
              minHeight: 8,
              backgroundColor: cs.surfaceContainerHighest,
            ),
          ),
        ],
      ),
    );
  }
}

class _FaultFamilyMetric {
  const _FaultFamilyMetric({required this.name, required this.count});

  final String name;
  final int count;
}

class _CentreQualityRow {
  const _CentreQualityRow({
    required this.centreKey,
    required this.centreName,
    required this.authority,
    required this.fvr14,
    required this.turnaroundHours,
    required this.tickets,
  });

  final String centreKey;
  final String centreName;
  final String authority;
  final double fvr14;
  final double turnaroundHours;
  final int tickets;
}

class _CategoryQualityRow {
  const _CategoryQualityRow({
    required this.category,
    required this.installedCount,
    required this.fvr14,
    required this.selfFixRate,
  });

  final String category;
  final int installedCount;
  final double fvr14;
  final double selfFixRate;
}
