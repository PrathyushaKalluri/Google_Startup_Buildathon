import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'brand_strings.dart';

/// Displays all warranty forwards and retailer installation handovers sent to
/// service centres, with status filters and prominent authority decline reasons.
class ForwardedRequestsScreen extends StatefulWidget {
  const ForwardedRequestsScreen({
    super.key,
    required this.api,
    required this.session,
    required this.brandStrings,
  });

  final KwApiClient api;
  final KwUserSession session;
  final BrandStrings brandStrings;

  @override
  State<ForwardedRequestsScreen> createState() =>
      _ForwardedRequestsScreenState();
}

class _ForwardedRequestsScreenState extends State<ForwardedRequestsScreen> {
  static const List<String> _statusBuckets = [
    'all',
    'received',
    'in_progress',
    'closed',
    'declined',
  ];

  final TextEditingController _searchController = TextEditingController();

  bool _loading = true;
  String? _errorMessage;
  List<TicketCard> _requests = const [];
  String _selectedStatus = 'all';
  String? _selectedBrand;

  @override
  void initState() {
    super.initState();
    _selectedBrand = widget.session.brandId;
    _loadRequests();
  }

  @override
  void didUpdateWidget(covariant ForwardedRequestsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.session.uid != widget.session.uid ||
        oldWidget.session.brandId != widget.session.brandId) {
      _selectedBrand = widget.session.brandId;
      _loadRequests();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    try {
      final page = await widget.api.listBrandRequests(brand: _selectedBrand);
      if (!mounted) return;
      setState(() {
        _requests = page.items;
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

  String _normalizeBucket(TicketCard ticket) {
    final s = ticket.status.toLowerCase();
    final res = (ticket.resolution ?? '').toLowerCase();
    final hasDeclineFlag = ticket.flags.any(
      (f) =>
          f.toLowerCase().contains('declin') ||
          f.toLowerCase().contains('no_authority') ||
          f.toLowerCase().contains('returned_to_brand'),
    );
    if (s == 'declined' ||
        s == 'returned_to_brand' ||
        s == 'rejected' ||
        hasDeclineFlag ||
        res.contains('no authority') ||
        res.contains('returned to brand') ||
        res.contains('declined')) {
      return 'declined';
    }
    if (s == 'closed' || s == 'resolved' || s == 'completed') {
      return 'closed';
    }
    if (s == 'in_progress' ||
        s == 'assigned' ||
        s == 'scheduled' ||
        s == 'en_route' ||
        s == 'visiting' ||
        s == 'quoted' ||
        s == 'parts_pending') {
      return 'in_progress';
    }
    return 'received';
  }

  String? _extractDeclineReason(TicketCard ticket) {
    if (_normalizeBucket(ticket) != 'declined') return null;
    final res = ticket.resolution?.trim();
    if (res != null && res.isNotEmpty) return res;
    for (final flag in ticket.flags) {
      if (flag.toLowerCase().contains('authority') ||
          flag.toLowerCase().contains('declin') ||
          flag.toLowerCase().contains('return')) {
        return flag;
      }
    }
    return 'Returned to brand: no authority';
  }

  String _centreLabel(String centreIdOrKey) {
    for (final c in KwAuthHelper.demoCentres) {
      if (c.key == centreIdOrKey || centreIdOrKey.contains(c.key)) {
        return '${c.name} (${c.key})';
      }
    }
    return centreIdOrKey;
  }

  List<TicketCard> get _filteredRequests {
    final query = _searchController.text.trim().toLowerCase();
    return _requests.where((ticket) {
      if (_selectedStatus != 'all' &&
          _normalizeBucket(ticket) != _selectedStatus) {
        return false;
      }
      if (query.isEmpty) return true;
      final declineReason = _extractDeclineReason(ticket) ?? '';
      final haystack = [
        ticket.id,
        ticket.centreId,
        ticket.status,
        ticket.trigger,
        ticket.complaintSummary,
        ticket.household.displayName,
        ticket.household.locality,
        ticket.appliance?.brand ?? '',
        ticket.appliance?.modelCode ?? '',
        ticket.appliance?.categoryCode ?? '',
        declineReason,
      ].join(' ').toLowerCase();
      return haystack.contains(query);
    }).toList();
  }

  int _countForBucket(String bucket) {
    if (bucket == 'all') return _requests.length;
    return _requests.where((t) => _normalizeBucket(t) == bucket).length;
  }

  String _statusLabel(String bucket) {
    final bs = widget.brandStrings;
    return switch (bucket) {
      'received' => bs.statusReceived,
      'in_progress' => bs.statusInProgress,
      'closed' => bs.statusClosed,
      'declined' => bs.statusDeclined,
      _ => bs.statusAll,
    };
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final bs = widget.brandStrings;
    final windowSize = KwWindowSize.of(context);
    final isPlatform = widget.session.role == KwRole.platform;

    return RefreshIndicator(
      onRefresh: _loadRequests,
      child: ListView(
        padding: EdgeInsets.all(windowSize.isCompact ? KwSpacing.md : KwSpacing.lg),
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      bs.requestsHeading,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xxs),
                    Text(
                      bs.requestsSubtitle,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: KwSpacing.sm),
              OutlinedButton.icon(
                onPressed: _loading ? null : _loadRequests,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(bs.refreshLabel),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),

          // Summary KPI strip
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.sm,
            children: [
              _SummaryPill(
                label: bs.statusAll,
                count: _countForBucket('all'),
                icon: Icons.list_alt_rounded,
                selected: _selectedStatus == 'all',
                onTap: () => setState(() => _selectedStatus = 'all'),
              ),
              _SummaryPill(
                label: bs.statusReceived,
                count: _countForBucket('received'),
                icon: Icons.mark_email_read_outlined,
                selected: _selectedStatus == 'received',
                onTap: () => setState(() => _selectedStatus = 'received'),
              ),
              _SummaryPill(
                label: bs.statusInProgress,
                count: _countForBucket('in_progress'),
                icon: Icons.engineering_outlined,
                selected: _selectedStatus == 'in_progress',
                onTap: () => setState(() => _selectedStatus = 'in_progress'),
              ),
              _SummaryPill(
                label: bs.statusClosed,
                count: _countForBucket('closed'),
                icon: Icons.check_circle_outline_rounded,
                selected: _selectedStatus == 'closed',
                onTap: () => setState(() => _selectedStatus = 'closed'),
              ),
              _SummaryPill(
                label: bs.statusDeclined,
                count: _countForBucket('declined'),
                icon: Icons.gpp_bad_outlined,
                isAlert: _countForBucket('declined') > 0,
                selected: _selectedStatus == 'declined',
                onTap: () => setState(() => _selectedStatus = 'declined'),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),

          // Search + optional platform brand filter
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 440, minWidth: 260),
                child: TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: bs.searchHint,
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            tooltip: 'Clear search',
                            onPressed: () {
                              _searchController.clear();
                              setState(() {});
                            },
                            icon: const Icon(Icons.close_rounded),
                          )
                        : null,
                  ),
                ),
              ),
              if (isPlatform)
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 220),
                  child: DropdownButtonFormField<String?>(
                    value: _selectedBrand,
                    decoration: const InputDecoration(
                      labelText: 'Filter by Brand',
                    ),
                    items: [
                      const DropdownMenuItem<String?>(
                        value: null,
                        child: Text('All Brands'),
                      ),
                      for (final b in KwAuthHelper.demoBrandKeys)
                        DropdownMenuItem<String?>(
                          value: b,
                          child: Text(b[0].toUpperCase() + b.substring(1)),
                        ),
                    ],
                    onChanged: (value) {
                      setState(() => _selectedBrand = value);
                      _loadRequests();
                    },
                  ),
                ),
            ],
          ),
          const SizedBox(height: KwSpacing.sm),

          // Status filter chips
          Wrap(
            spacing: KwSpacing.xs,
            runSpacing: KwSpacing.xs,
            children: [
              for (final bucket in _statusBuckets)
                FilterChip(
                  key: ValueKey('status-filter-$bucket'),
                  selected: _selectedStatus == bucket,
                  label: Text('${_statusLabel(bucket)} (${_countForBucket(bucket)})'),
                  onSelected: (_) => setState(() => _selectedStatus = bucket),
                ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),

          if (_loading)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(KwSpacing.lg),
                child: KwSkeletonLoader(lines: 5, height: 18),
              ),
            )
          else if (_errorMessage != null)
            KwErrorState(
              body: _errorMessage,
              onRetry: _loadRequests,
            )
          else if (_filteredRequests.isEmpty)
            KwEmptyState(
              icon: Icons.forward_to_inbox_outlined,
              title: bs.noRequestsTitle,
              body: bs.noRequestsBody,
              action: _selectedStatus != 'all' ||
                      _searchController.text.isNotEmpty
                  ? OutlinedButton(
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _selectedStatus = 'all');
                      },
                      child: const Text('Clear filters'),
                    )
                  : null,
            )
          else if (windowSize.isWide)
            _buildWideTable(context, _filteredRequests)
          else
            Column(
              children: [
                for (final ticket in _filteredRequests) ...[
                  _buildRequestCard(context, ticket),
                  const SizedBox(height: KwSpacing.sm),
                ],
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildWideTable(BuildContext context, List<TicketCard> items) {
    final theme = Theme.of(context);
    final bs = widget.brandStrings;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          showCheckboxColumn: false,
          headingRowHeight: 48,
          dataRowMinHeight: 72,
          dataRowMaxHeight: 112,
          columns: const [
            DataColumn(label: Text('Ticket & Channel')),
            DataColumn(label: Text('Service Centre')),
            DataColumn(label: Text('Appliance & Household')),
            DataColumn(label: Text('Status & Authority')),
            DataColumn(label: Text('Urgency')),
            DataColumn(label: Text('Updated (IST)')),
          ],
          rows: [
            for (final ticket in items)
              _buildTableRow(context, ticket, theme, bs),
          ],
        ),
      ),
    );
  }

  DataRow _buildTableRow(
    BuildContext context,
    TicketCard ticket,
    ThemeData theme,
    BrandStrings bs,
  ) {
    final bucket = _normalizeBucket(ticket);
    final declineReason = _extractDeclineReason(ticket);
    final updatedDt = DateTime.tryParse(ticket.updatedAt);

    return DataRow(
      onSelectChanged: (_) => _showDetailSheet(context, ticket),
      cells: [
        DataCell(
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                ticket.id,
                style: KwTheme.monoStyle(context, fontSize: 13),
              ),
              const SizedBox(height: 2),
              Text(
                ticket.trigger == 'retailer_handover'
                    ? 'Retailer Handover · ${ticket.jobType}'
                    : 'Brand Forward · ${ticket.entitlement}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        DataCell(
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 220),
            child: Text(
              _centreLabel(ticket.centreId),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
        DataCell(
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 260),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  ticket.appliance != null
                      ? '${ticket.appliance!.brand} ${ticket.appliance!.categoryCode} ${ticket.appliance!.modelCode ?? ''}'
                          .trim()
                      : 'Appliance pending',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  '${ticket.household.displayName} · ${ticket.household.locality}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  ticket.complaintSummary,
                  style: theme.textTheme.bodySmall,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
        DataCell(
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 280),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatusBadge(bucket: bucket, label: _statusLabel(bucket)),
                if (declineReason != null) ...[
                  const SizedBox(height: 4),
                  _DeclineReasonCallout(
                    label: bs.declineReasonLabel,
                    reason: declineReason,
                    compact: true,
                  ),
                ],
              ],
            ),
          ),
        ),
        DataCell(
          KwUrgencyChip(
            urgency: KwUrgencyClass.fromWire(ticket.urgencyClass),
            compact: true,
          ),
        ),
        DataCell(
          Text(
            updatedDt != null
                ? formatIstDateTime(updatedDt)
                : ticket.updatedAt,
            style: theme.textTheme.bodySmall,
          ),
        ),
      ],
    );
  }

  Widget _buildRequestCard(BuildContext context, TicketCard ticket) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final bs = widget.brandStrings;
    final bucket = _normalizeBucket(ticket);
    final declineReason = _extractDeclineReason(ticket);
    final updatedDt = DateTime.tryParse(ticket.updatedAt);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _showDetailSheet(context, ticket),
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      ticket.id,
                      style: KwTheme.monoStyle(context, fontSize: 13),
                    ),
                  ),
                  _StatusBadge(bucket: bucket, label: _statusLabel(bucket)),
                ],
              ),
              const SizedBox(height: KwSpacing.xs),
              Text(
                ticket.appliance != null
                    ? '${ticket.appliance!.brand} ${ticket.appliance!.categoryCode} ${ticket.appliance!.modelCode ?? ''}'
                        .trim()
                    : ticket.complaintSummary,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: KwSpacing.xxs),
              Text(
                ticket.complaintSummary,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: KwSpacing.xs),
              Wrap(
                spacing: KwSpacing.xs,
                runSpacing: KwSpacing.xs,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  KwUrgencyChip(
                    urgency: KwUrgencyClass.fromWire(ticket.urgencyClass),
                    compact: true,
                  ),
                  Chip(
                    label: Text(_centreLabel(ticket.centreId)),
                    visualDensity: VisualDensity.compact,
                  ),
                  Text(
                    '${ticket.household.displayName} · ${ticket.household.locality}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
              if (declineReason != null) ...[
                const SizedBox(height: KwSpacing.sm),
                _DeclineReasonCallout(
                  label: bs.declineReasonLabel,
                  reason: declineReason,
                ),
              ],
              if (updatedDt != null) ...[
                const SizedBox(height: KwSpacing.xs),
                Text(
                  formatIstDateTime(updatedDt),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: cs.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  void _showDetailSheet(BuildContext context, TicketCard ticket) {
    final theme = Theme.of(context);
    final bs = widget.brandStrings;
    final bucket = _normalizeBucket(ticket);
    final declineReason = _extractDeclineReason(ticket);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(KwSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        ticket.id,
                        style: KwTheme.monoStyle(context, fontSize: 16),
                      ),
                    ),
                    _StatusBadge(bucket: bucket, label: _statusLabel(bucket)),
                  ],
                ),
                const SizedBox(height: KwSpacing.sm),
                Text(
                  ticket.complaintSummary,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.sm),
                Text('Centre: ${_centreLabel(ticket.centreId)}'),
                Text(
                  'Household: ${ticket.household.displayName} (${ticket.household.locality}, ${ticket.household.pincode})',
                ),
                if (ticket.appliance != null)
                  Text(
                    'Appliance: ${ticket.appliance!.brand} · ${ticket.appliance!.categoryCode} · ${ticket.appliance!.modelCode ?? 'Unknown model'} (${ticket.appliance!.serialMasked ?? 'Unverified serial'})',
                  ),
                Text('Trigger: ${ticket.trigger} · Entitlement: ${ticket.entitlement}'),
                if (declineReason != null) ...[
                  const SizedBox(height: KwSpacing.md),
                  _DeclineReasonCallout(
                    label: bs.declineReasonLabel,
                    reason: declineReason,
                  ),
                ],
                const SizedBox(height: KwSpacing.md),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(KwStrings.of(context).closeLabel),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SummaryPill extends StatelessWidget {
  const _SummaryPill({
    required this.label,
    required this.count,
    required this.icon,
    required this.selected,
    required this.onTap,
    this.isAlert = false,
  });

  final String label;
  final int count;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  final bool isAlert;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    final bg = isAlert
        ? kw.declined.container
        : selected
            ? cs.primaryContainer
            : cs.surfaceContainerLow;
    final fg = isAlert
        ? kw.declined.onContainer
        : selected
            ? cs.onPrimaryContainer
            : cs.onSurface;

    return Semantics(
      button: true,
      selected: selected,
      label: '$label: $count',
      child: Material(
        color: bg,
        shape: KwShapes.rounded(
          KwShapes.medium,
          side: BorderSide(
            color: selected
                ? cs.primary
                : isAlert
                    ? kw.declined.accent
                    : cs.outlineVariant,
            width: selected || isAlert ? 1.5 : 1,
          ),
        ),
        child: InkWell(
          borderRadius: KwShapes.radiusMedium,
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.md,
              vertical: KwSpacing.sm,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 18, color: fg),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  label,
                  style: theme.textTheme.labelLarge?.copyWith(color: fg),
                ),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  '$count',
                  style: KwTheme.monoStyle(
                    context,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    color: fg,
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

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.bucket,
    required this.label,
  });

  final String bucket;
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;

    final (role, icon) = switch (bucket) {
      'declined' => (kw.declined, Icons.cancel_outlined),
      'closed' => (kw.verified, Icons.check_circle_outline_rounded),
      'in_progress' => (kw.urgent, Icons.autorenew_rounded),
      _ => (kw.standard, Icons.inbox_outlined),
    };

    return Semantics(
      label: 'Status: $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: role.container,
          borderRadius: KwShapes.radiusFull,
          border: Border.all(color: role.accent.withValues(alpha: 0.5)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15, color: role.onContainer),
            const SizedBox(width: 4),
            Text(
              label,
              style: theme.textTheme.labelMedium?.copyWith(
                color: role.onContainer,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DeclineReasonCallout extends StatelessWidget {
  const _DeclineReasonCallout({
    required this.label,
    required this.reason,
    this.compact = false,
  });

  final String label;
  final String reason;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;

    return Semantics(
      liveRegion: true,
      label: '$label: $reason',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? KwSpacing.xs : KwSpacing.sm,
          vertical: compact ? 4 : KwSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: kw.declined.container,
          borderRadius: KwShapes.radiusSmall,
          border: Border.all(color: kw.declined.accent, width: 1.2),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.gpp_bad_rounded,
              size: compact ? 15 : 18,
              color: kw.declined.onContainer,
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                reason,
                maxLines: compact ? 2 : 4,
                overflow: TextOverflow.ellipsis,
                style: (compact
                        ? theme.textTheme.labelSmall
                        : theme.textTheme.bodySmall)
                    ?.copyWith(
                  color: kw.declined.onContainer,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
