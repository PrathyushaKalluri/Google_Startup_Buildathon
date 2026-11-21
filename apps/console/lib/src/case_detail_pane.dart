import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Complete Case Detail pane for the selected ticket.
///
/// Displays household & appliance identity, authority check, urgency with
/// Reclassify (+ 10s Undo), two-step consent gates, clarifying Q&A, fixes tried,
/// diagnosis hypotheses with citations, visit plan with `"Needs checking"` parts,
/// 6-factor technician candidates with Reassign (+ 10s Undo), slots, quotes,
/// payments, debrief, timeline, and centre actions.
class CaseDetailPane extends StatefulWidget {
  const CaseDetailPane({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<CaseDetailPane> createState() => _CaseDetailPaneState();
}

class _CaseDetailPaneState extends State<CaseDetailPane> {
  bool _actionBusy = false;

  Future<void> _openReclassifyDialog(TicketDetail detail) async {
    final previousClass = detail.card.urgencyClass;
    var selectedClass = previousClass;
    final reasonController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              title: const Text('Change urgency'),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Select the updated urgency class and explain why so the agent learns from your override.',
                      style: Theme.of(ctx).textTheme.bodySmall,
                    ),
                    const SizedBox(height: KwSpacing.sm),
                    DropdownButtonFormField<String>(
                      key: const Key('reclassify_class_dropdown'),
                      value: selectedClass,
                      decoration: const InputDecoration(
                        labelText: 'Urgency class',
                      ),
                      items: const [
                        DropdownMenuItem(value: 'safety', child: Text('Safety')),
                        DropdownMenuItem(value: 'urgent', child: Text('Urgent')),
                        DropdownMenuItem(
                          value: 'standard',
                          child: Text('Standard'),
                        ),
                        DropdownMenuItem(
                          value: 'planned',
                          child: Text('Planned'),
                        ),
                      ],
                      onChanged: (v) {
                        if (v != null) {
                          setDialogState(() => selectedClass = v);
                        }
                      },
                    ),
                    const SizedBox(height: KwSpacing.sm),
                    TextField(
                      key: const Key('reclassify_reason_field'),
                      controller: reasonController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Reason (required)',
                        hintText: 'e.g. Elderly resident without cooling overnight',
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  key: const Key('reclassify_confirm_button'),
                  onPressed: () {
                    if (reasonController.text.trim().isEmpty) return;
                    Navigator.of(ctx).pop(true);
                  },
                  child: const Text('Save urgency'),
                ),
              ],
            );
          },
        );
      },
    );

    final reason = reasonController.text.trim();
    if (confirmed != true || reason.isEmpty || !mounted) return;

    setState(() => _actionBusy = true);
    try {
      await widget.controller.reclassifyUrgency(
        ticketId: detail.card.id,
        urgencyClass: selectedClass,
        reason: reason,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 10),
            content: Text(
              'Urgency updated to $selectedClass (was $previousClass).',
            ),
            action: SnackBarAction(
              label: 'Undo',
              onPressed: () {
                widget.controller.reclassifyUrgency(
                  ticketId: detail.card.id,
                  urgencyClass: previousClass,
                  reason: 'Undo urgency reclassification',
                );
              },
            ),
          ),
        );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not reclassify urgency: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  Future<void> _openReassignSheet(TicketDetail detail) async {
    final candidates = detail.candidates;
    final previousWinner = candidates.isNotEmpty
        ? candidates.firstWhere(
            (c) => c.outcome == 'assigned' || c.outcome == 'accepted',
            orElse: () => candidates.first,
          )
        : null;

    var selectedTechId = candidates.length > 1
        ? candidates[1].technicianId
        : (candidates.isNotEmpty ? candidates.first.technicianId : 'tech_1');
    final initialCand = candidates.firstWhere(
      (c) => c.technicianId == selectedTechId,
      orElse: () => AssignmentCandidate(
        technicianId: selectedTechId,
        name: selectedTechId,
        rank: 1,
        score: 80,
        scoreBreakdown: const ScoreBreakdown(
          fixConfidence: 24,
          partsReadiness: 20,
          timeToVisit: 16,
          routeCost: 12,
          reliability: 4,
          householdFit: 4,
        ),
        slotStart: DateTime.now().add(const Duration(hours: 2)).toIso8601String(),
        slotEnd: DateTime.now().add(const Duration(hours: 4)).toIso8601String(),
        outcome: 'proposed',
        chosenBy: 'agent',
        why: '',
      ),
    );

    final slotStartController =
        TextEditingController(text: initialCand.slotStart);
    final slotEndController = TextEditingController(text: initialCand.slotEnd);
    final reasonController = TextEditingController();

    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                KwSpacing.lg,
                KwSpacing.xs,
                KwSpacing.lg,
                MediaQuery.viewInsetsOf(ctx).bottom + KwSpacing.lg,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Reassign technician',
                      style: Theme.of(ctx).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: KwSpacing.sm),
                    if (candidates.isNotEmpty)
                      ...candidates.map((cand) {
                        return RadioListTile<String>(
                          key: Key('reassign_candidate_${cand.technicianId}'),
                          value: cand.technicianId,
                          groupValue: selectedTechId,
                          title: Text('${cand.name} (#${cand.rank} · ${cand.score.toStringAsFixed(0)}/100)'),
                          subtitle: Text(cand.why),
                          onChanged: (val) {
                            if (val == null) return;
                            setSheetState(() {
                              selectedTechId = val;
                              slotStartController.text = cand.slotStart;
                              slotEndController.text = cand.slotEnd;
                            });
                          },
                        );
                      })
                    else
                      TextField(
                        decoration: const InputDecoration(
                          labelText: 'Technician ID',
                        ),
                        onChanged: (val) => selectedTechId = val.trim(),
                      ),
                    const SizedBox(height: KwSpacing.sm),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: slotStartController,
                            decoration: const InputDecoration(
                              labelText: 'Slot start (ISO)',
                            ),
                          ),
                        ),
                        const SizedBox(width: KwSpacing.sm),
                        Expanded(
                          child: TextField(
                            controller: slotEndController,
                            decoration: const InputDecoration(
                              labelText: 'Slot end (ISO)',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: KwSpacing.sm),
                    TextField(
                      key: const Key('reassign_reason_field'),
                      controller: reasonController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Reason (required)',
                        hintText: 'e.g. Closer technician already carrying pump part',
                      ),
                    ),
                    const SizedBox(height: KwSpacing.md),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(false),
                          child: const Text('Cancel'),
                        ),
                        const SizedBox(width: KwSpacing.xs),
                        FilledButton(
                          key: const Key('reassign_confirm_button'),
                          onPressed: () {
                            if (reasonController.text.trim().isEmpty) return;
                            Navigator.of(ctx).pop(true);
                          },
                          child: const Text('Confirm reassignment'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    final slotStart = slotStartController.text.trim();
    final slotEnd = slotEndController.text.trim();
    final reason = reasonController.text.trim();

    if (confirmed != true || reason.isEmpty || !mounted) return;

    setState(() => _actionBusy = true);
    try {
      await widget.controller.reassignTicket(
        ticketId: detail.card.id,
        technicianId: selectedTechId,
        slotStart: slotStart,
        slotEnd: slotEnd,
        reason: reason,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 10),
            content: Text('Reassigned case to $selectedTechId.'),
            action: previousWinner != null
                ? SnackBarAction(
                    label: 'Undo',
                    onPressed: () {
                      widget.controller.reassignTicket(
                        ticketId: detail.card.id,
                        technicianId: previousWinner.technicianId,
                        slotStart: previousWinner.slotStart,
                        slotEnd: previousWinner.slotEnd,
                        reason: 'Undo technician reassignment',
                      );
                    },
                  )
                : null,
          ),
        );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Reassignment failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  Future<void> _rerunDiagnosis(TicketDetail detail) async {
    setState(() => _actionBusy = true);
    try {
      await widget.controller.rerunDiagnosis(detail.card.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Diagnosis re-run completed.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Diagnosis re-run failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  Future<void> _openReturnToBrandDialog(TicketDetail detail) async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Return to brand'),
        content: TextField(
          controller: reasonController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Reason (required)',
            hintText: 'e.g. Outside authorised pincode or brand warranty escalation',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (reasonController.text.trim().isEmpty) return;
              Navigator.of(ctx).pop(true);
            },
            child: const Text('Return to brand'),
          ),
        ],
      ),
    );
    final reason = reasonController.text.trim();
    if (confirmed != true || reason.isEmpty || !mounted) return;

    setState(() => _actionBusy = true);
    try {
      await widget.controller.returnToBrand(
        ticketId: detail.card.id,
        reason: reason,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Case returned to brand.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Return to brand failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  Future<void> _openSendMessageDialog(TicketDetail detail) async {
    final textController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Send message to household'),
        content: TextField(
          controller: textController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Message',
            hintText: 'Share an update on technician arrival or part status…',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (textController.text.trim().isEmpty) return;
              Navigator.of(ctx).pop(true);
            },
            child: const Text('Send'),
          ),
        ],
      ),
    );
    final text = textController.text.trim();
    textController.dispose();
    if (confirmed != true || text.isEmpty || !mounted) return;

    setState(() => _actionBusy = true);
    try {
      await widget.controller.sendCentreMessage(
        ticketId: detail.card.id,
        text: text,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Message sent to household.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not send message: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = widget.controller;
    if (ctrl.loadingDetail && ctrl.selectedDetail == null) {
      return const Padding(
        padding: EdgeInsets.all(KwSpacing.lg),
        child: KwSkeletonLoader(lines: 10),
      );
    }
    if (ctrl.detailError != null && ctrl.selectedDetail == null) {
      return KwErrorState(
        title: 'Could not load case detail',
        body: ctrl.detailError,
        onRetry: ctrl.selectedTicketId == null
            ? null
            : () => ctrl.selectTicket(ctrl.selectedTicketId!),
      );
    }
    final detail = ctrl.selectedDetail;
    if (detail == null) {
      return const KwEmptyState(
        icon: Icons.touch_app_outlined,
        title: 'Select a case',
        body: 'Choose a case from the board to inspect triage, diagnosis, and assignment.',
      );
    }

    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final card = detail.card;
    final latestUrgency =
        detail.urgency.isNotEmpty ? detail.urgency.last : null;

    final gate1 = _findGate(detail.gates, 1);
    final gate2 = _findGate(detail.gates, 2);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(KwSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header & primary action bar
          Wrap(
            spacing: KwSpacing.sm,
            runSpacing: KwSpacing.sm,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: KwSpacing.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        card.id,
                        style: KwTheme.monoStyle(
                          context,
                          fontSize: theme.textTheme.titleMedium?.fontSize,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      KwUrgencyChip(
                        urgency: KwUrgencyClass.fromWire(card.urgencyClass),
                      ),
                      Chip(label: Text(card.status)),
                      Chip(label: Text('${card.entitlement.toUpperCase()} · ${card.jobType}')),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.xxs),
                  Text(
                    card.complaintSummary,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              Wrap(
                spacing: KwSpacing.xs,
                runSpacing: KwSpacing.xs,
                children: [
                  FilledButton.tonalIcon(
                    key: const Key('action_change_urgency'),
                    onPressed:
                        _actionBusy ? null : () => _openReclassifyDialog(detail),
                    icon: const Icon(Icons.tune_rounded, size: 18),
                    label: const Text('Change urgency'),
                  ),
                  FilledButton.tonalIcon(
                    key: const Key('action_reassign'),
                    onPressed:
                        _actionBusy ? null : () => _openReassignSheet(detail),
                    icon: const Icon(Icons.swap_horiz_rounded, size: 18),
                    label: const Text('Reassign'),
                  ),
                  OutlinedButton.icon(
                    onPressed:
                        _actionBusy ? null : () => _rerunDiagnosis(detail),
                    icon: const Icon(Icons.biotech_rounded, size: 18),
                    label: const Text('Re-run diagnosis'),
                  ),
                  OutlinedButton.icon(
                    onPressed:
                        _actionBusy ? null : () => _openSendMessageDialog(detail),
                    icon: const Icon(Icons.send_rounded, size: 18),
                    label: const Text('Send message'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _actionBusy
                        ? null
                        : () => _openReturnToBrandDialog(detail),
                    icon: const Icon(Icons.undo_rounded, size: 18),
                    label: const Text('Return to brand'),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.md),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(KwSpacing.md),
              child: KwStatusStepper(
                currentStep: ConsoleController.statusToStep(card.status),
              ),
            ),
          ),
          const SizedBox(height: KwSpacing.md),

          // Household, Appliance & Authority
          _SectionCard(
            title: 'Household, Appliance & Authority',
            icon: Icons.home_work_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: KwSpacing.lg,
                  runSpacing: KwSpacing.sm,
                  children: [
                    _KeyValue(
                      label: 'Household',
                      value:
                          '${card.household.displayName} (${card.household.language.toUpperCase()})',
                    ),
                    _KeyValue(
                      label: 'Address',
                      value:
                          '${card.household.addressLine}, ${card.household.locality} ${card.household.pincode}',
                    ),
                    _KeyValue(
                      label: 'Verified via',
                      value: card.household.verifiedVia,
                    ),
                    if (card.appliance != null) ...[
                      _KeyValue(
                        label: 'Appliance',
                        value:
                            '${card.appliance!.brand} ${card.appliance!.categoryCode} · ${card.appliance!.modelCode ?? 'Model pending'}',
                      ),
                      _KeyValue(
                        label: 'Identity confidence',
                        value: card.appliance!.identityStatus,
                      ),
                      if (card.appliance!.serialMasked != null)
                        _KeyValue(
                          label: 'Serial',
                          value: card.appliance!.serialMasked!,
                          mono: true,
                        ),
                      if (card.appliance!.warrantyEnd != null)
                        _KeyValue(
                          label: 'Warranty end',
                          value: card.appliance!.warrantyEnd!,
                        ),
                    ],
                    _KeyValue(
                      label: 'Authority check',
                      value:
                          '${detail.authority.level} → ${detail.authority.decision}',
                    ),
                  ],
                ),
                if (detail.caseCard.summary.isNotEmpty) ...[
                  const SizedBox(height: KwSpacing.sm),
                  Text(
                    detail.caseCard.summary,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
                if (detail.caseCard.errorCodes.isNotEmpty) ...[
                  const SizedBox(height: KwSpacing.xs),
                  Wrap(
                    spacing: KwSpacing.xs,
                    children: [
                      for (final code in detail.caseCard.errorCodes)
                        Chip(
                          label: Text(
                            code,
                            style: KwTheme.monoStyle(context),
                          ),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: KwSpacing.md),

          // Urgency reasoning + Rule codes
          if (latestUrgency != null) ...[
            _SectionCard(
              title: 'Urgency Assessment',
              icon: Icons.speed_rounded,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: KwSpacing.xs,
                    runSpacing: KwSpacing.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      KwUrgencyChip(
                        urgency:
                            KwUrgencyClass.fromWire(latestUrgency.urgencyClass),
                      ),
                      Text(
                        'Assessed by ${latestUrgency.assessedBy}',
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                      for (final rule in latestUrgency.ruleCodes)
                        Chip(
                          label: Text(rule, style: KwTheme.monoStyle(context)),
                        ),
                    ],
                  ),
                  const SizedBox(height: KwSpacing.xs),
                  Text(latestUrgency.reason, style: theme.textTheme.bodyMedium),
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Two-step Consent Gates
          KwConsentGateCard(gate1: gate1, gate2: gate2),
          const SizedBox(height: KwSpacing.md),

          // Clarifying Q&A
          if (detail.clarifyingQa.isNotEmpty) ...[
            _SectionCard(
              title: 'Clarifying Questions',
              icon: Icons.question_answer_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final qa in detail.clarifyingQa)
                    Padding(
                      padding: const EdgeInsets.only(bottom: KwSpacing.sm),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Q${qa.seq}: ${qa.question}',
                            style: theme.textTheme.labelLarge?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            qa.answer ?? 'Awaiting answer',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Fixes Tried
          if (detail.fixAttempts.isNotEmpty) ...[
            _SectionCard(
              title: 'Safe Self-Fixes Tried',
              icon: Icons.build_circle_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final fix in detail.fixAttempts)
                    Container(
                      margin: const EdgeInsets.only(bottom: KwSpacing.xs),
                      padding: const EdgeInsets.all(KwSpacing.sm),
                      decoration: BoxDecoration(
                        color: cs.surface,
                        borderRadius: KwShapes.radiusMedium,
                        border: Border.all(color: cs.outlineVariant),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: KwSpacing.xs,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                fix.title,
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Chip(label: Text('${fix.stepsDone}/${fix.ofSteps} steps')),
                              Chip(label: Text(fix.outcome)),
                              if (fix.observedOnVideo)
                                const Chip(
                                  avatar: Icon(Icons.videocam_rounded, size: 16),
                                  label: Text('Observed on video'),
                                ),
                            ],
                          ),
                          if (fix.householdReport.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              fix.householdReport,
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Diagnosis Hypotheses
          if (detail.diagnosis != null) ...[
            _SectionCard(
              title: 'Diagnosis Hypotheses (${detail.diagnosis!.modelVersion})',
              icon: Icons.biotech_rounded,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (detail.diagnosis!.abstained)
                    KwConfidenceMeter(
                      probability: 0.0,
                      abstained: true,
                      abstentionReason: detail.diagnosis!.reason,
                    ),
                  for (final hyp in detail.diagnosis!.hypotheses) ...[
                    KwConfidenceMeter(
                      probability: hyp.probability,
                      label: hyp.label,
                      evidenceCount: hyp.evidence.length,
                    ),
                    if (hyp.evidence.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Evidence: ${hyp.evidence.join(' • ')}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                    ],
                    if (hyp.citations.isNotEmpty) ...[
                      const SizedBox(height: KwSpacing.xs),
                      Wrap(
                        spacing: KwSpacing.xs,
                        runSpacing: KwSpacing.xs,
                        children: [
                          for (final c in hyp.citations)
                            KwSourceCitationChip(
                              docTitle: c.docTitle,
                              snippet: c.snippet,
                              page: c.page,
                              uri: c.uri,
                            ),
                        ],
                      ),
                    ],
                    const SizedBox(height: KwSpacing.sm),
                  ],
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Visit Plan
          if (detail.visitPlan != null) ...[
            _SectionCard(
              title:
                  'Visit Plan v${detail.visitPlan!.version} (${detail.visitPlan!.estDurationP50Min}–${detail.visitPlan!.estDurationP80Min} min)',
              icon: Icons.assignment_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (detail.visitPlan!.requiredSkills.isNotEmpty)
                    Wrap(
                      spacing: KwSpacing.xs,
                      runSpacing: KwSpacing.xs,
                      children: [
                        for (final skill in detail.visitPlan!.requiredSkills)
                          Chip(label: Text('Skill: $skill')),
                        for (final tool in detail.visitPlan!.toolsNeeded)
                          Chip(label: Text('Tool: $tool')),
                      ],
                    ),
                  if (detail.visitPlan!.alreadyTried.isNotEmpty) ...[
                    const SizedBox(height: KwSpacing.sm),
                    Text(
                      'Already tried: ${detail.visitPlan!.alreadyTried.join(', ')}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                  if (detail.visitPlan!.parts.isNotEmpty) ...[
                    const SizedBox(height: KwSpacing.sm),
                    for (final part in detail.visitPlan!.parts)
                      Padding(
                        padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                        child: KwMoneyLine(
                          description:
                              '${part.name} (×${part.quantity} · ${(part.probability * 100).round()}% · ${part.sourceLadder})',
                          partNo: part.partNo.isEmpty ? null : part.partNo,
                          payer: KwPayer.household,
                          needsChecking: !part.ready ||
                              part.partNo.isEmpty ||
                              part.sourceLadder == 'unmatched',
                          amountPaise: 0,
                          showZeroDecimals: false,
                        ),
                      ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Technician Candidates
          if (detail.candidates.isNotEmpty) ...[
            _SectionCard(
              title: 'Technician Candidates (6-Factor Score)',
              icon: Icons.engineering_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final cand in detail.candidates) ...[
                    Container(
                      margin: const EdgeInsets.only(bottom: KwSpacing.sm),
                      padding: const EdgeInsets.all(KwSpacing.sm),
                      decoration: BoxDecoration(
                        color: cs.surface,
                        borderRadius: KwShapes.radiusMedium,
                        border: Border.all(
                          color: cand.outcome == 'assigned'
                              ? cs.primary
                              : cs.outlineVariant,
                          width: cand.outcome == 'assigned' ? 2 : 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: KwSpacing.xs,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                '#${cand.rank} ${cand.name}',
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Chip(label: Text(cand.outcome)),
                              Chip(label: Text('by ${cand.chosenBy}')),
                            ],
                          ),
                          if (cand.why.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(cand.why, style: theme.textTheme.bodySmall),
                          ],
                          const SizedBox(height: KwSpacing.xs),
                          KwCandidateScoreBar(
                            totalScoreOverride: cand.score,
                            breakdown: KwCandidateScoreBreakdown(
                              fixConfidence: cand.scoreBreakdown.fixConfidence,
                              partsReadiness:
                                  cand.scoreBreakdown.partsReadiness,
                              timeToVisit: cand.scoreBreakdown.timeToVisit,
                              routeCost: cand.scoreBreakdown.routeCost,
                              reliability: cand.scoreBreakdown.reliability,
                              householdFit: cand.scoreBreakdown.householdFit,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Slot Proposals, Quotes & Payments
          if (detail.slotProposals.isNotEmpty ||
              detail.quotes.isNotEmpty ||
              detail.payments.isNotEmpty) ...[
            _SectionCard(
              title: 'Slots, Quotes & Payments',
              icon: Icons.receipt_long_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final slot in detail.slotProposals)
                    Padding(
                      padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                      child: Text(
                        'Slot: ${slot.slotStart} → ${slot.slotEnd} · ${formatInrRange(slot.priceLowPaise, slot.priceHighPaise)} ${slot.accepted ? '(Accepted)' : ''}',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  for (final quote in detail.quotes) ...[
                    const SizedBox(height: KwSpacing.xs),
                    Text(
                      'Quote v${quote.version} (${quote.quoteType}) · Total ${formatInrPaise(quote.totalPaise)} · Household ${formatInrPaise(quote.householdPaise)}',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xs),
                    for (final line in quote.lines)
                      Padding(
                        padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                        child: KwMoneyLine(
                          description: line.description,
                          amountPaise: line.amountPaise,
                          payer: KwPayer.fromWire(line.payer),
                        ),
                      ),
                  ],
                  for (final pay in detail.payments) ...[
                    const SizedBox(height: KwSpacing.xs),
                    Chip(
                      avatar: const Icon(Icons.payments_rounded, size: 16),
                      label: Text(
                        'Payment ${pay.status.toUpperCase()} · ${formatInrPaise(pay.amountPaise)} via ${pay.method}',
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Confirmed Debrief
          if (detail.debrief != null) ...[
            _SectionCard(
              title: 'Technician Debrief (${detail.debrief!.status})',
              icon: Icons.summarize_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Fault found: ${detail.debrief!.extracted.faultFound}',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('Work done: ${detail.debrief!.extracted.workDone}'),
                  if (detail.debrief!.extracted.adviceForHousehold.isNotEmpty)
                    Text(
                      'Advice: ${detail.debrief!.extracted.adviceForHousehold}',
                    ),
                ],
              ),
            ),
            const SizedBox(height: KwSpacing.md),
          ],

          // Timeline
          _SectionCard(
            title: 'Case Timeline (${detail.timeline.length})',
            icon: Icons.timeline_rounded,
            child: detail.timeline.isEmpty
                ? const Text('No timeline events recorded yet.')
                : Column(
                    children: [
                      for (final ev in detail.timeline)
                        KwEventRow(
                          type: ev.type,
                          title: ev.title,
                          detail: ev.detail,
                          actor: ev.actor,
                          at: ConsoleController.parseIsoDate(ev.at),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  KwConsentGateState _findGate(List<ConsentGate> gates, int gateNum) {
    for (final g in gates) {
      if (g.gate == gateNum) {
        return KwConsentGateState(
          gate: g.gate,
          answer: KwConsentAnswer.fromWire(g.answer),
          choice: KwConsentChoice.fromWire(g.choice),
          notAskedReason: g.notAskedReason,
        );
      }
    }
    return KwConsentGateState(
      gate: gateNum,
      answer: KwConsentAnswer.notAsked,
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
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
                Icon(icon, size: 20, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            child,
          ],
        ),
      ),
    );
  }
}

class _KeyValue extends StatelessWidget {
  const _KeyValue({
    required this.label,
    required this.value,
    this.mono = false,
  });

  final String label;
  final String value;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: mono
              ? KwTheme.monoStyle(context, fontWeight: FontWeight.w600)
              : theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
        ),
      ],
    );
  }
}
