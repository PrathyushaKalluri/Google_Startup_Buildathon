import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import '../field_l10n.dart';

/// Parts Centre incoming reservation queue screen.
///
/// Uses large (>= 52 dp) one-handed primary action buttons for Accept,
/// Mark Ready, and Handover transitions.
class PartsRequestsScreen extends StatefulWidget {
  const PartsRequestsScreen({
    super.key,
    required this.api,
  });

  final KwApiClient api;

  @override
  State<PartsRequestsScreen> createState() => _PartsRequestsScreenState();
}

class _PartsRequestsScreenState extends State<PartsRequestsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _requests = <Map<String, dynamic>>[];
  final Set<String> _busyIds = <String>{};

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await widget.api.listPartsRequests();
      if (!mounted) return;
      setState(() {
        _requests = page.items.map((e) => Map<String, dynamic>.from(e)).toList();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _transition(
    int index,
    String targetStatus,
    Future<Map<String, dynamic>> Function(String id) call,
  ) async {
    final item = _requests[index];
    final id = (item['id'] ?? '').toString();
    if (id.isEmpty || _busyIds.contains(id)) return;

    setState(() => _busyIds.add(id));
    try {
      final updated = await call(id);
      if (!mounted) return;
      setState(() {
        _requests[index] = <String, dynamic>{
          ...item,
          ...updated,
          'status': (updated['status'] ?? targetStatus).toString(),
        };
        _busyIds.remove(id);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyIds.remove(id));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Action failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = FieldStrings.of(context);

    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(KwSpacing.md),
        child: KwSkeletonLoader(lines: 6, height: 20),
      );
    }
    if (_error != null) {
      return KwErrorState(body: _error, onRetry: _loadRequests);
    }
    if (_requests.isEmpty) {
      return KwEmptyState(
        icon: Icons.inventory_2_outlined,
        title: 'No pending parts requests',
        body: 'Incoming reservations from technicians will appear here.',
        action: FilledButton.icon(
          onPressed: _loadRequests,
          icon: const Icon(Icons.refresh_rounded),
          label: Text(KwStrings.of(context).retryLabel),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadRequests,
      child: ListView.separated(
        padding: const EdgeInsets.all(KwSpacing.md),
        itemCount: _requests.length,
        separatorBuilder: (_, __) => const SizedBox(height: KwSpacing.sm),
        itemBuilder: (context, index) {
          final req = _requests[index];
          final id = (req['id'] ?? '').toString();
          final partNo = (req['part_no'] ?? '').toString();
          final partName = (req['part_name'] ?? req['name'] ?? 'Spare part').toString();
          final qty = (req['quantity'] as num?)?.toInt() ?? 1;
          final techName = (req['technician_name'] ?? req['technician_id'] ?? '').toString();
          final ticketId = (req['ticket_id'] ?? '').toString();
          final status = (req['status'] ?? 'requested').toString().toLowerCase();
          final isBusy = _busyIds.contains(id);

          final (statusLabel, role) = switch (status) {
            'accepted' => ('Accepted', kw.standard),
            'ready' => ('Ready for pickup', kw.planned),
            'handed_over' || 'completed' => ('Handed over', kw.verified),
            _ => ('Requested', kw.urgent),
          };

          return Card(
            key: Key('kw_parts_req_$id'),
            child: Padding(
              padding: const EdgeInsets.all(KwSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: KwSpacing.xs,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: role.container,
                          borderRadius: KwShapes.radiusSmall,
                        ),
                        child: Text(
                          statusLabel,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: role.onContainer,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const Spacer(),
                      if (ticketId.isNotEmpty)
                        Text(
                          ticketId,
                          style: KwTheme.monoStyle(
                            context,
                            fontSize: theme.textTheme.labelSmall?.fontSize,
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  Text(
                    '$partName (×$qty)',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: KwSpacing.xxs),
                  Text(
                    '$partNo${techName.isNotEmpty ? ' · $techName' : ''}',
                    style: KwTheme.monoStyle(
                      context,
                      fontSize: theme.textTheme.bodySmall?.fontSize,
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: KwSpacing.md),
                  _buildPrimaryAction(
                    context,
                    id: id,
                    index: index,
                    status: status,
                    isBusy: isBusy,
                    strings: strings,
                    kw: kw,
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPrimaryAction(
    BuildContext context, {
    required String id,
    required int index,
    required String status,
    required bool isBusy,
    required FieldStrings strings,
    required KwSemanticColors kw,
  }) {
    final buttonStyle = FilledButton.styleFrom(
      minimumSize: const Size(double.infinity, 52),
    );

    if (status == 'requested' || status == 'pending') {
      return FilledButton.icon(
        key: Key('kw_parts_accept_$id'),
        style: buttonStyle,
        onPressed: isBusy
            ? null
            : () => _transition(
                  index,
                  'accepted',
                  widget.api.acceptPartsRequest,
                ),
        icon: const Icon(Icons.thumb_up_alt_outlined),
        label: Text(strings.acceptAction),
      );
    }

    if (status == 'accepted') {
      return FilledButton.icon(
        key: Key('kw_parts_ready_$id'),
        style: buttonStyle,
        onPressed: isBusy
            ? null
            : () => _transition(
                  index,
                  'ready',
                  widget.api.readyPartsRequest,
                ),
        icon: const Icon(Icons.inventory_rounded),
        label: Text(strings.markReadyAction),
      );
    }

    if (status == 'ready') {
      return FilledButton.icon(
        key: Key('kw_parts_handover_$id'),
        style: buttonStyle,
        onPressed: isBusy
            ? null
            : () => _transition(
                  index,
                  'handed_over',
                  widget.api.handoverPartsRequest,
                ),
        icon: const Icon(Icons.handshake_outlined),
        label: Text(strings.handoverAction),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: KwSpacing.md,
        vertical: KwSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: kw.verified.container,
        borderRadius: KwShapes.radiusSmall,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.check_circle_rounded,
            size: 20,
            color: kw.verified.onContainer,
          ),
          const SizedBox(width: KwSpacing.xs),
          Text(
            'Handed over to technician',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: kw.verified.onContainer,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}
