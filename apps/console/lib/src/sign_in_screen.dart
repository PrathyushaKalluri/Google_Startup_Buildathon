import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Material 3 Expressive Sign-In screen for Keepwell Centre Console.
///
/// Supports `console.<key>@keepwell.demo` and `platform@keepwell.demo` via
/// [KwAuthHelper], plus one-click demo access to Frost & Wave (`c_fw`).
class SignInScreen extends StatefulWidget {
  const SignInScreen({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final TextEditingController _emailController =
      TextEditingController(text: 'console.c_fw@keepwell.demo');
  final TextEditingController _passwordController =
      TextEditingController(text: 'keepwell-demo-password');
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit([String? overrideEmail]) async {
    final email = (overrideEmail ?? _emailController.text).trim();
    if (email.isEmpty) {
      setState(() => _error = 'Enter a Keepwell console account email.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.controller.signInWithEmail(
        email,
        password: _passwordController.text,
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final size = KwWindowSize.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Keepwell Centre Console'),
        actions: [
          _LanguageMenu(controller: widget.controller),
          _ThemeMenu(controller: widget.controller),
          const SizedBox(width: KwSpacing.xs),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(KwSpacing.lg),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: size.isWide ? 960 : 520,
              ),
              child: size.isWide
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: _buildHeroCard(context, cs, theme)),
                        const SizedBox(width: KwSpacing.lg),
                        Expanded(child: _buildFormCard(context, cs, theme)),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _buildHeroCard(context, cs, theme),
                        const SizedBox(height: KwSpacing.md),
                        _buildFormCard(context, cs, theme),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeroCard(
    BuildContext context,
    ColorScheme cs,
    ThemeData theme,
  ) {
    return Card(
      color: cs.primaryContainer.withValues(alpha: 0.35),
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: cs.primary,
                    borderRadius: KwShapes.radiusMedium,
                  ),
                  child: Icon(
                    Icons.support_agent_rounded,
                    color: cs.onPrimary,
                  ),
                ),
                const SizedBox(width: KwSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Keepwell Operations',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Autonomous intake, triage, and live field coordination',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: KwSpacing.lg),
            Text(
              'Quick Demo Sign-In',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Text(
              'Jump straight into Frost & Wave Service Point (Kukatpally) for the C03 Live Stage demo, or open the cross-centre platform view.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: cs.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: KwSpacing.md),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                key: const Key('quick_sign_in_c_fw'),
                onPressed: _submitting
                    ? null
                    : () => _submit('console.c_fw@keepwell.demo'),
                icon: const Icon(Icons.flash_on_rounded),
                label: const Text('Sign in: Frost & Wave (c_fw)'),
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                key: const Key('quick_sign_in_platform'),
                onPressed: _submitting
                    ? null
                    : () => _submit('platform@keepwell.demo'),
                icon: const Icon(Icons.public_rounded),
                label: const Text('Sign in: Platform Admin (All 9 Centres)'),
              ),
            ),
            const SizedBox(height: KwSpacing.md),
            Text(
              'All 9 Hyderabad Demo Centres',
              style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              children: [
                for (final centre in KwAuthHelper.demoCentres)
                  ActionChip(
                    label: Text('${centre.key} · ${centre.locality}'),
                    onPressed: _submitting
                        ? null
                        : () {
                            _emailController.text =
                                'console.${centre.key}@keepwell.demo';
                            _submit('console.${centre.key}@keepwell.demo');
                          },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFormCard(
    BuildContext context,
    ColorScheme cs,
    ThemeData theme,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Centre Account Sign-In',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: KwSpacing.xs),
            Text(
              'Use console.<centre_key>@keepwell.demo or platform@keepwell.demo',
              style: theme.textTheme.bodySmall?.copyWith(
                color: cs.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: KwSpacing.md),
            TextField(
              key: const Key('sign_in_email_field'),
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Account Email',
                prefixIcon: Icon(Icons.alternate_email_rounded),
              ),
              onSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: KwSpacing.sm),
            TextField(
              key: const Key('sign_in_password_field'),
              controller: _passwordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Password',
                prefixIcon: Icon(Icons.lock_outline_rounded),
              ),
              onSubmitted: (_) => _submit(),
            ),
            if (_error != null) ...[
              const SizedBox(height: KwSpacing.sm),
              Text(
                _error!,
                style: theme.textTheme.bodySmall?.copyWith(color: cs.error),
              ),
            ],
            const SizedBox(height: KwSpacing.md),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                key: const Key('sign_in_submit_button'),
                onPressed: _submitting ? null : () => _submit(),
                child: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Sign In'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LanguageMenu extends StatelessWidget {
  const _LanguageMenu({required this.controller});

  final ConsoleController controller;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      tooltip: 'Language',
      icon: const Icon(Icons.translate_rounded),
      onSelected: controller.setLanguage,
      itemBuilder: (context) => const [
        PopupMenuItem(value: 'en', child: Text('English (en)')),
        PopupMenuItem(value: 'hi', child: Text('हिन्दी (hi)')),
        PopupMenuItem(value: 'te', child: Text('తెలుగు (te)')),
      ],
    );
  }
}

class _ThemeMenu extends StatelessWidget {
  const _ThemeMenu({required this.controller});

  final ConsoleController controller;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<KwThemePreset>(
      tooltip: 'Theme',
      icon: const Icon(Icons.contrast_rounded),
      onSelected: controller.setThemePreset,
      itemBuilder: (context) => const [
        PopupMenuItem(value: KwThemePreset.light, child: Text('Light')),
        PopupMenuItem(value: KwThemePreset.dark, child: Text('Dark')),
        PopupMenuItem(
          value: KwThemePreset.highContrastLight,
          child: Text('High Contrast Light'),
        ),
        PopupMenuItem(
          value: KwThemePreset.highContrastDark,
          child: Text('High Contrast Dark'),
        ),
        PopupMenuItem(
          value: KwThemePreset.projector,
          child: Text('Projector Mode'),
        ),
      ],
    );
  }
}
