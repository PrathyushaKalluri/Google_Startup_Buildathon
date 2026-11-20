import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Operations Data Tables screen with tabs for Stock, Prices, Safe-Fix Library
/// (including overdue `review_due` badges), and Overrides ("What the agent
/// learned from you"), with sorting, filtering, and CSV copy/preview.
class OperationsScreen extends StatefulWidget {
  const OperationsScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<OperationsScreen> createState() => _OperationsScreenState();
}

class _OperationsScreenState extends State<OperationsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final TextEditingController _filterController = TextEditingController();

  List<Map<String, dynamic>> _stock = const [];
  List<Map<String, dynamic>> _prices = const [];
  List<SafeFixEntry> _safeFixes = const [];
  List<Map<String, dynamic>> _overrides = const [];

  bool _loading = true;
  bool _sortAscending = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _filterController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final ctrl = widget.controller;
      final isPlatform = ctrl.session?.role == KwRole.platform;
      final cid = isPlatform ? null : ctrl.activeCentreId;
      final ckey = isPlatform ? null : ctrl.activeCentreKey;

      final results = await Future.wait<dynamic>([
        ctrl.apiClient.getCentreStock(centreId: cid, centreKey: ckey),
        ctrl.apiClient.getCentrePrices(centreId: cid, centreKey: ckey),
        ctrl.apiClient.listSafeFixes(),
        ctrl.apiClient.getCentreOverrides(centreId: cid, centreKey: ckey),
      ]);

      if (mounted) {
        setState(() {
          _stock = (results[0] as PagedList<Map<String, dynamic>>).items;
          _prices = (results[1] as PagedList<Map<String, dynamic>>).items;
          _safeFixes = (results[2] as PagedList<SafeFixEntry>).items;
          _overrides = (results[3] as PagedList<Map<String, dynamic>>).items;
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

  Future<void> _exportCurrentTabCsv() async {
    final csv = _buildCsvForTab(_tabController.index);
    await Clipboard.setData(ClipboardData(text: csv));
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('CSV Export (Copied to clipboard)'),
        content: SizedBox(
          width: 560,
          child: SingleChildScrollView(
            child: SelectableText(
              csv,
              style: KwTheme.monoStyle(ctx, fontSize: 12),
            ),
          ),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  String _buildCsvForTab(int tabIndex) {
    final buf = StringBuffer();
    switch (tabIndex) {
      case 0:
        buf.writeln('part_no,name,qty_on_hand,location');
        for (final row in _stock) {
          buf.writeln(
            '${row['part_no'] ?? ''},"${row['name'] ?? ''}",${row['qty_on_hand'] ?? row['quantity'] ?? 0},${row['location'] ?? 'centre'}',
          );
        }
      case 1:
        buf.writeln('code,description,amount_paise,category');
        for (final row in _prices) {
          buf.writeln(
            '${row['code'] ?? ''},"${row['description'] ?? row['name'] ?? ''}",${row['amount_paise'] ?? row['price_paise'] ?? 0},${row['category'] ?? ''}',
          );
        }
      case 2:
        buf.writeln('code,title,category_code,status,est_minutes,reviewer');
        for (final fix in _safeFixes) {
          buf.writeln(
            '${fix.code},"${fix.title}",${fix.categoryCode},${fix.status},${fix.estMinutes},${fix.reviewerName}',
          );
        }
      default:
        buf.writeln('id,kind,ticket_id,reason,at');
        for (final row in _overrides) {
          buf.writeln(
            '${row['id'] ?? ''},${row['kind'] ?? row['type'] ?? ''},${row['ticket_id'] ?? ''},"${row['reason'] ?? ''}",${row['at'] ?? row['created_at'] ?? ''}',
          );
        }
    }
    return buf.toString();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            KwSpacing.md,
            KwSpacing.sm,
            KwSpacing.md,
            0,
          ),
          child: Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.xs,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SizedBox(
                width: 300,
                child: TextField(
                  controller: _filterController,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: 'Filter table rows…',
                    prefixIcon: Icon(Icons.search_rounded),
                    isDense: true,
                  ),
                ),
              ),
              Wrap(
                spacing: KwSpacing.xs,
                children: [
                  OutlinedButton.icon(
                    onPressed: () =>
                        setState(() => _sortAscending = !_sortAscending),
                    icon: Icon(
                      _sortAscending
                          ? Icons.arrow_upward_rounded
                          : Icons.arrow_downward_rounded,
                      size: 18,
                    ),
                    label: Text(_sortAscending ? 'Sort A→Z' : 'Sort Z→A'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: _exportCurrentTabCsv,
                    icon: const Icon(Icons.download_rounded, size: 18),
                    label: const Text('Export CSV'),
                  ),
                  IconButton.filledTonal(
                    tooltip: 'Refresh tables',
                    onPressed: _load,
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ],
              ),
            ],
          ),
        ),
        TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            Tab(text: 'Stock (${_stock.length})'),
            Tab(text: 'Prices (${_prices.length})'),
            Tab(text: 'Safe-Fix Library (${_safeFixes.length})'),
            Tab(text: 'Overrides · Agent Learning (${_overrides.length})'),
          ],
        ),
        Expanded(
          child: _loading
              ? const Padding(
                  padding: EdgeInsets.all(KwSpacing.lg),
                  child: KwSkeletonLoader(lines: 8),
                )
              : _error != null
                  ? KwErrorState(
                      title: 'Could not load operations data',
                      body: _error,
                      onRetry: _load,
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildMapTable(
                          context,
                          rows: _stock,
                          columns: const [
                            ('Part No', 'part_no'),
                            ('Name', 'name'),
                            ('On Hand', 'qty_on_hand'),
                            ('Location', 'location'),
                          ],
                          emptyTitle: 'No stock items',
                        ),
                        _buildMapTable(
                          context,
                          rows: _prices,
                          columns: const [
                            ('Code', 'code'),
                            ('Description', 'description'),
                            ('Amount (INR)', 'amount_paise'),
                            ('Category', 'category'),
                          ],
                          formatMoneyKey: 'amount_paise',
                          emptyTitle: 'No price rows',
                        ),
                        _buildSafeFixTab(context, cs),
                        _buildOverridesTab(context, cs),
                      ],
                    ),
        ),
      ],
    );
  }

  Widget _buildMapTable(
    BuildContext context, {
    required List<Map<String, dynamic>> rows,
    required List<(String, String)> columns,
    String? formatMoneyKey,
    required String emptyTitle,
  }) {
    final q = _filterController.text.trim().toLowerCase();
    final filtered = rows.where((row) {
      if (q.isEmpty) return true;
      return row.values.any((v) => '$v'.toLowerCase().contains(q));
    }).toList();

    filtered.sort((a, b) {
      final firstKey = columns.first.$2;
      final cmp = '${a[firstKey] ?? ''}'.compareTo('${b[firstKey] ?? ''}');
      return _sortAscending ? cmp : -cmp;
    });

    if (filtered.isEmpty) {
      return KwEmptyState(title: emptyTitle);
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(KwSpacing.md),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: [
            for (final col in columns) DataColumn(label: Text(col.$1)),
          ],
          rows: [
            for (final row in filtered)
              DataRow(
                cells: [
                  for (final col in columns)
                    DataCell(
                      Text(
                        col.$2 == formatMoneyKey
                            ? formatInrPaise(
                                (row[col.$2] as num?)?.toInt() ??
                                    (row['price_paise'] as num?)?.toInt() ??
                                    0,
                              )
                            : '${row[col.$2] ?? row['quantity'] ?? row['name'] ?? '—'}',
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSafeFixTab(BuildContext context, ColorScheme cs) {
    final q = _filterController.text.trim().toLowerCase();
    final kw = Theme.of(context).kwColors;
    final filtered = _safeFixes.where((fix) {
      if (q.isEmpty) return true;
      return '${fix.code} ${fix.title} ${fix.categoryCode} ${fix.status}'
          .toLowerCase()
          .contains(q);
    }).toList();

    filtered.sort((a, b) {
      final cmp = a.title.compareTo(b.title);
      return _sortAscending ? cmp : -cmp;
    });

    if (filtered.isEmpty) {
      return const KwEmptyState(title: 'No safe-fix entries found');
    }

    return ListView.separated(
      padding: const EdgeInsets.all(KwSpacing.md),
      itemCount: filtered.length,
      separatorBuilder: (_, __) => const SizedBox(height: KwSpacing.xs),
      itemBuilder: (context, index) {
        final fix = filtered[index];
        final isReviewDue = fix.status.toLowerCase() == 'review_due';
        return Card(
          child: ListTile(
            title: Wrap(
              spacing: KwSpacing.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  fix.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                Text(fix.code, style: KwTheme.monoStyle(context, fontSize: 12)),
                if (isReviewDue)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: kw.needsChecking.container,
                      borderRadius: KwShapes.radiusSmall,
                    ),
                    child: Text(
                      'OVERDUE REVIEW_DUE',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: kw.needsChecking.onContainer,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
              ],
            ),
            subtitle: Text(
              '${fix.categoryCode} · ${fix.stepCount} steps · ~${fix.estMinutes} min · Reviewer: ${fix.reviewerName}',
            ),
            trailing: Chip(label: Text(fix.status)),
          ),
        );
      },
    );
  }

  Widget _buildOverridesTab(BuildContext context, ColorScheme cs) {
    final q = _filterController.text.trim().toLowerCase();
    final filtered = _overrides.where((row) {
      if (q.isEmpty) return true;
      return row.values.any((v) => '$v'.toLowerCase().contains(q));
    }).toList();

    if (filtered.isEmpty) {
      return const KwEmptyState(
        icon: Icons.psychology_alt_outlined,
        title: 'What the agent learned from you',
        body:
            'Urgency reclassifications and technician reassignments appear here so you can audit how the agent adapts.',
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(KwSpacing.md),
      itemCount: filtered.length,
      separatorBuilder: (_, __) => const SizedBox(height: KwSpacing.xs),
      itemBuilder: (context, index) {
        final row = filtered[index];
        return Card(
          child: ListTile(
            leading: Icon(Icons.auto_awesome_rounded, color: cs.primary),
            title: Text(
              '${row['kind'] ?? row['type'] ?? 'Override'} · Ticket ${row['ticket_id'] ?? ''}',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            subtitle: Text(row['reason']?.toString() ?? 'No reason recorded'),
            trailing: Text(
              row['at']?.toString() ?? row['created_at']?.toString() ?? '',
              style: KwTheme.monoStyle(context, fontSize: 11),
            ),
          ),
        );
      },
    );
  }
}
