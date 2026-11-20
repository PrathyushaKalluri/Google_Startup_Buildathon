import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Technicians & Day Calendar screen with route/ETA bars, static map fallback
/// when `GOOGLE_MAPS_API_KEY` is empty, and a keyboard-accessible Reschedule
/// dialog (WCAG 2.2 AA dragging alternative).
class CalendarScreen extends StatefulWidget {
  const CalendarScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  List<TechnicianSummary> _technicians = const [];
  List<Map<String, dynamic>> _calendarItems = const [];
  bool _loading = true;
  String? _error;

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
      final techsPage = await ctrl.apiClient.getCentreTechnicians(
        centreId: isPlatform ? null : ctrl.activeCentreId,
        centreKey: isPlatform ? null : ctrl.activeCentreKey,
      );
      final calPage = await ctrl.apiClient.getCentreCalendar(
        centreId: isPlatform ? null : ctrl.activeCentreId,
        centreKey: isPlatform ? null : ctrl.activeCentreKey,
      );
      if (mounted) {
        setState(() {
          _technicians = techsPage.items;
          _calendarItems = calPage.items;
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

  Future<void> _openRescheduleDialog({
    required String ticketId,
    required String currentTechId,
    required String currentStart,
    required String currentEnd,
  }) async {
    var selectedTechId = currentTechId;
    final startCtrl = TextEditingController(text: currentStart);
    final endCtrl = TextEditingController(text: currentEnd);
    final reasonCtrl = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogContext, setDialogState) {
          return AlertDialog(
            title: Text('Reschedule $ticketId'),
            content: SizedBox(
              width: 440,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_technicians.isNotEmpty)
                    DropdownButtonFormField<String>(
                      value: _technicians.any((t) => t.id == selectedTechId)
                          ? selectedTechId
                          : _technicians.first.id,
                      decoration: const InputDecoration(
                        labelText: 'Technician',
                      ),
                      items: [
                        for (final t in _technicians)
                          DropdownMenuItem(
                            value: t.id,
                            child: Text('${t.name} (${t.status})'),
                          ),
                      ],
                      onChanged: (v) {
                        if (v != null) {
                          setDialogState(() => selectedTechId = v);
                        }
                      },
                    ),
                  const SizedBox(height: KwSpacing.sm),
                  TextField(
                    controller: startCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Slot start (ISO)',
                    ),
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  TextField(
                    controller: endCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Slot end (ISO)',
                    ),
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  TextField(
                    controller: reasonCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Reason (required)',
                      hintText: 'e.g. Route balance for Kukatpally corridor',
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  if (reasonCtrl.text.trim().isEmpty) return;
                  Navigator.of(dialogContext).pop(true);
                },
                child: const Text('Save schedule'),
              ),
            ],
          );
        },
      ),
    );

    final slotStart = startCtrl.text.trim();
    final slotEnd = endCtrl.text.trim();
    final reason = reasonCtrl.text.trim();
    startCtrl.dispose();
    endCtrl.dispose();
    reasonCtrl.dispose();

    if (confirmed != true || reason.isEmpty || !mounted) return;

    try {
      await widget.controller.reassignTicket(
        ticketId: ticketId,
        technicianId: selectedTechId,
        slotStart: slotStart,
        slotEnd: slotEnd,
        reason: reason,
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Rescheduled $ticketId cleanly.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Reschedule failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final hasMapsKey =
        widget.controller.config.googleMapsApiKey.trim().isNotEmpty;

    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(KwSpacing.lg),
        child: KwSkeletonLoader(lines: 8),
      );
    }
    if (_error != null) {
      return KwErrorState(
        title: 'Could not load technician calendar',
        body: _error,
        onRetry: _load,
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(KwSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Technicians & Day Schedule',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton.filledTonal(
                tooltip: 'Refresh calendar',
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.sm),
          // Route / Map card with static fallback when GOOGLE_MAPS_API_KEY is empty
          Card(
            child: Padding(
              padding: const EdgeInsets.all(KwSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.map_outlined, color: cs.primary),
                      const SizedBox(width: KwSpacing.xs),
                      Expanded(
                        child: Text(
                          hasMapsKey
                              ? 'Live Hyderabad Route Map'
                              : 'Static Corridor Route Preview (Maps key not set)',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  Wrap(
                    spacing: KwSpacing.sm,
                    runSpacing: KwSpacing.xs,
                    children: [
                      KwRouteEtaBar(
                        driveMinutes: 14,
                        distanceKm: 4.8,
                        destinationLabel: 'Kukatpally → KPHB',
                        isStaticFallback: !hasMapsKey,
                      ),
                      KwRouteEtaBar(
                        driveMinutes: 22,
                        distanceKm: 7.4,
                        destinationLabel: 'Miyapur → Kondapur',
                        isStaticFallback: !hasMapsKey,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: KwSpacing.md),
          if (_technicians.isEmpty)
            const KwEmptyState(
              icon: Icons.engineering_outlined,
              title: 'No technicians listed',
              body: 'Switch to a centre with active technicians or reset demo data.',
            )
          else
            for (final tech in _technicians) ...[
              _buildTechnicianCard(context, tech, !hasMapsKey),
              const SizedBox(height: KwSpacing.sm),
            ],
        ],
      ),
    );
  }

  Widget _buildTechnicianCard(
    BuildContext context,
    TechnicianSummary tech,
    bool staticFallback,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final techJobs = _calendarItems.where((item) {
      final tid = item['technician_id']?.toString() ?? '';
      return tid == tech.id;
    }).toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                CircleAvatar(
                  backgroundColor: cs.primaryContainer,
                  child: Text(
                    tech.name.isEmpty ? '?' : tech.name[0].toUpperCase(),
                    style: TextStyle(color: cs.onPrimaryContainer),
                  ),
                ),
                Text(
                  tech.name,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Chip(label: Text(tech.status)),
                Chip(label: Text('${tech.shiftStart}–${tech.shiftEnd}')),
                Chip(label: Text(tech.vehicleType)),
                for (final lang in tech.languages)
                  Chip(label: Text(lang.toUpperCase())),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            if (techJobs.isEmpty)
              Text(
                'Open capacity across today’s shift window.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              )
            else
              Column(
                children: [
                  for (final job in techJobs)
                    Container(
                      margin: const EdgeInsets.only(bottom: KwSpacing.xs),
                      padding: const EdgeInsets.all(KwSpacing.sm),
                      decoration: BoxDecoration(
                        color: cs.surface,
                        borderRadius: KwShapes.radiusMedium,
                        border: Border.all(color: cs.outlineVariant),
                      ),
                      child: Wrap(
                        spacing: KwSpacing.sm,
                        runSpacing: KwSpacing.xs,
                        alignment: WrapAlignment.spaceBetween,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${job['ticket_id'] ?? 'Visit'} · ${job['household_name'] ?? job['locality'] ?? 'Scheduled visit'}',
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${job['slot_start'] ?? ''} → ${job['slot_end'] ?? ''}',
                                style: KwTheme.monoStyle(
                                  context,
                                  fontSize: theme.textTheme.bodySmall?.fontSize,
                                  color: cs.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                          KwRouteEtaBar(
                            driveMinutes:
                                (job['drive_minutes'] as num?)?.toInt() ?? 16,
                            distanceKm:
                                (job['distance_km'] as num?)?.toDouble() ?? 5.2,
                            isStaticFallback: staticFallback,
                          ),
                          OutlinedButton.icon(
                            onPressed: () => _openRescheduleDialog(
                              ticketId: job['ticket_id']?.toString() ?? '',
                              currentTechId: tech.id,
                              currentStart: job['slot_start']?.toString() ?? '',
                              currentEnd: job['slot_end']?.toString() ?? '',
                            ),
                            icon: const Icon(Icons.edit_calendar_rounded, size: 18),
                            label: const Text('Reschedule'),
                          ),
                        ],
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
