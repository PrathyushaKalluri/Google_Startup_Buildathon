import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import '../field_l10n.dart';
import 'offline_outbox.dart';
import 'visit_detail_screen.dart';

/// Technician "Today's Jobs" list screen loaded from `api.getMyJobs(...)`.
class TechJobsScreen extends StatefulWidget {
  const TechJobsScreen({
    super.key,
    required this.api,
    required this.session,
    required this.outbox,
  });

  final KwApiClient api;
  final KwUserSession session;
  final OfflineOutboxController outbox;

  @override
  State<TechJobsScreen> createState() => _TechJobsScreenState();
}

class _TechJobsScreenState extends State<TechJobsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _jobs = const [];

  @override
  void initState() {
    super.initState();
    _loadJobs();
  }

  Future<void> _loadJobs() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await widget.api.getMyJobs(
        technicianId: widget.session.technicianId,
      );
      if (!mounted) return;
      setState(() {
        _jobs = page.items.map(_flattenJob).toList();
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

  String _formatSlot(Map<String, dynamic> job) {
    final startRaw = (job['planned_start'] ?? job['slot_start'] ?? '').toString();
    final endRaw = (job['planned_end'] ?? job['slot_end'] ?? '').toString();
    final startDt = DateTime.tryParse(startRaw);
    final endDt = DateTime.tryParse(endRaw);
    if (startDt != null && endDt != null) {
      return formatIstSlotWindow(startDt, endDt);
    }
    if (startRaw.isNotEmpty && endRaw.isNotEmpty) {
      return '$startRaw – $endRaw';
    }
    return 'Slot window pending';
  }

  /// The API returns `{visit: {...}, ticket: {...}}` per job. The cards below read flat
  /// fields (`visit_id`, `planned_start`, `summary`, ...), so merge the two maps.
  Map<String, dynamic> _flattenJob(Map<String, dynamic> raw) {
    final visit = raw['visit'];
    final ticket = raw['ticket'];
    if (visit is! Map && ticket is! Map) return raw;
    final out = <String, dynamic>{};
    if (ticket is Map) {
      out.addAll(Map<String, dynamic>.from(ticket));
      out['ticket_id'] = ticket['id'];
    }
    if (visit is Map) {
      out.addAll(Map<String, dynamic>.from(visit));
      out['visit_id'] = visit['id'];
    }
    if (ticket is Map && ticket['id'] != null) out['id'] = ticket['id'];
    return out;
  }

  Future<void> _openVisit(Map<String, dynamic> job) async {
    final visitId = (job['visit_id'] ?? job['id'] ?? '').toString();
    if (visitId.isEmpty) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => VisitDetailScreen(
          api: widget.api,
          outbox: widget.outbox,
          visitId: visitId,
          initialJobSummary: job,
        ),
      ),
    );
    if (mounted && !widget.outbox.isOffline) {
      _loadJobs();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = FieldStrings.of(context);

    return Column(
      children: [
        OfflineSyncBanner(
          outbox: widget.outbox,
          onSynced: _loadJobs,
        ),
        Expanded(
          child: _loading
              ? const Padding(
                  padding: EdgeInsets.all(KwSpacing.md),
                  child: KwSkeletonLoader(lines: 6, height: 18),
                )
              : _error != null
                  ? KwErrorState(
                      body: _error,
                      onRetry: _loadJobs,
                    )
                  : _jobs.isEmpty
                      ? KwEmptyState(
                          icon: Icons.build_circle_outlined,
                          title: strings.todaysJobsTitle,
                          body: 'No visits assigned yet for today.',
                          action: FilledButton.icon(
                            onPressed: _loadJobs,
                            icon: const Icon(Icons.refresh_rounded),
                            label: Text(KwStrings.of(context).retryLabel),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadJobs,
                          child: ListView.separated(
                            padding: const EdgeInsets.all(KwSpacing.md),
                            itemCount: _jobs.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: KwSpacing.sm),
                            itemBuilder: (context, index) {
                              final job = _jobs[index];
                              final visitId =
                                  (job['visit_id'] ?? job['id'] ?? '').toString();
                              final ticketId =
                                  (job['ticket_id'] ?? '').toString();
                              final urgency = KwUrgencyClass.fromWire(
                                job['urgency_class']?.toString(),
                              );
                              final summary = (job['complaint_summary'] ??
                                      job['summary'] ??
                                      'Service visit')
                                  .toString();
                              final locality = (job['locality'] ??
                                      (job['household'] is Map<dynamic, dynamic>
                                          ? (job['household']
                                              as Map<dynamic, dynamic>)['locality']
                                          : null) ??
                                      '')
                                  .toString();
                              final brand = (job['appliance_brand'] ??
                                      (job['appliance'] is Map<dynamic, dynamic>
                                          ? (job['appliance']
                                              as Map<dynamic, dynamic>)['brand']
                                          : null) ??
                                      '')
                                  .toString();
                              final category = (job['appliance_category'] ??
                                      (job['appliance'] is Map<dynamic, dynamic>
                                          ? (job['appliance'] as Map<dynamic,
                                              dynamic>)['category_code']
                                          : null) ??
                                      '')
                                  .toString();
                              final status =
                                  (job['status'] ?? 'assigned').toString();

                              return Card(
                                key: Key('kw_job_card_$visitId'),
                                clipBehavior: Clip.antiAlias,
                                child: InkWell(
                                  onTap: () => _openVisit(job),
                                  child: Padding(
                                    padding: const EdgeInsets.all(KwSpacing.md),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            KwUrgencyChip(
                                              urgency: urgency,
                                              compact: true,
                                            ),
                                            const SizedBox(width: KwSpacing.xs),
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                horizontal: KwSpacing.xs,
                                                vertical: 4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: cs.secondaryContainer,
                                                borderRadius:
                                                    KwShapes.radiusSmall,
                                              ),
                                              child: Text(
                                                status
                                                    .replaceAll('_', ' ')
                                                    .toUpperCase(),
                                                style: theme
                                                    .textTheme.labelSmall
                                                    ?.copyWith(
                                                  color:
                                                      cs.onSecondaryContainer,
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
                                                  fontSize: theme.textTheme
                                                      .labelSmall?.fontSize,
                                                  color: cs.onSurfaceVariant,
                                                ),
                                              ),
                                          ],
                                        ),
                                        const SizedBox(height: KwSpacing.sm),
                                        Text(
                                          summary,
                                          style: theme.textTheme.titleMedium
                                              ?.copyWith(
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        const SizedBox(height: KwSpacing.xs),
                                        Wrap(
                                          spacing: KwSpacing.md,
                                          runSpacing: KwSpacing.xxs,
                                          children: [
                                            Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(
                                                  Icons.schedule_rounded,
                                                  size: 16,
                                                  color: cs.primary,
                                                ),
                                                const SizedBox(width: 4),
                                                Text(
                                                  _formatSlot(job),
                                                  style: theme
                                                      .textTheme.bodySmall
                                                      ?.copyWith(
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            if (locality.isNotEmpty)
                                              Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    Icons.location_on_outlined,
                                                    size: 16,
                                                    color: cs.onSurfaceVariant,
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    locality,
                                                    style: theme
                                                        .textTheme.bodySmall
                                                        ?.copyWith(
                                                      color:
                                                          cs.onSurfaceVariant,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            if (brand.isNotEmpty ||
                                                category.isNotEmpty)
                                              Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    Icons
                                                        .kitchen_outlined,
                                                    size: 16,
                                                    color: cs.onSurfaceVariant,
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    [brand, category]
                                                        .where((s) =>
                                                            s.isNotEmpty)
                                                        .join(' · '),
                                                    style: theme
                                                        .textTheme.bodySmall
                                                        ?.copyWith(
                                                      color:
                                                          cs.onSurfaceVariant,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                          ],
                                        ),
                                        const SizedBox(height: KwSpacing.sm),
                                        Align(
                                          alignment: Alignment.centerRight,
                                          child: FilledButton.tonalIcon(
                                            onPressed: () => _openVisit(job),
                                            icon: const Icon(
                                              Icons.arrow_forward_rounded,
                                              size: 18,
                                            ),
                                            label: const Text('Open job brief'),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
        ),
      ],
    );
  }
}
