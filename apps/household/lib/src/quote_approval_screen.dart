import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'household_l10n.dart';

/// Surface 5: Quote Approval, Payment & OTP Closure
/// (routes `/quotes/:token` and `/otp/:token`).
///
/// Loads `GET /v1/public/quotes/{token}`, renders line items via [KwMoneyLine]
/// (including GST, covered vs household share, and `"Needs checking"` for
/// unmatched parts), approves via `POST /v1/public/quotes/{token}/approve`,
/// initiates Google Pay (TEST) or UPI Intent via
/// `POST /v1/public/quotes/{token}/pay-intent`, polls status, provides
/// `PAYMENT_MODE=sandbox` Success/Failure controls via
/// `POST /v1/public/quotes/{token}/payment/sandbox-complete`, always displays
/// **"Payment does not close the job — only your OTP closes the repair."**,
/// and completes closure via [KwOtpInput] -> `POST /v1/public/otp/{token}/confirm`.
class QuoteApprovalScreen extends StatefulWidget {
  const QuoteApprovalScreen({
    super.key,
    required this.token,
    required this.apiClient,
    required this.activeCentre,
    this.otpOnly = false,
  });

  final String token;
  final KwApiClient apiClient;
  final KwCentreIdentity activeCentre;
  final bool otpOnly;

  @override
  State<QuoteApprovalScreen> createState() => _QuoteApprovalScreenState();
}

class _QuoteApprovalScreenState extends State<QuoteApprovalScreen> {
  bool _loading = true;
  String? _error;

  Quote? _quote;
  List<Map<String, dynamic>> _rawLines = const [];
  String? _centreName;
  String? _applianceSummary;

  bool _approving = false;
  bool _creatingPayment = false;
  bool _completingSandbox = false;
  PaymentIntent? _paymentIntent;
  bool _showGooglePaySheet = false;
  String? _paymentNotice;
  Timer? _pollTimer;

  String _otpCode = '';
  bool _submittingOtp = false;
  String? _otpError;
  bool _jobClosed = false;
  String? _closureReceiptRef;

  @override
  void initState() {
    super.initState();
    _centreName = widget.activeCentre.name;
    if (widget.otpOnly) {
      _loading = false;
    } else {
      unawaited(_loadQuote());
    }
  }

  @override
  void didUpdateWidget(covariant QuoteApprovalScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.token != widget.token || oldWidget.otpOnly != widget.otpOnly) {
      if (widget.otpOnly) {
        setState(() {
          _loading = false;
          _error = null;
        });
      } else {
        unawaited(_loadQuote());
      }
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadQuote() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final raw = await widget.apiClient.getPublicQuote(widget.token);
      if (!mounted) return;
      final quoteJson = raw['quote'] is Map
          ? (raw['quote'] as Map<dynamic, dynamic>)
              .map((k, v) => MapEntry(k.toString(), v))
          : raw;
      final parsedQuote = Quote.fromJson(quoteJson);
      final rawLinesList = quoteJson['lines'] is List
          ? (quoteJson['lines'] as List<dynamic>)
              .whereType<Map<dynamic, dynamic>>()
              .map((m) => m.map((k, v) => MapEntry(k.toString(), v)))
              .toList()
          : const <Map<String, dynamic>>[];

      PaymentIntent? existingPayment;
      if (raw['payment'] is Map) {
        existingPayment = PaymentIntent.fromJson(
          (raw['payment'] as Map<dynamic, dynamic>)
              .map((k, v) => MapEntry(k.toString(), v)),
        );
      }

      setState(() {
        _quote = parsedQuote;
        _rawLines = rawLinesList;
        _paymentIntent = existingPayment ?? _paymentIntent;
        _centreName =
            raw['centre_name']?.toString() ?? widget.activeCentre.name;
        _applianceSummary = raw['appliance_summary']?.toString();
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not load quote details for this link.';
        _loading = false;
      });
    }
  }

  Future<void> _approveQuote() async {
    setState(() {
      _approving = true;
      _paymentNotice = null;
    });
    try {
      final updated = await widget.apiClient.approvePublicQuote(widget.token);
      if (!mounted) return;
      setState(() {
        _quote = updated;
        _approving = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _approving = false;
        _paymentNotice = 'Could not approve quote right now. Please retry.';
      });
    }
  }

  Future<void> _initiatePayment(String method) async {
    setState(() {
      _creatingPayment = true;
      _paymentNotice = null;
    });
    try {
      final intent = await widget.apiClient.createPayIntent(
        widget.token,
        method: method,
      );
      if (!mounted) return;
      setState(() {
        _paymentIntent = intent;
        _creatingPayment = false;
        _showGooglePaySheet = method == 'google_pay';
      });
      _startPaymentPolling();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _creatingPayment = false;
        _paymentNotice = 'Could not start payment intent. Please try again.';
      });
    }
  }

  void _startPaymentPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      unawaited(_pollPaymentStatus());
    });
  }

  Future<void> _pollPaymentStatus() async {
    if (!mounted) return;
    try {
      final latest = await widget.apiClient.getPublicPayment(widget.token);
      if (!mounted) return;
      setState(() {
        _paymentIntent = latest;
      });
      if (latest.status == 'paid' || latest.status == 'failed') {
        _pollTimer?.cancel();
      }
    } catch (_) {
      // Non-fatal polling error; user can retry or use sandbox controls.
    }
  }

  Future<void> _sandboxComplete(String result) async {
    final intent = _paymentIntent;
    if (intent == null || _completingSandbox) return;
    setState(() {
      _completingSandbox = true;
      _paymentNotice = null;
    });
    try {
      final updated = await widget.apiClient.sandboxCompletePayment(
        widget.token,
        paymentId: intent.id,
        result: result,
        reason: result == 'failure' ? 'simulated_bank_decline' : null,
      );
      if (!mounted) return;
      _pollTimer?.cancel();
      setState(() {
        _paymentIntent = updated;
        _completingSandbox = false;
        _showGooglePaySheet = false;
        _paymentNotice = updated.status == 'paid'
            ? 'Test payment confirmed (${updated.paymentRef ?? updated.id}). Now enter your 6-digit OTP to close the repair.'
            : 'Test payment marked failed. You can retry with Google Pay or UPI Intent.';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _completingSandbox = false;
        _paymentNotice = 'Sandbox completion request failed. Please retry.';
      });
    }
  }

  Future<void> _confirmOtp([String? submittedCode]) async {
    final code = (submittedCode ?? _otpCode).trim();
    if (code.length < 6 || _submittingOtp) return;
    setState(() {
      _submittingOtp = true;
      _otpError = null;
    });
    try {
      final res = await widget.apiClient.confirmPublicOtp(
        widget.token,
        code: code,
      );
      if (!mounted) return;
      setState(() {
        _submittingOtp = false;
        _jobClosed = true;
        _closureReceiptRef =
            (res['ticket_id'] ?? res['visit_id'] ?? res['status'] ?? 'CLOSED')
                .toString();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submittingOtp = false;
        _otpError =
            'OTP did not match or expired. Check the 6-digit code and try again.';
      });
    }
  }

  bool _isNeedsCheckingLine(QuoteLine line, int index) {
    if (line.kind.toLowerCase() == 'unmatched' ||
        line.kind.toLowerCase() == 'compatibility_unverified') {
      return true;
    }
    if (index < _rawLines.length) {
      final raw = _rawLines[index];
      if (raw['needs_checking'] == true ||
          raw['compatibility_unverified'] == true ||
          raw['status']?.toString() == 'needs_checking') {
        return true;
      }
    }
    return false;
  }

  String? _partNoForLine(int index) {
    if (index < _rawLines.length) {
      return _rawLines[index]['part_no']?.toString();
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final hStrings = HouseholdStrings.of(context);

    if (_loading) {
      return Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: const Padding(
            padding: EdgeInsets.all(KwSpacing.lg),
            child: KwSkeletonLoader(lines: 5, height: 18),
          ),
        ),
      );
    }

    if (_error != null) {
      return KwErrorState(
        title: 'Quote unavailable',
        body: _error,
        onRetry: _loadQuote,
      );
    }

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 740),
        child: ListView(
          padding: const EdgeInsets.all(KwSpacing.md),
          children: [
            _buildOtpBoundaryBanner(context, hStrings),
            const SizedBox(height: KwSpacing.sm),
            if (!widget.otpOnly && _quote != null) ...[
              _buildQuoteCard(context, hStrings, _quote!),
              const SizedBox(height: KwSpacing.md),
              if (_quote!.approvedAt != null) ...[
                _buildPaymentCard(context, hStrings, _quote!),
                const SizedBox(height: KwSpacing.md),
              ],
            ],
            _buildOtpClosureCard(context, hStrings),
          ],
        ),
      ),
    );
  }

  Widget _buildOtpBoundaryBanner(
    BuildContext context,
    HouseholdStrings hStrings,
  ) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.sm),
        decoration: BoxDecoration(
          color: kw.standard.container,
          borderRadius: KwShapes.radiusMedium,
          border: Border.all(color: kw.standard.accent, width: 1.5),
        ),
        child: Row(
          children: [
            Icon(Icons.verified_user_rounded, color: kw.standard.onContainer),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Text(
                hStrings.paymentBannerText,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: kw.standard.onContainer,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuoteCard(
    BuildContext context,
    HouseholdStrings hStrings,
    Quote quote,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final isApproved = quote.approvedAt != null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${_centreName ?? widget.activeCentre.name} · ${quote.quoteType.toUpperCase()}',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      if (_applianceSummary != null)
                        Text(
                          _applianceSummary!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ),
                ),
                if (isApproved)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: kw.verified.container,
                      borderRadius: KwShapes.radiusFull,
                    ),
                    child: Text(
                      hStrings.quoteApprovedBadge,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: kw.verified.onContainer,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            for (var i = 0; i < quote.lines.length; i++) ...[
              KwMoneyLine(
                description: quote.lines[i].description,
                amountPaise: quote.lines[i].amountPaise,
                payer: KwPayer.fromWire(quote.lines[i].payer),
                partNo: _partNoForLine(i),
                needsChecking: _isNeedsCheckingLine(quote.lines[i], i),
              ),
              const SizedBox(height: KwSpacing.xs),
            ],
            const Divider(height: KwSpacing.lg),
            _SummaryAmountRow(
              label: 'Total (incl. GST)',
              amountPaise: quote.totalPaise,
            ),
            const SizedBox(height: 4),
            _SummaryAmountRow(
              label: 'Covered (Brand / Plan)',
              amountPaise: quote.coveredPaise,
              toneColor: kw.verified.accent,
            ),
            const SizedBox(height: 4),
            _SummaryAmountRow(
              label: 'Household payable share',
              amountPaise: quote.householdPaise,
              bold: true,
            ),
            if (!isApproved) ...[
              const SizedBox(height: KwSpacing.md),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _approving ? null : _approveQuote,
                  icon: const Icon(Icons.thumb_up_alt_rounded),
                  label: Text(
                    _approving ? 'Approving…' : hStrings.approveQuoteLabel,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPaymentCard(
    BuildContext context,
    HouseholdStrings hStrings,
    Quote quote,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final intent = _paymentIntent;
    final isPaid = intent?.status == 'paid';
    final isFailed = intent?.status == 'failed';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.payments_rounded, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    'Payment · ${formatInrPaise(quote.householdPaise, showZeroDecimals: true)}',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (intent != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: isPaid
                          ? kw.verified.container
                          : isFailed
                              ? kw.declined.container
                              : kw.standard.container,
                      borderRadius: KwShapes.radiusFull,
                    ),
                    child: Text(
                      intent.status.toUpperCase(),
                      style: KwTheme.monoStyle(
                        context,
                        fontSize: 11,
                        color: isPaid
                            ? kw.verified.onContainer
                            : isFailed
                                ? kw.declined.onContainer
                                : kw.standard.onContainer,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: KwSpacing.sm),
            if (!isPaid)
              Wrap(
                spacing: KwSpacing.sm,
                runSpacing: KwSpacing.xs,
                children: [
                  FilledButton.icon(
                    onPressed: _creatingPayment
                        ? null
                        : () => _initiatePayment('google_pay'),
                    icon: const Icon(Icons.account_balance_wallet_rounded),
                    label: Text(hStrings.payWithGooglePayTest),
                  ),
                  OutlinedButton.icon(
                    onPressed: _creatingPayment
                        ? null
                        : () => _initiatePayment('upi_intent'),
                    icon: const Icon(Icons.qr_code_2_rounded),
                    label: Text(hStrings.payWithUpiIntent),
                  ),
                  if (intent != null)
                    TextButton.icon(
                      onPressed: _pollPaymentStatus,
                      icon: const Icon(Icons.refresh_rounded, size: 18),
                      label: const Text('Check status'),
                    ),
                ],
              ),
            if (_showGooglePaySheet && intent?.googlePay != null) ...[
              const SizedBox(height: KwSpacing.sm),
              _buildGooglePaySheet(context, intent!.googlePay!),
            ],
            if (intent?.upiIntentUrl != null &&
                intent!.upiIntentUrl!.isNotEmpty) ...[
              const SizedBox(height: KwSpacing.sm),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(KwSpacing.sm),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHigh,
                  borderRadius: KwShapes.radiusSmall,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'UPI Intent Link',
                      style: theme.textTheme.labelMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    SelectableText(
                      intent.upiIntentUrl!,
                      style: KwTheme.monoStyle(context, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
            if (widget.apiClient.config.isSandboxPayment &&
                intent != null &&
                !isPaid) ...[
              const SizedBox(height: KwSpacing.md),
              Container(
                padding: const EdgeInsets.all(KwSpacing.sm),
                decoration: BoxDecoration(
                  color: kw.needsChecking.container.withValues(alpha: 0.45),
                  borderRadius: KwShapes.radiusMedium,
                  border: Border.all(color: kw.needsChecking.accent),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      hStrings.sandboxTestCardTitle,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: kw.needsChecking.onContainer,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xs),
                    Wrap(
                      spacing: KwSpacing.xs,
                      runSpacing: KwSpacing.xs,
                      children: [
                        FilledButton.icon(
                          onPressed: _completingSandbox
                              ? null
                              : () => _sandboxComplete('success'),
                          icon: const Icon(Icons.check_circle_outline_rounded),
                          label: Text(hStrings.completeTestPaymentSuccess),
                        ),
                        OutlinedButton.icon(
                          onPressed: _completingSandbox
                              ? null
                              : () => _sandboxComplete('failure'),
                          icon: const Icon(Icons.cancel_outlined),
                          label: Text(hStrings.completeTestPaymentFailure),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
            if (_paymentNotice != null) ...[
              const SizedBox(height: KwSpacing.sm),
              Text(
                _paymentNotice!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: isPaid ? kw.verified.accent : cs.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildGooglePaySheet(
    BuildContext context,
    GooglePayConfig gpay,
  ) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Container(
      padding: const EdgeInsets.all(KwSpacing.sm),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest,
        borderRadius: KwShapes.radiusMedium,
        border: Border.all(color: cs.primary),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.credit_card_rounded, color: cs.primary),
              const SizedBox(width: KwSpacing.xs),
              Text(
                'Google Pay (${gpay.environment}) Transaction Sheet',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: KwSpacing.xs),
          Text('Merchant: ${gpay.merchantName} (${gpay.merchantId})'),
          Text('Gateway: ${gpay.gateway} · ${gpay.gatewayMerchantId}'),
          Text(
            'Amount: ${gpay.transactionInfo.currencyCode} ${gpay.transactionInfo.totalPrice} (${gpay.transactionInfo.totalPriceStatus})',
            style: KwTheme.monoStyle(context, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Widget _buildOtpClosureCard(
    BuildContext context,
    HouseholdStrings hStrings,
  ) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;
    final duration = KwMotion.durationFor(context, KwMotion.defaultDuration);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.md),
        child: AnimatedSwitcher(
          duration: duration,
          child: _jobClosed
              ? Container(
                  key: const ValueKey<String>('otp_closed'),
                  width: double.infinity,
                  padding: const EdgeInsets.all(KwSpacing.md),
                  decoration: BoxDecoration(
                    color: kw.verified.container,
                    borderRadius: KwShapes.radiusLarge,
                  ),
                  child: Column(
                    children: [
                      Icon(
                        Icons.verified_rounded,
                        size: 48,
                        color: kw.verified.accent,
                      ),
                      const SizedBox(height: KwSpacing.sm),
                      Text(
                        hStrings.jobClosedTitle,
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: kw.verified.onContainer,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: KwSpacing.xxs),
                      Text(
                        hStrings.jobClosedSubtitle,
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: kw.verified.onContainer,
                        ),
                      ),
                      if (_closureReceiptRef != null) ...[
                        const SizedBox(height: KwSpacing.xs),
                        Text(
                          'Reference: $_closureReceiptRef',
                          style: KwTheme.monoStyle(
                            context,
                            color: kw.verified.onContainer,
                          ),
                        ),
                      ],
                    ],
                  ),
                )
              : Column(
                  key: const ValueKey<String>('otp_entry'),
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      hStrings.otpSectionTitle,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.xs),
                    Text(
                      'Share or enter your 6-digit closure OTP only after you have checked that your appliance works properly.',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: KwSpacing.md),
                    KwOtpInput(
                      enabled: !_submittingOtp,
                      errorText: _otpError,
                      onChanged: (code) {
                        setState(() {
                          _otpCode = code;
                          _otpError = null;
                        });
                      },
                      onCompleted: _confirmOtp,
                    ),
                    const SizedBox(height: KwSpacing.md),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: (_otpCode.length == 6 && !_submittingOtp)
                            ? () => _confirmOtp()
                            : null,
                        icon: const Icon(Icons.lock_open_rounded),
                        label: Text(
                          _submittingOtp
                              ? 'Confirming…'
                              : hStrings.confirmOtpLabel,
                        ),
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class _SummaryAmountRow extends StatelessWidget {
  const _SummaryAmountRow({
    required this.label,
    required this.amountPaise,
    this.bold = false,
    this.toneColor,
  });

  final String label;
  final int amountPaise;
  final bool bold;
  final Color? toneColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: bold
                ? theme.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.w700)
                : theme.textTheme.bodyMedium,
          ),
        ),
        Text(
          formatInrPaise(amountPaise, showZeroDecimals: true),
          style: KwTheme.monoStyle(
            context,
            fontSize: bold ? 16 : 14,
            fontWeight: bold ? FontWeight.w700 : FontWeight.w600,
            color: toneColor ?? theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }
}
