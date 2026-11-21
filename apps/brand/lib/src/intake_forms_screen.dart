import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'brand_strings.dart';

/// Two-tab Material 3 Expressive intake workspace:
/// 1. Brand Warranty Forward (`POST /channels/brand/requests` with `X-Keepwell-Key`)
/// 2. Retailer Installation Handover (`POST /channels/retailer/handovers` with `X-Keepwell-Key`)
class IntakeFormsScreen extends StatefulWidget {
  const IntakeFormsScreen({
    super.key,
    required this.api,
    required this.session,
    required this.brandStrings,
    this.onSubmitted,
  });

  final KwApiClient api;
  final KwUserSession session;
  final BrandStrings brandStrings;
  final VoidCallback? onSubmitted;

  @override
  State<IntakeFormsScreen> createState() => _IntakeFormsScreenState();
}

class _IntakeFormsScreenState extends State<IntakeFormsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  // --- Brand Warranty Forward state ---
  final _brandFormKey = GlobalKey<FormState>();
  final _brandKeyCtrl = TextEditingController(text: 'demo-brand-key');
  final _brandModelCtrl = TextEditingController(text: 'AV-AC-15T-INV');
  final _brandSerialCtrl = TextEditingController(text: 'AV2026HYD88412');
  final _brandCustomerCtrl = TextEditingController(text: 'Raghavendra Rao');
  final _brandPhoneCtrl = TextEditingController(text: '+919848011223');
  final _brandLocalityCtrl = TextEditingController(text: 'Madhapur');
  final _brandPincodeCtrl = TextEditingController(text: '500081');
  final _brandSymptomCtrl = TextEditingController(
    text: 'Split AC indoor unit blowing warm air after 10 minutes; E4 blinking.',
  );
  late String _brandKey;
  String _targetCentreKey = 'c_av';
  String _brandCategory = 'air_conditioner';
  String _claimedWarranty = 'in_warranty';
  bool _submittingBrand = false;
  Map<String, dynamic>? _brandResponse;
  String? _brandError;

  // --- Retailer Installation Handover state ---
  final _retailerFormKey = GlobalKey<FormState>();
  final _retailerKeyCtrl = TextEditingController(text: 'demo-retailer-key');
  final _retailerNameCtrl = TextEditingController(
    text: 'Digital Plaza Electronics, Jubilee Hills',
  );
  final _invoiceRefCtrl = TextEditingController(text: 'INV-DPE-2026-44109');
  final _retailerModelCtrl = TextEditingController(text: 'ZN-WM-75FL');
  final _retailerSerialCtrl = TextEditingController(text: 'ZN2026BLR55209');
  final _deliveryDateCtrl = TextEditingController(text: '2026-11-22');
  final _retailerCustomerCtrl = TextEditingController(text: 'Meenakshi Iyer');
  final _retailerPhoneCtrl = TextEditingController(text: '+919849055667');
  final _retailerAddressCtrl = TextEditingController(
    text: 'Flat 402, Lotus Residency, Road No. 12, Banjara Hills, Hyderabad',
  );
  final _locationPinCtrl = TextEditingController(text: '17.4126, 78.4398');
  final _floorCtrl = TextEditingController(text: '4th Floor');
  final _accessNotesCtrl = TextEditingController(
    text: 'Dedicated 16A socket near utility balcony; service lift available.',
  );
  late String _retailerBrand;
  String _retailerCategory = 'washing_machine';
  bool _liftAvailable = true;
  bool _powerPointReady = true;
  bool _submittingRetailer = false;
  Map<String, dynamic>? _retailerResponse;
  String? _retailerError;

  static const List<String> _categories = [
    'air_conditioner',
    'washing_machine',
    'refrigerator',
    'water_purifier',
    'geyser',
    'microwave',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _brandKey = widget.session.brandId ?? 'aerovane';
    _retailerBrand = widget.session.brandId ?? 'zenith';
  }

  @override
  void didUpdateWidget(covariant IntakeFormsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.session.brandId != widget.session.brandId &&
        widget.session.brandId != null) {
      _brandKey = widget.session.brandId!;
      _retailerBrand = widget.session.brandId!;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _brandKeyCtrl.dispose();
    _brandModelCtrl.dispose();
    _brandSerialCtrl.dispose();
    _brandCustomerCtrl.dispose();
    _brandPhoneCtrl.dispose();
    _brandLocalityCtrl.dispose();
    _brandPincodeCtrl.dispose();
    _brandSymptomCtrl.dispose();
    _retailerKeyCtrl.dispose();
    _retailerNameCtrl.dispose();
    _invoiceRefCtrl.dispose();
    _retailerModelCtrl.dispose();
    _retailerSerialCtrl.dispose();
    _deliveryDateCtrl.dispose();
    _retailerCustomerCtrl.dispose();
    _retailerPhoneCtrl.dispose();
    _retailerAddressCtrl.dispose();
    _locationPinCtrl.dispose();
    _floorCtrl.dispose();
    _accessNotesCtrl.dispose();
    super.dispose();
  }

  void _applyIndependentDeclinePreset() {
    setState(() {
      _brandKey = 'aerovane';
      _targetCentreKey = 'c_cc';
      _claimedWarranty = 'in_warranty';
      _brandCategory = 'air_conditioner';
      _brandModelCtrl.text = 'AV-AC-15T-INV';
      _brandSerialCtrl.text = 'AV2026HYD88412';
      _brandSymptomCtrl.text =
          'Warranty forward to independent centre c_cc to verify authority decline.';
    });
  }

  Future<void> _submitBrandForward() async {
    if (!(_brandFormKey.currentState?.validate() ?? false)) return;
    setState(() {
      _submittingBrand = true;
      _brandError = null;
      _brandResponse = null;
    });
    final payload = <String, dynamic>{
      'brand': _brandKey,
      'centre_key': _targetCentreKey,
      'claimed_warranty': _claimedWarranty,
      'appliance': {
        'brand': _brandKey,
        'category_code': _brandCategory,
        'model_code': _brandModelCtrl.text.trim(),
        'serial_number': _brandSerialCtrl.text.trim(),
      },
      'customer': {
        'display_name': _brandCustomerCtrl.text.trim(),
        'phone': _brandPhoneCtrl.text.trim(),
        'locality': _brandLocalityCtrl.text.trim(),
        'pincode': _brandPincodeCtrl.text.trim(),
      },
      'complaint': _brandSymptomCtrl.text.trim(),
    };
    try {
      final resp = await widget.api.submitBrandRequest(
        payload,
        apiKey: _brandKeyCtrl.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _brandResponse = resp;
        _submittingBrand = false;
      });
      widget.onSubmitted?.call();
    } on KwApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _brandError = '${e.error.code}: ${e.error.message}';
        _submittingBrand = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _brandError = e.toString();
        _submittingBrand = false;
      });
    }
  }

  Future<void> _submitRetailerHandover() async {
    if (!(_retailerFormKey.currentState?.validate() ?? false)) return;
    setState(() {
      _submittingRetailer = true;
      _retailerError = null;
      _retailerResponse = null;
    });
    final payload = <String, dynamic>{
      'retailer': _retailerNameCtrl.text.trim(),
      'invoice_ref': _invoiceRefCtrl.text.trim(),
      'requested_job': 'installation',
      'brand': _retailerBrand,
      'appliance': {
        'brand': _retailerBrand,
        'category_code': _retailerCategory,
        'model_code': _retailerModelCtrl.text.trim(),
        'serial_number': _retailerSerialCtrl.text.trim(),
      },
      'delivery_date': _deliveryDateCtrl.text.trim(),
      'customer': {
        'display_name': _retailerCustomerCtrl.text.trim(),
        'phone': _retailerPhoneCtrl.text.trim(),
        'address_line': _retailerAddressCtrl.text.trim(),
        'location_pin': _locationPinCtrl.text.trim(),
      },
      'access_notes': {
        'floor': _floorCtrl.text.trim(),
        'lift_available': _liftAvailable,
        'power_point_ready': _powerPointReady,
        'notes': _accessNotesCtrl.text.trim(),
      },
    };
    try {
      final resp = await widget.api.submitRetailerHandover(
        payload,
        apiKey: _retailerKeyCtrl.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _retailerResponse = resp;
        _submittingRetailer = false;
      });
      widget.onSubmitted?.call();
    } on KwApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _retailerError = '${e.error.code}: ${e.error.message}';
        _submittingRetailer = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _retailerError = e.toString();
        _submittingRetailer = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bs = widget.brandStrings;
    final windowSize = KwWindowSize.of(context);
    final pad = windowSize.isCompact ? KwSpacing.md : KwSpacing.lg;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(pad, pad, pad, KwSpacing.xs),
          child: Text(
            bs.intakeHeading,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: pad),
          child: TabBar(
            controller: _tabController,
            tabs: [
              Tab(
                key: const ValueKey('tab-brand-forward'),
                icon: const Icon(Icons.verified_user_outlined),
                text: bs.tabBrandForward,
              ),
              Tab(
                key: const ValueKey('tab-retailer-handover'),
                icon: const Icon(Icons.storefront_outlined),
                text: bs.tabRetailerHandover,
              ),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildBrandForwardTab(context, pad),
              _buildRetailerHandoverTab(context, pad),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBrandForwardTab(BuildContext context, double pad) {
    final bs = widget.brandStrings;
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return SingleChildScrollView(
      padding: EdgeInsets.all(pad),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 880),
        child: Form(
          key: _brandFormKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Quick preset banner for live C18 authority check
              Card(
                color: cs.secondaryContainer.withValues(alpha: 0.45),
                child: Padding(
                  padding: const EdgeInsets.all(KwSpacing.md),
                  child: Wrap(
                    spacing: KwSpacing.sm,
                    runSpacing: KwSpacing.sm,
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 520),
                        child: Text(
                          'Endpoint: POST /channels/brand/requests (X-Keepwell-Key). Select independent centre c_cc with In-Warranty to observe the live HTTP 202 declined authority response.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: cs.onSecondaryContainer,
                          ),
                        ),
                      ),
                      OutlinedButton.icon(
                        key: const ValueKey('preset-c-cc-decline'),
                        onPressed: _applyIndependentDeclinePreset,
                        icon: const Icon(Icons.gpp_bad_outlined),
                        label: const Text('Preset: Independent c_cc'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: KwSpacing.md),

              if (_brandResponse != null) ...[
                _IntakeResponseCard(
                  title: bs.responseCardTitle,
                  response: _brandResponse!,
                ),
                const SizedBox(height: KwSpacing.md),
              ],
              if (_brandError != null) ...[
                _InlineErrorBanner(message: _brandError!),
                const SizedBox(height: KwSpacing.md),
              ],

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 260,
                    child: TextFormField(
                      controller: _brandKeyCtrl,
                      decoration: const InputDecoration(
                        labelText: 'X-Keepwell-Key',
                        prefixIcon: Icon(Icons.vpn_key_outlined),
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      value: _brandKey,
                      decoration: const InputDecoration(labelText: 'Brand'),
                      items: [
                        for (final b in KwAuthHelper.demoBrandKeys)
                          DropdownMenuItem(
                            value: b,
                            child: Text(b[0].toUpperCase() + b.substring(1)),
                          ),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _brandKey = v);
                      },
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      value: _claimedWarranty,
                      decoration: const InputDecoration(
                        labelText: 'Warranty Claim',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'in_warranty',
                          child: Text('In Warranty'),
                        ),
                        DropdownMenuItem(
                          value: 'out_of_warranty',
                          child: Text('Out of Warranty (Paid)'),
                        ),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _claimedWarranty = v);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              DropdownButtonFormField<String>(
                key: const ValueKey('brand-target-centre-dropdown'),
                value: _targetCentreKey,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Target Service Centre',
                  helperText:
                      'Select c_cc (independent) to test live authority decline.',
                ),
                items: [
                  for (final c in KwAuthHelper.demoCentres)
                    DropdownMenuItem(
                      value: c.key,
                      child: Text(
                        '${c.key} · ${c.name} — ${c.brandsSummary}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (v) {
                  if (v != null) setState(() => _targetCentreKey = v);
                },
              ),
              const SizedBox(height: KwSpacing.md),

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 240,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      value: _brandCategory,
                      decoration: const InputDecoration(
                        labelText: 'Appliance Category',
                      ),
                      items: [
                        for (final cat in _categories)
                          DropdownMenuItem(
                            value: cat,
                            child: Text(cat.replaceAll('_', ' ')),
                          ),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _brandCategory = v);
                      },
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _brandModelCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Model Code',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _brandSerialCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Appliance Serial',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _brandCustomerCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Customer Name',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: TextFormField(
                      controller: _brandPhoneCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Customer Phone',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 180,
                    child: TextFormField(
                      controller: _brandLocalityCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Locality',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 140,
                    child: TextFormField(
                      controller: _brandPincodeCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Pincode',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              TextFormField(
                controller: _brandSymptomCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Reported Symptom / Fault Description',
                ),
                validator: _requiredValidator,
              ),
              const SizedBox(height: KwSpacing.lg),

              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  key: const ValueKey('submit-brand-forward-btn'),
                  onPressed: _submittingBrand ? null : _submitBrandForward,
                  icon: _submittingBrand
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send_rounded),
                  label: Text(bs.submitBrandButton),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRetailerHandoverTab(BuildContext context, double pad) {
    final bs = widget.brandStrings;

    return SingleChildScrollView(
      padding: EdgeInsets.all(pad),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 880),
        child: Form(
          key: _retailerFormKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_retailerResponse != null) ...[
                _IntakeResponseCard(
                  title: bs.responseCardTitle,
                  response: _retailerResponse!,
                ),
                const SizedBox(height: KwSpacing.md),
              ],
              if (_retailerError != null) ...[
                _InlineErrorBanner(message: _retailerError!),
                const SizedBox(height: KwSpacing.md),
              ],

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _retailerKeyCtrl,
                      decoration: const InputDecoration(
                        labelText: 'X-Keepwell-Key',
                        prefixIcon: Icon(Icons.vpn_key_outlined),
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 300,
                    child: TextFormField(
                      controller: _retailerNameCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Retailer Store Name',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _invoiceRefCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Invoice Reference',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 180,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      value: _retailerBrand,
                      decoration: const InputDecoration(labelText: 'Brand'),
                      items: [
                        for (final b in KwAuthHelper.demoBrandKeys)
                          DropdownMenuItem(
                            value: b,
                            child: Text(b[0].toUpperCase() + b.substring(1)),
                          ),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _retailerBrand = v);
                      },
                    ),
                  ),
                  SizedBox(
                    width: 200,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      value: _retailerCategory,
                      decoration: const InputDecoration(
                        labelText: 'Appliance Category',
                      ),
                      items: [
                        for (final cat in _categories)
                          DropdownMenuItem(
                            value: cat,
                            child: Text(cat.replaceAll('_', ' ')),
                          ),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _retailerCategory = v);
                      },
                    ),
                  ),
                  SizedBox(
                    width: 180,
                    child: TextFormField(
                      controller: _retailerModelCtrl,
                      decoration: const InputDecoration(labelText: 'Model Code'),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 200,
                    child: TextFormField(
                      controller: _retailerSerialCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Serial Number',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 200,
                    child: TextFormField(
                      controller: _deliveryDateCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Delivery Date (YYYY-MM-DD)',
                        prefixIcon: Icon(Icons.calendar_today_outlined),
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _retailerCustomerCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Customer Name',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: TextFormField(
                      controller: _retailerPhoneCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Customer Phone',
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.md),

              TextFormField(
                controller: _retailerAddressCtrl,
                decoration: const InputDecoration(
                  labelText: 'Installation Address',
                  prefixIcon: Icon(Icons.home_outlined),
                ),
                validator: _requiredValidator,
              ),
              const SizedBox(height: KwSpacing.md),

              Wrap(
                spacing: KwSpacing.md,
                runSpacing: KwSpacing.md,
                children: [
                  SizedBox(
                    width: 260,
                    child: TextFormField(
                      controller: _locationPinCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Location Pin (lat, lon)',
                        prefixIcon: Icon(Icons.location_on_outlined),
                      ),
                      validator: _requiredValidator,
                    ),
                  ),
                  SizedBox(
                    width: 200,
                    child: TextFormField(
                      controller: _floorCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Floor',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.sm),

              Wrap(
                spacing: KwSpacing.lg,
                children: [
                  SizedBox(
                    width: 240,
                    child: SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Lift available'),
                      value: _liftAvailable,
                      onChanged: (v) => setState(() => _liftAvailable = v),
                    ),
                  ),
                  SizedBox(
                    width: 260,
                    child: SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Power point ready'),
                      value: _powerPointReady,
                      onChanged: (v) => setState(() => _powerPointReady = v),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.sm),

              TextFormField(
                controller: _accessNotesCtrl,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Access Notes (floor, lift, power point, gate)',
                ),
              ),
              const SizedBox(height: KwSpacing.lg),

              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  key: const ValueKey('submit-retailer-handover-btn'),
                  onPressed:
                      _submittingRetailer ? null : _submitRetailerHandover,
                  icon: _submittingRetailer
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.local_shipping_outlined),
                  label: Text(bs.submitRetailerButton),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String? _requiredValidator(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Required';
    }
    return null;
  }
}

class _IntakeResponseCard extends StatelessWidget {
  const _IntakeResponseCard({
    required this.title,
    required this.response,
  });

  final String title;
  final Map<String, dynamic> response;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final kw = theme.kwColors;
    final ticketId = (response['ticket_id'] ?? '').toString();
    final status = (response['status'] ?? 'received').toString();
    final declinedReason = response['declined_reason']?.toString();
    final isDeclined = status.toLowerCase() == 'declined' ||
        (declinedReason != null && declinedReason.trim().isNotEmpty);
    final role = isDeclined ? kw.declined : kw.verified;

    return Semantics(
      liveRegion: true,
      container: true,
      label:
          '$title. Ticket $ticketId, status $status.${declinedReason != null ? ' Reason: $declinedReason' : ''}',
      child: Card(
        color: role.container,
        shape: KwShapes.rounded(
          KwShapes.medium,
          side: BorderSide(color: role.accent, width: 1.5),
        ),
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    isDeclined
                        ? Icons.gpp_bad_rounded
                        : Icons.check_circle_rounded,
                    color: role.onContainer,
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  Expanded(
                    child: Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: role.onContainer,
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
                      color: role.accent,
                      borderRadius: KwShapes.radiusFull,
                    ),
                    child: Text(
                      status.toUpperCase(),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.surface,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: KwSpacing.sm),
              Wrap(
                spacing: KwSpacing.lg,
                runSpacing: KwSpacing.xs,
                children: [
                  _KeyVal(
                    label: 'ticket_id',
                    value: ticketId,
                    color: role.onContainer,
                    mono: true,
                  ),
                  _KeyVal(
                    label: 'status',
                    value: status,
                    color: role.onContainer,
                    mono: true,
                  ),
                ],
              ),
              if (declinedReason != null && declinedReason.trim().isNotEmpty) ...[
                const SizedBox(height: KwSpacing.sm),
                Text(
                  'declined_reason',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: role.onContainer.withValues(alpha: 0.8),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  declinedReason,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: role.onContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _KeyVal extends StatelessWidget {
  const _KeyVal({
    required this.label,
    required this.value,
    required this.color,
    this.mono = false,
  });

  final String label;
  final String value;
  final Color color;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: color.withValues(alpha: 0.8),
          ),
        ),
        Text(
          value,
          style: mono
              ? KwTheme.monoStyle(context, fontSize: 13, color: color)
              : theme.textTheme.bodyMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
        ),
      ],
    );
  }
}

class _InlineErrorBanner extends StatelessWidget {
  const _InlineErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final kw = Theme.of(context).kwColors;
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(KwSpacing.sm),
        decoration: BoxDecoration(
          color: kw.declined.container,
          borderRadius: KwShapes.radiusSmall,
          border: Border.all(color: kw.declined.accent),
        ),
        child: Row(
          children: [
            Icon(Icons.error_outline_rounded, color: kw.declined.onContainer),
            const SizedBox(width: KwSpacing.xs),
            Expanded(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: kw.declined.onContainer,
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
