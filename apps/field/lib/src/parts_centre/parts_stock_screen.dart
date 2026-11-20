import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import '../field_l10n.dart';

/// Mutable stock entry displayed in [PartsStockScreen].
class PartsStockItem {
  PartsStockItem({
    required this.partNo,
    required this.name,
    required this.quantity,
  });

  final String partNo;
  final String name;
  int quantity;

  Map<String, dynamic> toJson() => {
        'part_no': partNo,
        'name': name,
        'quantity': quantity,
      };
}

/// Fast quantity stepper screen for Parts Centre stock updates via
/// `api.updatePartsStock(...)`.
class PartsStockScreen extends StatefulWidget {
  const PartsStockScreen({
    super.key,
    required this.api,
    this.initialItems,
  });

  final KwApiClient api;
  final List<PartsStockItem>? initialItems;

  @override
  State<PartsStockScreen> createState() => _PartsStockScreenState();
}

class _PartsStockScreenState extends State<PartsStockScreen> {
  late final List<PartsStockItem> _items;
  final TextEditingController _skuController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  bool _saving = false;
  String? _statusMessage;

  @override
  void initState() {
    super.initState();
    _items = widget.initialItems != null
        ? List<PartsStockItem>.from(widget.initialItems!)
        : <PartsStockItem>[
            PartsStockItem(
              partNo: 'AV-CAP-45UF',
              name: 'Dual Run Capacitor 45µF',
              quantity: 8,
            ),
            PartsStockItem(
              partNo: 'FL-THERM-201',
              name: 'Frostline Defrost Thermostat',
              quantity: 5,
            ),
            PartsStockItem(
              partNo: 'WC-PUMP-DRN',
              name: 'Wavecrest Drain Pump Motor',
              quantity: 3,
            ),
            PartsStockItem(
              partNo: 'HW-ELEM-2KW',
              name: 'Heatwell 2kW Heating Element',
              quantity: 6,
            ),
          ];
  }

  @override
  void dispose() {
    _skuController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _stepQuantity(int index, int delta) {
    final next = _items[index].quantity + delta;
    if (next < 0) return;
    setState(() {
      _items[index].quantity = next;
      _statusMessage = null;
    });
  }

  void _addItem() {
    final sku = _skuController.text.trim();
    final name = _nameController.text.trim();
    if (sku.isEmpty) return;
    setState(() {
      _items.insert(
        0,
        PartsStockItem(
          partNo: sku,
          name: name.isEmpty ? sku : name,
          quantity: 1,
        ),
      );
      _skuController.clear();
      _nameController.clear();
      _statusMessage = null;
    });
  }

  Future<void> _saveStock() async {
    setState(() {
      _saving = true;
      _statusMessage = null;
    });
    try {
      await widget.api.updatePartsStock({
        'items': _items.map((e) => e.toJson()).toList(),
      });
      if (!mounted) return;
      setState(() {
        _saving = false;
        _statusMessage = 'Stock quantities updated (${_items.length} SKUs).';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _statusMessage = 'Update failed: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = FieldStrings.of(context);

    return Column(
      children: [
        if (_statusMessage != null)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.md,
              vertical: KwSpacing.sm,
            ),
            color: kw.verified.container,
            child: Text(
              _statusMessage!,
              style: theme.textTheme.labelLarge?.copyWith(
                color: kw.verified.onContainer,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(KwSpacing.md),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(KwSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Add SKU to stock list',
                        style: theme.textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: KwSpacing.xs),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _skuController,
                              decoration: const InputDecoration(
                                labelText: 'Part SKU',
                                hintText: 'e.g. PL-MEM-75G',
                              ),
                            ),
                          ),
                          const SizedBox(width: KwSpacing.xs),
                          Expanded(
                            child: TextField(
                              controller: _nameController,
                              decoration: const InputDecoration(
                                labelText: 'Part name',
                              ),
                            ),
                          ),
                          const SizedBox(width: KwSpacing.xs),
                          IconButton.filledTonal(
                            tooltip: 'Add SKU',
                            onPressed: _addItem,
                            icon: const Icon(Icons.add_rounded),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: KwSpacing.md),
              for (var i = 0; i < _items.length; i++) ...[
                Card(
                  key: Key('kw_stock_row_${_items[i].partNo}'),
                  child: Padding(
                    padding: const EdgeInsets.all(KwSpacing.md),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _items[i].name,
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _items[i].partNo,
                                style: KwTheme.monoStyle(
                                  context,
                                  fontSize: theme.textTheme.labelSmall?.fontSize,
                                  color: cs.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton.outlined(
                          key: Key('kw_stock_dec_${_items[i].partNo}'),
                          tooltip: 'Decrease ${_items[i].partNo}',
                          onPressed: _items[i].quantity > 0
                              ? () => _stepQuantity(i, -1)
                              : null,
                          icon: const Icon(Icons.remove_rounded),
                        ),
                        SizedBox(
                          width: 44,
                          child: Text(
                            '${_items[i].quantity}',
                            key: Key('kw_stock_qty_${_items[i].partNo}'),
                            textAlign: TextAlign.center,
                            style: KwTheme.monoStyle(
                              context,
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        IconButton.outlined(
                          key: Key('kw_stock_inc_${_items[i].partNo}'),
                          tooltip: 'Increase ${_items[i].partNo}',
                          onPressed: () => _stepQuantity(i, 1),
                          icon: const Icon(Icons.add_rounded),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: KwSpacing.xs),
              ],
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(KwSpacing.md),
            child: FilledButton.icon(
              key: const Key('kw_save_stock_button'),
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 52),
              ),
              onPressed: _saving ? null : _saveStock,
              icon: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_rounded),
              label: Text(strings.saveStockAction),
            ),
          ),
        ),
      ],
    );
  }
}
