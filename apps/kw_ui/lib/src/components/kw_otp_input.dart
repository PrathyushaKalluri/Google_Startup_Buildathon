import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// 6-digit accessible OTP input with keyboard navigation, paste support,
/// tabular monospace digits, and ≥ 48 dp touch targets (Shared Contract §0).
class KwOtpInput extends StatefulWidget {
  const KwOtpInput({
    super.key,
    this.length = 6,
    this.initialValue = '',
    this.enabled = true,
    this.errorText,
    this.onChanged,
    this.onCompleted,
  }) : assert(length >= 4 && length <= 8);

  final int length;
  final String initialValue;
  final bool enabled;
  final String? errorText;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onCompleted;

  @override
  State<KwOtpInput> createState() => _KwOtpInputState();
}

class _KwOtpInputState extends State<KwOtpInput> {
  late final List<TextEditingController> _controllers;
  late final List<FocusNode> _focusNodes;

  @override
  void initState() {
    super.initState();
    _controllers = List<TextEditingController>.generate(widget.length, (i) {
      final char = i < widget.initialValue.length ? widget.initialValue[i] : '';
      return TextEditingController(text: char);
    });
    _focusNodes = List<FocusNode>.generate(
      widget.length,
      (i) => FocusNode(debugLabel: 'kw_otp_$i'),
    );
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    for (final f in _focusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  String get _currentCode => _controllers.map((c) => c.text).join();

  void _handleChanged(int index, String raw) {
    final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');

    if (digits.length > 1) {
      // Paste or autofill of multiple digits.
      for (var i = 0; i < widget.length; i++) {
        final target = i < digits.length ? digits[i] : '';
        _controllers[i].text = target;
      }
      final nextIndex =
          digits.length >= widget.length ? widget.length - 1 : digits.length;
      _focusNodes[nextIndex].requestFocus();
    } else {
      _controllers[index].text = digits;
      _controllers[index].selection =
          TextSelection.collapsed(offset: digits.length);
      if (digits.isNotEmpty && index + 1 < widget.length) {
        _focusNodes[index + 1].requestFocus();
      } else if (digits.isEmpty && index > 0) {
        _focusNodes[index - 1].requestFocus();
      }
    }

    final code = _currentCode;
    widget.onChanged?.call(code);
    if (code.length == widget.length) {
      widget.onCompleted?.call(code);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final strings = KwStrings.of(context);
    final hasError = widget.errorText != null && widget.errorText!.isNotEmpty;

    return Semantics(
      container: true,
      label: strings.otpHeading,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.otpHeading,
            style: theme.textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: KwSpacing.xs),
          Wrap(
            spacing: KwSpacing.xs,
            runSpacing: KwSpacing.xs,
            children: [
              for (var i = 0; i < widget.length; i++)
                SizedBox(
                  width: KwSpacing.minTouchTarget,
                  height: 56,
                  child: Semantics(
                    label: '${strings.otpDigitLabel} ${i + 1} of ${widget.length}',
                    textField: true,
                    child: TextField(
                      controller: _controllers[i],
                      focusNode: _focusNodes[i],
                      enabled: widget.enabled,
                      keyboardType: TextInputType.number,
                      textAlign: TextAlign.center,
                      maxLength: widget.length,
                      autofillHints:
                          i == 0 ? const [AutofillHints.oneTimeCode] : null,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                      ],
                      style: KwTheme.monoStyle(
                        context,
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: cs.onSurface,
                      ),
                      decoration: InputDecoration(
                        counterText: '',
                        contentPadding: EdgeInsets.zero,
                        enabledBorder: OutlineInputBorder(
                          borderRadius: KwShapes.radiusSmall,
                          borderSide: BorderSide(
                            color: hasError ? kw.safety.accent : cs.outline,
                            width: hasError ? 2.0 : 1.0,
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: KwShapes.radiusSmall,
                          borderSide: BorderSide(
                            color: hasError ? kw.safety.accent : kw.focusRing,
                            width: 3.0,
                          ),
                        ),
                      ),
                      onChanged: (v) => _handleChanged(i, v),
                    ),
                  ),
                ),
            ],
          ),
          if (hasError) ...[
            const SizedBox(height: KwSpacing.xs),
            Text(
              widget.errorText!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: kw.safety.accent,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
