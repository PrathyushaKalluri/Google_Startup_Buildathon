import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import '../field_l10n.dart';
import 'offline_outbox.dart';

/// Complete Technician Job Brief & Field Execution screen.
///
/// Covers:
/// - Privacy-gated address/phone release + logged-read notice + Google Maps link
/// - Household complaint, Already Tried list, Fault Hypotheses with citations
/// - Tools needed & Parts ladder (`van` / `centre` / `parts_centre`) with
///   `"Needs checking"` badges for unverified parts
/// - Check-in with location (offline-capable)
/// - Parts used recorder (offline-capable)
/// - Photo/video evidence upload
/// - Firm Quote Composer with live variance vs estimate
/// - Spoken Close-Out Debrief (record/simulate -> review -> resolve unmatched -> confirm)
/// - Household OTP closure with [KwOtpInput] and calm completion state
class VisitDetailScreen extends StatefulWidget {
  const VisitDetailScreen({
    super.key,
    required this.api,
    required this.outbox,
    required this.visitId,
    this.initialJobSummary,
  });

  final KwApiClient api;
  final OfflineOutboxController outbox;
  final String visitId;
  final Map<String, dynamic>? initialJobSummary;

  @override
  State<VisitDetailScreen> createState() => _VisitDetailScreenState();
}

class _VisitDetailScreenState extends State<VisitDetailScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic> _data = const {};

  // Execution state
  String? _checkedInAt;
  bool _checkInQueued = false;
  final List<DebriefPartUsed> _recordedParts = <DebriefPartUsed>[];
  final List<String> _uploadedMedia = <String>[];
  String? _recordedOutcome;

  // Firm quote composer state
  final List<QuoteLine> _draftQuoteLines = <QuoteLine>[];
  Quote? _submittedQuote;
  bool _submittingQuote = false;
  final TextEditingController _lineDescController = TextEditingController();
  final TextEditingController _lineRupeesController = TextEditingController();
  String _lineKind = 'part';
  String _linePayer = 'household';

  // Parts used quick-add
  final TextEditingController _partNoController = TextEditingController();
  int _partQty = 1;

  // Debrief state
  Debrief? _debrief;
  bool _submittingDebrief = false;
  bool _debriefConfirmed = false;
  final Map<String, String> _resolvedUnmatched = <String, String>{};

  // OTP closure state
  String? _otpRef;
  String _otpCode = '';
  String? _otpError;
  bool _requestingOtp = false;
  bool _confirmingOtp = false;
  bool _visitClosed = false;

  @override
  void initState() {
    super.initState();
    _loadVisit();
  }

  @override
  void dispose() {
    _lineDescController.dispose();
    _lineRupeesController.dispose();
    _partNoController.dispose();
    super.dispose();
  }

  Future<void> _loadVisit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final raw = await widget.api.getVisit(widget.visitId);
      if (!mounted) return;
      _hydrateFromPayload(raw);
    } catch (e) {
      if (!mounted) return;
      if (widget.initialJobSummary != null) {
        _hydrateFromPayload(widget.initialJobSummary!);
      } else {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  void _hydrateFromPayload(Map<String, dynamic> raw) {
    final merged = <String, dynamic>{
      if (widget.initialJobSummary != null) ...widget.initialJobSummary!,
      ...raw,
    };

    // Hydrate check-in / closure / debrief if already present
    final visitMap = merged['visit'] is Map<dynamic, dynamic>
        ? Map<String, dynamic>.from(merged['visit'] as Map<dynamic, dynamic>)
        : merged;
    final checkInAt = visitMap['check_in_at']?.toString();
    final closureAt = visitMap['closure_confirmed_at']?.toString();
    final outcome = visitMap['outcome']?.toString();

    Debrief? existingDebrief;
    if (merged['debrief'] is Map<dynamic, dynamic>) {
      existingDebrief = Debrief.fromJson(
        Map<String, dynamic>.from(merged['debrief'] as Map<dynamic, dynamic>),
      );
    }

    // Seed draft quote lines from estimate if empty
    if (_draftQuoteLines.isEmpty) {
      final rawQuote = merged['estimate_quote'] ?? merged['quote'];
      if (rawQuote is Map<dynamic, dynamic>) {
        final q = Quote.fromJson(Map<String, dynamic>.from(rawQuote));
        _draftQuoteLines.addAll(q.lines);
      } else {
        _draftQuoteLines.add(
          const QuoteLine(
            kind: 'labour',
            description: 'Diagnostic & repair labour',
            amountPaise: 45000,
            payer: 'household',
          ),
        );
      }
    }

    setState(() {
      _data = merged;
      _checkedInAt = checkInAt ?? _checkedInAt;
      _recordedOutcome = outcome ?? _recordedOutcome;
      if (closureAt != null && closureAt.isNotEmpty) {
        _visitClosed = true;
      }
      if (existingDebrief != null) {
        _debrief = existingDebrief;
        _debriefConfirmed = existingDebrief.confirmedAt != null;
      }
      _loading = false;
    });
  }

  // ---------------------------------------------------------------------------
  // Derived helpers
  // ---------------------------------------------------------------------------

  String get _ticketId {
    final card = _data['card'];
    final cardId = card is Map<dynamic, dynamic> ? card['id'] : null;
    return (_data['ticket_id'] ?? cardId ?? widget.visitId).toString();
  }

  bool get _isAddressReleased {
    if (_data['address_released'] is bool) {
      return _data['address_released'] as bool;
    }
    final status = (_data['status'] ?? '').toString().toLowerCase();
    const unconfirmed = {'pending', 'proposed', 'unconfirmed', 'triage', 'new'};
    return !unconfirmed.contains(status);
  }

  Map<String, dynamic> get _householdMap {
    if (_data['household'] is Map<dynamic, dynamic>) {
      return Map<String, dynamic>.from(
        _data['household'] as Map<dynamic, dynamic>,
      );
    }
    return const {};
  }

  VisitPlan? get _visitPlan {
    if (_data['visit_plan'] is Map<dynamic, dynamic>) {
      return VisitPlan.fromJson(
        Map<String, dynamic>.from(_data['visit_plan'] as Map<dynamic, dynamic>),
      );
    }
    return null;
  }

  Diagnosis? get _diagnosis {
    if (_data['diagnosis'] is Map<dynamic, dynamic>) {
      return Diagnosis.fromJson(
        Map<String, dynamic>.from(_data['diagnosis'] as Map<dynamic, dynamic>),
      );
    }
    return null;
  }

  List<String> get _alreadyTried {
    final items = <String>[];
    final plan = _visitPlan;
    if (plan != null) {
      items.addAll(plan.alreadyTried);
    }
    if (_data['already_tried'] is List<dynamic>) {
      for (final item in _data['already_tried'] as List<dynamic>) {
        final s = item.toString();
        if (s.isNotEmpty && !items.contains(s)) items.add(s);
      }
    }
    if (_data['case_card'] is Map<dynamic, dynamic>) {
      final cc = Map<String, dynamic>.from(
        _data['case_card'] as Map<dynamic, dynamic>,
      );
      if (cc['what_was_tried'] is List<dynamic>) {
        for (final item in cc['what_was_tried'] as List<dynamic>) {
          final s = item.toString();
          if (s.isNotEmpty && !items.contains(s)) items.add(s);
        }
      }
    }
    return items;
  }

  int get _estimateTotalPaise {
    if (_data['estimate_total_paise'] is num) {
      return (_data['estimate_total_paise'] as num).toInt();
    }
    if (_data['estimate_quote'] is Map<dynamic, dynamic>) {
      final q = Quote.fromJson(
        Map<String, dynamic>.from(
          _data['estimate_quote'] as Map<dynamic, dynamic>,
        ),
      );
      return q.totalPaise;
    }
    return 85000;
  }

  int get _draftTotalPaise =>
      _draftQuoteLines.fold<int>(0, (sum, l) => sum + l.amountPaise);

  double get _variancePct {
    final est = _estimateTotalPaise;
    if (est <= 0) return 0;
    return ((_draftTotalPaise - est) / est) * 100.0;
  }

  String _googleMapsDeepLink() {
    final lat = _householdMap['lat'] ?? _data['lat'];
    final lon = _householdMap['lon'] ?? _data['lon'];
    if (lat != null && lon != null) {
      return 'https://www.google.com/maps/search/?api=1&query=$lat,$lon';
    }
    final address = (_householdMap['address_line'] ??
            _data['address_line'] ??
            _householdMap['locality'] ??
            'Hyderabad')
        .toString();
    final encoded = Uri.encodeComponent(address);
    return 'https://www.google.com/maps/search/?api=1&query=$encoded';
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  void _showMessage(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(text)),
    );
  }

  Future<void> _handleCheckIn() async {
    final lat = (_householdMap['lat'] as num?)?.toDouble() ?? 17.4483;
    final lon = (_householdMap['lon'] as num?)?.toDouble() ?? 78.3915;
    try {
      final res = await widget.outbox.submitCheckIn(
        visitId: widget.visitId,
        lat: lat,
        lon: lon,
      );
      if (!mounted) return;
      setState(() {
        if (res.queued) {
          _checkInQueued = true;
        } else {
          _checkInQueued = false;
          _checkedInAt =
              res.data?.checkInAt ?? DateTime.now().toIso8601String();
        }
      });
      _showMessage(
        res.queued
            ? 'Check-in queued offline. Sync when back online.'
            : 'Checked in at household location.',
      );
    } catch (e) {
      _showMessage('Check-in failed: $e');
    }
  }

  Future<void> _handleRecordPartUsed(String partNo, int qty) async {
    final clean = partNo.trim();
    if (clean.isEmpty) return;
    final entry = DebriefPartUsed(partNo: clean, quantity: qty);
    try {
      final res = await widget.outbox.submitPartsUsed(
        visitId: widget.visitId,
        parts: [entry],
      );
      if (!mounted) return;
      setState(() {
        _recordedParts.add(entry);
        _partNoController.clear();
        _partQty = 1;
      });
      _showMessage(
        res.queued
            ? 'Part $clean (×$qty) queued offline.'
            : 'Recorded $clean (×$qty).',
      );
    } catch (e) {
      _showMessage('Could not record part: $e');
    }
  }

  Future<void> _handleUploadEvidence({required bool isVideo}) async {
    if (widget.outbox.isOffline) {
      _showMessage('Reconnect to upload photo or video evidence.');
      return;
    }
    final ts = DateTime.now().millisecondsSinceEpoch;
    final filename = isVideo ? 'visit_$ts.mp4' : 'visit_$ts.jpg';
    final mime = isVideo ? 'video/mp4' : 'image/jpeg';
    try {
      final resp = await widget.api.getMediaUploadUrl(
        widget.visitId,
        filename: filename,
        mimeType: mime,
      );
      if (!mounted) return;
      final ref = (resp['media_ref'] ?? resp['upload_url'] ?? filename).toString();
      setState(() {
        _uploadedMedia.add('$filename ($ref)');
      });
      _showMessage('Uploaded $filename');
    } catch (e) {
      _showMessage('Upload failed: $e');
    }
  }

  void _addDraftQuoteLine() {
    final desc = _lineDescController.text.trim();
    final rupees = double.tryParse(_lineRupeesController.text.trim());
    if (desc.isEmpty || rupees == null || rupees < 0) {
      _showMessage('Enter a description and valid amount in ₹.');
      return;
    }
    setState(() {
      _draftQuoteLines.add(
        QuoteLine(
          kind: _lineKind,
          description: desc,
          amountPaise: (rupees * 100).round(),
          payer: _linePayer,
        ),
      );
      _lineDescController.clear();
      _lineRupeesController.clear();
    });
  }

  Future<void> _submitFirmQuote() async {
    if (_draftQuoteLines.isEmpty) return;
    setState(() => _submittingQuote = true);
    try {
      final quote = await widget.api.createFirmQuote(
        _ticketId,
        lines: _draftQuoteLines,
      );
      if (!mounted) return;
      setState(() {
        _submittedQuote = quote;
        _submittingQuote = false;
      });
      _showMessage('Firm quote sent to household.');
    } catch (e) {
      if (!mounted) return;
      setState(() => _submittingQuote = false);
      _showMessage('Could not submit quote: $e');
    }
  }

  Future<void> _handleSubmitVoiceDebrief() async {
    final lang = KwStrings.of(context).languageCode;
    setState(() => _submittingDebrief = true);
    try {
      final res = await widget.outbox.submitDebrief(
        visitId: widget.visitId,
        mediaRef: 'voice-note-${widget.visitId}-$lang.m4a',
        language: lang,
      );
      if (!mounted) return;
      setState(() {
        _submittingDebrief = false;
        if (!res.queued && res.data != null) {
          _debrief = res.data;
          _debriefConfirmed = res.data!.confirmedAt != null;
        }
      });
      if (res.queued) {
        _showMessage('Voice debrief queued offline.');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _submittingDebrief = false);
      _showMessage('Debrief submission failed: $e');
    }
  }

  Future<void> _handleConfirmDebrief() async {
    final current = _debrief;
    if (current == null) return;

    final updatedParts = <DebriefPartUsed>[
      ...current.extracted.partsUsed,
      for (final entry in _resolvedUnmatched.entries)
        if (entry.value.trim().isNotEmpty)
          DebriefPartUsed(partNo: entry.value.trim(), quantity: 1),
    ];

    final extracted = DebriefExtracted(
      faultFound: current.extracted.faultFound,
      workDone: current.extracted.workDone,
      partsUsed: updatedParts,
      adviceForHousehold: current.extracted.adviceForHousehold,
      applianceNotes: current.extracted.applianceNotes,
      followUpNeeded: current.extracted.followUpNeeded,
    );

    setState(() => _submittingDebrief = true);
    try {
      final confirmed = await widget.api.confirmDebrief(
        widget.visitId,
        extracted: extracted,
      );
      if (!mounted) return;
      setState(() {
        _debrief = confirmed;
        _debriefConfirmed = true;
        _submittingDebrief = false;
      });
      _showMessage('Debrief confirmed and logged.');
    } catch (e) {
      if (!mounted) return;
      setState(() => _submittingDebrief = false);
      _showMessage('Could not confirm debrief: $e');
    }
  }

  Future<void> _handleRecordOutcome(String outcome) async {
    try {
      final res = await widget.outbox.submitOutcome(
        visitId: widget.visitId,
        outcome: outcome,
      );
      if (!mounted) return;
      setState(() => _recordedOutcome = outcome);
      _showMessage(
        res.queued
            ? 'Outcome "$outcome" queued offline.'
            : 'Outcome "$outcome" recorded.',
      );
    } catch (e) {
      _showMessage('Could not record outcome: $e');
    }
  }

  Future<void> _handleRequestCloseOtp() async {
    setState(() {
      _requestingOtp = true;
      _otpError = null;
    });
    try {
      final resp = await widget.api.requestCloseOtp(widget.visitId);
      if (!mounted) return;
      setState(() {
        _otpRef = (resp['otp_ref'] ?? resp['ref'] ?? 'otp-ref').toString();
        _requestingOtp = false;
      });
      _showMessage('Closure OTP sent to household.');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _requestingOtp = false;
        _otpError = e.toString();
      });
    }
  }

  Future<void> _handleConfirmCloseOtp() async {
    if (_otpRef == null || _otpCode.length < 6) {
      setState(() => _otpError = 'Enter all 6 OTP digits from the household.');
      return;
    }
    setState(() {
      _confirmingOtp = true;
      _otpError = null;
    });
    try {
      await widget.api.confirmCloseOtp(
        widget.visitId,
        otpRef: _otpRef!,
        code: _otpCode,
      );
      if (!mounted) return;
      setState(() {
        _confirmingOtp = false;
        _visitClosed = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _confirmingOtp = false;
        _otpError = e.toString();
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = FieldStrings.of(context);
    final kwStrings = KwStrings.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('Visit ${widget.visitId}'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loadVisit,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Column(
        children: [
          OfflineSyncBanner(
            outbox: widget.outbox,
            onSynced: _loadVisit,
          ),
          Expanded(
            child: _loading
                ? const Padding(
                    padding: EdgeInsets.all(KwSpacing.md),
                    child: KwSkeletonLoader(lines: 8, height: 18),
                  )
                : _error != null
                    ? KwErrorState(body: _error, onRetry: _loadVisit)
                    : ListView(
                        padding: const EdgeInsets.all(KwSpacing.md),
                        children: [
                          if (_visitClosed) ...[
                            _buildClosedCalmBanner(theme, kw),
                            const SizedBox(height: KwSpacing.md),
                          ],
                          _buildHeaderAndPrivacyCard(theme, cs, kw, strings),
                          const SizedBox(height: KwSpacing.md),
                          _buildAlreadyTriedCard(theme, cs, kw, strings),
                          const SizedBox(height: KwSpacing.md),
                          _buildHypothesesCard(theme, cs, strings),
                          const SizedBox(height: KwSpacing.md),
                          _buildToolsAndPartsCard(
                            theme,
                            cs,
                            kw,
                            strings,
                            kwStrings,
                          ),
                          const SizedBox(height: KwSpacing.md),
                          _buildExecutionCard(theme, cs, kw, strings),
                          const SizedBox(height: KwSpacing.md),
                          _buildFirmQuoteCard(theme, cs, kw, strings),
                          const SizedBox(height: KwSpacing.md),
                          _buildDebriefCard(theme, cs, kw, strings, kwStrings),
                          const SizedBox(height: KwSpacing.md),
                          _buildOtpClosureCard(theme, cs, kw, strings),
                          const SizedBox(height: KwSpacing.xl),
                        ],
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildClosedCalmBanner(ThemeData theme, KwSemanticColors kw) {
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        key: const Key('kw_visit_closed_banner'),
        padding: const EdgeInsets.all(KwSpacing.md),
        decoration: BoxDecoration(
          color: kw.verified.container,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(color: kw.verified.accent, width: 1.5),
        ),
        child: Row(
          children: [
            Icon(
              Icons.check_circle_rounded,
              size: 28,
              color: kw.verified.onContainer,
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Visit closed calmly',
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: kw.verified.onContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    'Household OTP confirmed and service record updated.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: kw.verified.onContainer,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeaderAndPrivacyCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
  ) {
    final urgency = KwUrgencyClass.fromWire(_data['urgency_class']?.toString());
    final complaint = (_data['complaint_summary'] ??
            (_data['case_card'] is Map<dynamic, dynamic>
                ? (_data['case_card'] as Map<dynamic, dynamic>)['summary']
                : null) ??
            'Household service visit')
        .toString();
    final householdName = (_householdMap['display_name'] ?? 'Household').toString();
    final locality = (_householdMap['locality'] ?? _data['locality'] ?? '').toString();
    final address = (_householdMap['address_line'] ?? _data['address_line'] ?? '').toString();
    final phone = (_householdMap['phone'] ??
            _householdMap['phone_masked'] ??
            _data['phone'] ??
            '')
        .toString();
    final driveMin = (_data['drive_minutes'] as num?)?.toInt();
    final distKm = (_data['distance_km'] as num?)?.toDouble();

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
                KwUrgencyChip(urgency: urgency),
                if (driveMin != null && distKm != null)
                  KwRouteEtaBar(
                    driveMinutes: driveMin,
                    distanceKm: distKm,
                    isStaticFallback: _data['route_static_fallback'] == true,
                    destinationLabel: locality.isNotEmpty ? locality : null,
                  ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            Text(
              'What the household reported',
              style: theme.textTheme.labelMedium?.copyWith(
                color: cs.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.xxs),
            Text(
              complaint,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const Divider(height: KwSpacing.lg),
            // Privacy-gated contact section
            Row(
              children: [
                Icon(
                  _isAddressReleased
                      ? Icons.location_on_rounded
                      : Icons.lock_outline_rounded,
                  size: 18,
                  color: _isAddressReleased
                      ? cs.primary
                      : kw.needsChecking.accent,
                ),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    '$householdName${locality.isNotEmpty ? ' · $locality' : ''}',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            if (!_isAddressReleased)
              Container(
                key: const Key('kw_address_masked_notice'),
                width: double.infinity,
                padding: const EdgeInsets.all(KwSpacing.sm),
                decoration: BoxDecoration(
                  color: kw.needsChecking.container,
                  borderRadius: KwShapes.radiusSmall,
                ),
                child: Text(
                  strings.addressHiddenNotice,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: kw.needsChecking.onContainer,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              )
            else ...[
              if (address.isNotEmpty)
                Text(address, style: theme.textTheme.bodyMedium),
              if (phone.isNotEmpty) ...[
                const SizedBox(height: KwSpacing.xxs),
                Text(
                  'Phone: $phone',
                  style: KwTheme.monoStyle(context),
                ),
              ],
              const SizedBox(height: KwSpacing.sm),
              OutlinedButton.icon(
                key: const Key('kw_maps_link_button'),
                onPressed: () {
                  final url = _googleMapsDeepLink();
                  Clipboard.setData(ClipboardData(text: url));
                  _showMessage('Google Maps link ready: $url');
                },
                icon: const Icon(Icons.map_outlined),
                label: Text(strings.openInMaps),
              ),
            ],
            const SizedBox(height: KwSpacing.xs),
            Row(
              children: [
                Icon(
                  Icons.visibility_outlined,
                  size: 15,
                  color: cs.onSurfaceVariant,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    strings.privacyLoggedNotice,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
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

  Widget _buildAlreadyTriedCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
  ) {
    final tried = _alreadyTried;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.history_rounded, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    strings.alreadyTriedTitle,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            if (tried.isEmpty)
              Text(
                'No self-fix steps recorded before this visit.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              )
            else
              for (final step in tried)
                Padding(
                  padding: const EdgeInsets.only(bottom: KwSpacing.xs),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.check_circle_outline_rounded,
                        size: 18,
                        color: kw.verified.accent,
                      ),
                      const SizedBox(width: KwSpacing.xs),
                      Expanded(
                        child: Text(step, style: theme.textTheme.bodyMedium),
                      ),
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Widget _buildHypothesesCard(
    ThemeData theme,
    ColorScheme cs,
    FieldStrings strings,
  ) {
    final diagnosis = _diagnosis;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.biotech_outlined, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  strings.hypothesesTitle,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            if (diagnosis == null || diagnosis.hypotheses.isEmpty)
              KwConfidenceMeter(
                probability: 0.0,
                abstained: true,
                abstentionReason: diagnosis?.reason,
              )
            else
              for (final h in diagnosis.hypotheses) ...[
                KwConfidenceMeter(
                  probability: h.probability,
                  label: h.label,
                  abstained: diagnosis.abstained,
                  abstentionReason: diagnosis.reason,
                  evidenceCount: h.evidence.length,
                ),
                if (h.citations.isNotEmpty) ...[
                  const SizedBox(height: KwSpacing.xs),
                  Wrap(
                    spacing: KwSpacing.xs,
                    runSpacing: KwSpacing.xs,
                    children: [
                      for (final c in h.citations)
                        KwSourceCitationChip(
                          docTitle: c.docTitle,
                          snippet: c.snippet,
                          page: c.page,
                          uri: c.uri,
                        ),
                    ],
                  ),
                ],
                const SizedBox(height: KwSpacing.md),
              ],
          ],
        ),
      ),
    );
  }

  Widget _buildToolsAndPartsCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
    KwStrings kwStrings,
  ) {
    final plan = _visitPlan;
    final tools = plan?.toolsNeeded ?? const <String>[];
    final parts = plan?.parts ?? const <VisitPlanPart>[];

    String ladderLabel(String ladder) {
      return switch (ladder.toLowerCase()) {
        'van' => 'Van',
        'parts_centre' => 'Parts Centre',
        _ => 'Centre',
      };
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.handyman_outlined, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  strings.toolsAndPartsTitle,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            if (tools.isNotEmpty) ...[
              const SizedBox(height: KwSpacing.sm),
              Text(
                'Tools needed',
                style: theme.textTheme.labelMedium?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: KwSpacing.xxs),
              Wrap(
                spacing: KwSpacing.xs,
                runSpacing: KwSpacing.xs,
                children: [
                  for (final t in tools)
                    Chip(
                      label: Text(t),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
            ],
            const SizedBox(height: KwSpacing.sm),
            Text(
              'Parts ladder',
              style: theme.textTheme.labelMedium?.copyWith(
                color: cs.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            if (parts.isEmpty)
              Text(
                'No specific parts pre-assigned.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: cs.onSurfaceVariant,
                ),
              )
            else
              for (final p in parts)
                Container(
                  margin: const EdgeInsets.only(bottom: KwSpacing.xs),
                  padding: const EdgeInsets.all(KwSpacing.sm),
                  decoration: BoxDecoration(
                    color: p.ready
                        ? cs.surfaceContainerHighest.withValues(alpha: 0.45)
                        : kw.needsChecking.container.withValues(alpha: 0.5),
                    borderRadius: KwShapes.radiusSmall,
                    border: Border.all(
                      color: p.ready
                          ? cs.outlineVariant
                          : kw.needsChecking.accent,
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${p.name} (×${p.quantity})',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              '${p.partNo} · ${ladderLabel(p.sourceLadder)}',
                              style: KwTheme.monoStyle(
                                context,
                                fontSize: theme.textTheme.labelSmall?.fontSize,
                                color: cs.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (!p.ready)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: KwSpacing.xs,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: kw.needsChecking.container,
                            borderRadius: KwShapes.radiusSmall,
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.warning_amber_rounded,
                                size: 15,
                                color: kw.needsChecking.onContainer,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                kwStrings.needsChecking,
                                style: theme.textTheme.labelSmall?.copyWith(
                                  color: kw.needsChecking.onContainer,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        Icon(
                          Icons.verified_rounded,
                          size: 20,
                          color: kw.verified.accent,
                        ),
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Widget _buildExecutionCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'On-Site Execution',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.sm),
            // 1. Check-in
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                key: const Key('kw_checkin_button'),
                onPressed: _handleCheckIn,
                icon: Icon(
                  _checkedInAt != null
                      ? Icons.check_circle_rounded
                      : Icons.my_location_rounded,
                ),
                label: Text(
                  _checkInQueued
                      ? 'Check-in queued offline'
                      : _checkedInAt != null
                          ? 'Checked in'
                          : strings.checkInAction,
                ),
              ),
            ),
            const Divider(height: KwSpacing.lg),
            // 2. Parts Used recorder
            Text(
              strings.partsUsedAction,
              style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    key: const Key('kw_part_no_input'),
                    controller: _partNoController,
                    decoration: const InputDecoration(
                      labelText: 'Part number (SKU)',
                      hintText: 'e.g. AV-CAP-45UF',
                    ),
                  ),
                ),
                const SizedBox(width: KwSpacing.xs),
                IconButton.outlined(
                  tooltip: 'Decrease quantity',
                  onPressed:
                      _partQty > 1 ? () => setState(() => _partQty -= 1) : null,
                  icon: const Icon(Icons.remove_rounded),
                ),
                Text(
                  '$_partQty',
                  style: KwTheme.monoStyle(context, fontSize: 16),
                ),
                IconButton.outlined(
                  tooltip: 'Increase quantity',
                  onPressed: () => setState(() => _partQty += 1),
                  icon: const Icon(Icons.add_rounded),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            FilledButton.tonalIcon(
              key: const Key('kw_record_part_button'),
              onPressed: () =>
                  _handleRecordPartUsed(_partNoController.text, _partQty),
              icon: const Icon(Icons.inventory_2_outlined),
              label: const Text('Record part used'),
            ),
            if (_recordedParts.isNotEmpty) ...[
              const SizedBox(height: KwSpacing.xs),
              Wrap(
                spacing: KwSpacing.xs,
                children: [
                  for (final p in _recordedParts)
                    Chip(label: Text('${p.partNo} ×${p.quantity}')),
                ],
              ),
            ],
            const Divider(height: KwSpacing.lg),
            // 3. Photo / Video Evidence upload
            Text(
              strings.evidenceAction,
              style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              children: [
                OutlinedButton.icon(
                  key: const Key('kw_upload_photo_button'),
                  onPressed: () => _handleUploadEvidence(isVideo: false),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Add photo'),
                ),
                OutlinedButton.icon(
                  key: const Key('kw_upload_video_button'),
                  onPressed: () => _handleUploadEvidence(isVideo: true),
                  icon: const Icon(Icons.videocam_outlined),
                  label: const Text('Add video'),
                ),
              ],
            ),
            if (_uploadedMedia.isNotEmpty) ...[
              const SizedBox(height: KwSpacing.xs),
              for (final m in _uploadedMedia)
                Text(
                  'Uploaded: $m',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: kw.verified.accent,
                  ),
                ),
            ],
            const Divider(height: KwSpacing.lg),
            // 4. Visit outcome quick-select
            Text(
              'Visit outcome',
              style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              children: [
                for (final outcome in const [
                  'fixed',
                  'parts_needed',
                  'no_access',
                ])
                  ChoiceChip(
                    label: Text(outcome.replaceAll('_', ' ')),
                    selected: _recordedOutcome == outcome,
                    onSelected: (_) => _handleRecordOutcome(outcome),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFirmQuoteCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
  ) {
    final est = _estimateTotalPaise;
    final total = _draftTotalPaise;
    final variance = _variancePct;
    final varianceText =
        '${variance >= 0 ? '+' : ''}${variance.toStringAsFixed(1)}%';
    final isHighVariance = variance.abs() > 15.0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.receipt_long_outlined, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    strings.firmQuoteTitle,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: KwSpacing.xs,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: isHighVariance
                        ? kw.needsChecking.container
                        : kw.verified.container,
                    borderRadius: KwShapes.radiusSmall,
                  ),
                  child: Text(
                    'Variance $varianceText vs est ${formatInrPaise(est)}',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: isHighVariance
                          ? kw.needsChecking.onContainer
                          : kw.verified.onContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            for (var i = 0; i < _draftQuoteLines.length; i++) ...[
              KwMoneyLine(
                description: _draftQuoteLines[i].description,
                amountPaise: _draftQuoteLines[i].amountPaise,
                payer: KwPayer.fromWire(_draftQuoteLines[i].payer),
              ),
              const SizedBox(height: KwSpacing.xs),
            ],
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextField(
                    controller: _lineDescController,
                    decoration: const InputDecoration(
                      labelText: 'Line description',
                    ),
                  ),
                ),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: TextField(
                    controller: _lineRupeesController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: '₹ Amount',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                DropdownButton<String>(
                  value: _lineKind,
                  items: const [
                    DropdownMenuItem(value: 'part', child: Text('Part')),
                    DropdownMenuItem(value: 'labour', child: Text('Labour')),
                    DropdownMenuItem(value: 'visit', child: Text('Visit fee')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => _lineKind = v);
                  },
                ),
                DropdownButton<String>(
                  value: _linePayer,
                  items: const [
                    DropdownMenuItem(
                      value: 'household',
                      child: Text('Household'),
                    ),
                    DropdownMenuItem(value: 'brand', child: Text('Brand')),
                    DropdownMenuItem(value: 'plan', child: Text('Plan')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => _linePayer = v);
                  },
                ),
                OutlinedButton.icon(
                  onPressed: _addDraftQuoteLine,
                  icon: const Icon(Icons.add_rounded),
                  label: const Text('Add line'),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Firm total: ${formatInrPaise(total)}',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                FilledButton(
                  key: const Key('kw_submit_quote_button'),
                  onPressed: _submittingQuote ? null : _submitFirmQuote,
                  child: Text(
                    _submittedQuote != null
                        ? 'Quote sent (v${_submittedQuote!.version})'
                        : 'Send firm quote',
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDebriefCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
    KwStrings kwStrings,
  ) {
    final debrief = _debrief;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.mic_none_rounded, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    strings.debriefTitle,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            FilledButton.tonalIcon(
              key: const Key('kw_record_debrief_button'),
              onPressed: _submittingDebrief ? null : _handleSubmitVoiceDebrief,
              icon: const Icon(Icons.record_voice_over_rounded),
              label: Text(
                debrief == null
                    ? 'Record / simulate voice note'
                    : 'Re-record voice debrief',
              ),
            ),
            if (debrief != null) ...[
              const SizedBox(height: KwSpacing.md),
              if (debrief.transcript.isNotEmpty) ...[
                Text(
                  'Transcript (${debrief.language})',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: cs.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: KwSpacing.xxs),
                Text(debrief.transcript, style: theme.textTheme.bodyMedium),
                const SizedBox(height: KwSpacing.sm),
              ],
              _debriefRow(theme, 'Fault found', debrief.extracted.faultFound),
              _debriefRow(theme, 'Work done', debrief.extracted.workDone),
              _debriefRow(
                theme,
                'Household advice',
                debrief.extracted.adviceForHousehold,
              ),
              if (debrief.extracted.partsUsed.isNotEmpty) ...[
                const SizedBox(height: KwSpacing.xs),
                Wrap(
                  spacing: KwSpacing.xs,
                  children: [
                    for (final p in debrief.extracted.partsUsed)
                      Chip(label: Text('${p.partNo} ×${p.quantity}')),
                  ],
                ),
              ],
              if (debrief.unresolved.isNotEmpty && !_debriefConfirmed) ...[
                const SizedBox(height: KwSpacing.sm),
                Container(
                  key: const Key('kw_debrief_needs_checking'),
                  width: double.infinity,
                  padding: const EdgeInsets.all(KwSpacing.sm),
                  decoration: BoxDecoration(
                    color: kw.needsChecking.container,
                    borderRadius: KwShapes.radiusSmall,
                    border: Border.all(color: kw.needsChecking.accent),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.warning_amber_rounded,
                            size: 18,
                            color: kw.needsChecking.onContainer,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            kwStrings.needsChecking,
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: kw.needsChecking.onContainer,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: KwSpacing.xs),
                      for (final rawPart in debrief.unresolved) ...[
                        Text(
                          'Unmatched part: $rawPart',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: kw.needsChecking.onContainer,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: KwSpacing.xxs),
                        TextField(
                          key: Key('kw_resolve_part_$rawPart'),
                          decoration: InputDecoration(
                            labelText: 'Verified part number for "$rawPart"',
                            hintText: 'Leave blank to omit or enter SKU',
                          ),
                          onChanged: (v) {
                            _resolvedUnmatched[rawPart] = v;
                          },
                        ),
                        const SizedBox(height: KwSpacing.xs),
                      ],
                    ],
                  ),
                ),
              ],
              const SizedBox(height: KwSpacing.sm),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const Key('kw_confirm_debrief_button'),
                  onPressed: (_submittingDebrief || _debriefConfirmed)
                      ? null
                      : _handleConfirmDebrief,
                  icon: Icon(
                    _debriefConfirmed
                        ? Icons.check_circle_rounded
                        : Icons.done_all_rounded,
                  ),
                  label: Text(
                    _debriefConfirmed
                        ? 'Debrief confirmed'
                        : 'Confirm close-out debrief',
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _debriefRow(ThemeData theme, String label, String value) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: KwSpacing.xs),
      child: RichText(
        text: TextSpan(
          style: theme.textTheme.bodyMedium,
          children: [
            TextSpan(
              text: '$label: ',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }

  Widget _buildOtpClosureCard(
    ThemeData theme,
    ColorScheme cs,
    KwSemanticColors kw,
    FieldStrings strings,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.verified_user_outlined, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Text(
                  strings.otpClosureTitle,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            if (_visitClosed)
              Text(
                'Closure OTP verified. Thank you for completing this visit.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: kw.verified.accent,
                  fontWeight: FontWeight.w600,
                ),
              )
            else ...[
              if (_otpRef == null)
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    key: const Key('kw_request_otp_button'),
                    onPressed: _requestingOtp ? null : _handleRequestCloseOtp,
                    icon: const Icon(Icons.sms_outlined),
                    label: const Text('Request closure OTP'),
                  ),
                )
              else ...[
                KwOtpInput(
                  key: const Key('kw_close_otp_input'),
                  errorText: _otpError,
                  onChanged: (v) => setState(() {
                    _otpCode = v;
                    _otpError = null;
                  }),
                  onCompleted: (v) => setState(() {
                    _otpCode = v;
                    _otpError = null;
                  }),
                ),
                const SizedBox(height: KwSpacing.md),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    key: const Key('kw_confirm_otp_button'),
                    onPressed: _confirmingOtp ? null : _handleConfirmCloseOtp,
                    icon: const Icon(Icons.lock_open_rounded),
                    label: const Text('Confirm OTP & close visit'),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
