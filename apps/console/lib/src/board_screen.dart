import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'case_detail_pane.dart';
import 'console_state.dart';

/// Adaptive Case Board & List-Detail screen.
///
/// Orders tickets strictly `safety` -> `urgent` -> `standard` -> `planned`,
/// then earliest `needed_by`. Includes status/urgency/trigger filters, search,
/// and a live activity strip powered by [LiveFeedRepository].
class BoardScreen extends StatefulWidget {
  const BoardScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends State<BoardScreen> {
  final TextEditingController _searchController = TextEditingController();
  String? _urgencyFilter;
  String? _statusFilter;
  String? _triggerFilter;
  bool _showingMobileDetail = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<TicketCard> _filteredTickets(List<TicketCard> all) {
    final query = _searchController.text.trim().toLowerCase();
    final filtered = all.where((ticket) {
      if (_urgencyFilter != null &&
          ticket.urgencyClass.toLowerCase() != _urgencyFilter) {
        return false;
      }
      if (_statusFilter != null &&
          ticket.status.toLowerCase() != _statusFilter) {
        return false;
      }
      if (_triggerFilter != null &&
          ticket.trigger.toLowerCase() != _triggerFilter) {
        return false;
      }
      if (query.isNotEmpty) {
        final haystack = [
          ticket.id,
          ticket.household.displayName,
          ticket.household.locality,
          ticket.complaintSummary,
          ticket.appliance?.brand ?? '',
          ticket.appliance?.categoryCode ?? '',
          ticket.appliance?.modelCode ?? '',
        ].join(' ').toLowerCase();
        if (!haystack.contains(query)) return false;
      }
      return true;
    }).toList();

    return ConsoleController.sortTickets(filtered);
  }

  void _selectTicket(TicketCard card, bool isWide) {
    widget.controller.selectTicket(card.id);
    if (!isWide) {
      setState(() => _showingMobileDetail = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = widget.controller;
    final size = KwWindowSize.of(context);
    final isWide = size.isWide;
    final visibleTickets = _filteredTickets(ctrl.tickets);

    if (!isWide && _showingMobileDetail) {
      return Column(
        children: [
          Material(
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            child: Row(
              children: [
                IconButton(
                  tooltip: 'Back to case list',
                  onPressed: () =>
                      setState(() => _showingMobileDetail = false),
                  icon: const Icon(Icons.arrow_back_rounded),
                ),
                Text(
                  'Case Detail',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: CaseDetailPane(controller: ctrl),
          ),
        ],
      );
    }

    return Column(
      children: [
        _LiveActivityStrip(
          events: ctrl.liveFeed,
          onSelectTicket: (ticketId) {
            ctrl.selectTicket(ticketId);
            if (!isWide) setState(() => _showingMobileDetail = true);
          },
        ),
        const Divider(height: 1),
        Expanded(
          child: isWide
              ? Row(
                  children: [
                    SizedBox(
                      width: size.isLarge ? 430 : 370,
                      child: _buildListPane(context, visibleTickets, true),
                    ),
                    const VerticalDivider(width: 1),
                    Expanded(
                      child: CaseDetailPane(controller: ctrl),
                    ),
                  ],
                )
              : _buildListPane(context, visibleTickets, false),
        ),
      ],
    );
  }

  Widget _buildListPane(
    BuildContext context,
    List<TicketCard> visibleTickets,
    bool isWide,
  ) {
    final ctrl = widget.controller;
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(KwSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('board_search_field'),
                      controller: _searchController,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: 'Search household, appliance, ID…',
                        prefixIcon: const Icon(Icons.search_rounded),
                        isDense: true,
                        suffixIcon: _searchController.text.isNotEmpty
                            ? IconButton(
                                tooltip: 'Clear search',
                                onPressed: () {
                                  _searchController.clear();
                                  setState(() {});
                                },
                                icon: const Icon(Icons.close_rounded, size: 18),
                              )
                            : null,
                      ),
                    ),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  IconButton.filledTonal(
                    tooltip: 'Refresh cases',
                    onPressed: ctrl.loadingTickets
                        ? null
                        : () => ctrl.loadTickets(),
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.xs),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final urgency in const [
                      'safety',
                      'urgent',
                      'standard',
                      'planned',
                    ])
                      Padding(
                        padding: const EdgeInsets.only(right: KwSpacing.xs),
                        child: FilterChip(
                          label: Text(_capitalize(urgency)),
                          selected: _urgencyFilter == urgency,
                          onSelected: (selected) {
                            setState(
                              () => _urgencyFilter = selected ? urgency : null,
                            );
                          },
                        ),
                      ),
                    _CompactDropdown(
                      label: 'Status',
                      value: _statusFilter,
                      options: const [
                        'open',
                        'triage',
                        'self_fix',
                        'assigned',
                        'in_progress',
                        'closed',
                      ],
                      onChanged: (val) => setState(() => _statusFilter = val),
                    ),
                    const SizedBox(width: KwSpacing.xs),
                    _CompactDropdown(
                      label: 'Trigger',
                      value: _triggerFilter,
                      options: const [
                        'voice',
                        'whatsapp',
                        'brand',
                        'retailer',
                      ],
                      onChanged: (val) => setState(() => _triggerFilter = val),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: KwSpacing.xxs),
              Text(
                '${visibleTickets.length} cases · ordered Safety → Urgent → Standard → Planned',
                style: theme.textTheme.labelSmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: ctrl.loadingTickets && ctrl.tickets.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(KwSpacing.md),
                  child: KwSkeletonLoader(lines: 8),
                )
              : ctrl.ticketsError != null && ctrl.tickets.isEmpty
                  ? KwErrorState(
                      title: 'Could not load cases',
                      body: ctrl.ticketsError,
                      onRetry: () => ctrl.loadTickets(),
                    )
                  : visibleTickets.isEmpty
                      ? KwEmptyState(
                          icon: Icons.check_circle_outline_rounded,
                          title: 'No matching cases',
                          body:
                              'Adjust filters or play a seeded scenario from the Demo Drawer.',
                          action: (_urgencyFilter != null ||
                                  _statusFilter != null ||
                                  _triggerFilter != null ||
                                  _searchController.text.isNotEmpty)
                              ? OutlinedButton(
                                  onPressed: () {
                                    _searchController.clear();
                                    setState(() {
                                      _urgencyFilter = null;
                                      _statusFilter = null;
                                      _triggerFilter = null;
                                    });
                                  },
                                  child: const Text('Clear filters'),
                                )
                              : null,
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(KwSpacing.sm),
                          itemCount: visibleTickets.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: KwSpacing.xs),
                          itemBuilder: (context, index) {
                            final card = visibleTickets[index];
                            final appLabel = card.appliance == null
                                ? null
                                : '${card.appliance!.brand} ${card.appliance!.categoryCode}'
                                    '${card.appliance!.modelCode != null ? ' · ${card.appliance!.modelCode}' : ''}';
                            return KwCaseCard(
                              key: Key('case_card_${card.id}'),
                              ticketId: card.id,
                              urgency:
                                  KwUrgencyClass.fromWire(card.urgencyClass),
                              triggerLabel:
                                  '${card.trigger.toUpperCase()} · ${card.channel}',
                              householdName: card.household.displayName,
                              summary: card.complaintSummary,
                              applianceLabel: appLabel,
                              locality: card.household.locality,
                              neededBy:
                                  ConsoleController.parseIsoDate(card.neededBy),
                              statusLabel: card.status,
                              selected: ctrl.selectedTicketId == card.id,
                              safetyBannerText: card.safetyReason,
                              onTap: () => _selectTicket(card, isWide),
                            );
                          },
                        ),
        ),
      ],
    );
  }

  String _capitalize(String s) =>
      s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';
}

class _CompactDropdown extends StatelessWidget {
  const _CompactDropdown({
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  final String label;
  final String? value;
  final List<String> options;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: const Icon(Icons.filter_list_rounded, size: 16),
      label: Text(value == null ? label : '$label: $value'),
      tooltip: 'Filter by $label',
      onPressed: () async {
        final box = context.findRenderObject() as RenderBox?;
        final overlay =
            Overlay.of(context).context.findRenderObject() as RenderBox?;
        if (box == null || overlay == null) return;
        final pos = RelativeRect.fromRect(
          Rect.fromPoints(
            box.localToGlobal(Offset.zero, ancestor: overlay),
            box.localToGlobal(
              box.size.bottomRight(Offset.zero),
              ancestor: overlay,
            ),
          ),
          Offset.zero & overlay.size,
        );
        final selected = await showMenu<String>(
          context: context,
          position: pos,
          items: [
            PopupMenuItem<String>(
              value: '__all__',
              child: Text('All $label'),
            ),
            for (final opt in options)
              PopupMenuItem<String>(
                value: opt,
                child: Text(opt),
              ),
          ],
        );
        if (selected == null) return;
        onChanged(selected == '__all__' ? null : selected);
      },
    );
  }
}

class _LiveActivityStrip extends StatelessWidget {
  const _LiveActivityStrip({
    required this.events,
    required this.onSelectTicket,
  });

  final List<LiveEvent> events;
  final ValueChanged<String> onSelectTicket;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Container(
      height: 52,
      color: cs.surfaceContainerLow,
      padding: const EdgeInsets.symmetric(horizontal: KwSpacing.sm),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.xs,
              vertical: 4,
            ),
            decoration: BoxDecoration(
              color: cs.primaryContainer,
              borderRadius: KwShapes.radiusSmall,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.bolt_rounded, size: 15, color: cs.onPrimaryContainer),
                const SizedBox(width: 4),
                Text(
                  'LIVE FEED',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: cs.onPrimaryContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: KwSpacing.sm),
          Expanded(
            child: events.isEmpty
                ? Text(
                    'Listening for live centre updates…',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  )
                : ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: events.length.clamp(0, 12),
                    separatorBuilder: (_, __) =>
                        const SizedBox(width: KwSpacing.xs),
                    itemBuilder: (context, index) {
                      final ev = events[index];
                      final meta = KwEventVisualMeta.resolve(ev.type);
                      return Center(
                        child: ActionChip(
                          avatar: Icon(meta.icon, size: 16),
                          label: Text(
                            ev.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          onPressed: ev.ticketId == null
                              ? null
                              : () => onSelectTicket(ev.ticketId!),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
