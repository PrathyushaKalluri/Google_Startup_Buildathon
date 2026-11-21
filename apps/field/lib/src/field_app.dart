import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'field_l10n.dart';
import 'parts_centre/parts_requests_screen.dart';
import 'parts_centre/parts_stock_screen.dart';
import 'technician/offline_outbox.dart';
import 'technician/tech_jobs_screen.dart';

/// Root Keepwell Field application supporting:
/// - Light, Dark, and High-Contrast themes
/// - Runtime `en` / `hi` / `te` language switching
/// - Role-based sign-in routing (`tech1.<key>@keepwell.demo` -> Technician Shell;
///   `parts.demo@keepwell.demo` -> Parts Centre Shell)
class KeepwellFieldApp extends StatefulWidget {
  const KeepwellFieldApp({
    super.key,
    required this.api,
    required this.authHelper,
    this.initialSession,
    this.initialLanguageCode = 'en',
    this.initialThemePreset = KwThemePreset.light,
  });

  final KwApiClient api;
  final KwAuthHelper authHelper;
  final KwUserSession? initialSession;
  final String initialLanguageCode;
  final KwThemePreset initialThemePreset;

  @override
  State<KeepwellFieldApp> createState() => _KeepwellFieldAppState();
}

class _KeepwellFieldAppState extends State<KeepwellFieldApp> {
  late String _languageCode;
  late KwThemePreset _themePreset;
  KwUserSession? _session;
  late final OfflineOutboxController _outbox;

  @override
  void initState() {
    super.initState();
    _languageCode = widget.initialLanguageCode;
    _themePreset = widget.initialThemePreset;
    _session = widget.initialSession;
    _outbox = OfflineOutboxController(api: widget.api);
  }

  @override
  void dispose() {
    _outbox.dispose();
    super.dispose();
  }

  void _cycleTheme() {
    setState(() {
      _themePreset = switch (_themePreset) {
        KwThemePreset.light => KwThemePreset.dark,
        KwThemePreset.dark => KwThemePreset.highContrastLight,
        KwThemePreset.highContrastLight => KwThemePreset.highContrastDark,
        KwThemePreset.highContrastDark => KwThemePreset.light,
        KwThemePreset.projector => KwThemePreset.light,
      };
    });
  }

  String _themeLabel(KwThemePreset preset) {
    return switch (preset) {
      KwThemePreset.light => 'Light',
      KwThemePreset.dark => 'Dark',
      KwThemePreset.highContrastLight => 'HC Light',
      KwThemePreset.highContrastDark => 'HC Dark',
      KwThemePreset.projector => 'Projector',
    };
  }

  Future<void> _signInWithEmail(String rawEmail) async {
    final email = rawEmail.trim().toLowerCase();
    if (email.isEmpty) return;

    var session = await widget.authHelper.signInDemoPersona(email);
    // Ensure role routing for any tech1.<key>@keepwell.demo or parts.* email.
    if (email.startsWith('parts.')) {
      session = session.copyWith(
        role: KwRole.partsCentre,
        partsCentreId: session.partsCentreId ?? 'parts_centre_demo',
      );
    } else if (email.startsWith('tech')) {
      final parts = email.split('@').first.split('.');
      final centreKey = parts.length > 1 ? parts[1] : (session.centreKey ?? 'c_fw');
      session = session.copyWith(
        role: KwRole.technician,
        centreKey: centreKey,
        technicianId: session.technicianId ?? '${parts.first}_$centreKey',
      );
    }

    if (!mounted) return;
    setState(() {
      _session = session;
    });
  }

  void _signOut() {
    setState(() {
      _session = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final locale = Locale(_languageCode);
    return KwLocaleScope(
      languageCode: _languageCode,
      child: MaterialApp(
        title: 'Keepwell Field',
        debugShowCheckedModeBanner: false,
        locale: locale,
        supportedLocales: const [
          Locale('en'),
          Locale('hi'),
          Locale('te'),
        ],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        theme: KwTheme.fromPreset(_themePreset, locale: locale),
        home: _session == null
            ? _FieldSignInScreen(
                onSignIn: _signInWithEmail,
                languageCode: _languageCode,
                onLanguageChanged: (code) =>
                    setState(() => _languageCode = code),
                themeLabel: _themeLabel(_themePreset),
                onCycleTheme: _cycleTheme,
              )
            : _session!.role == KwRole.partsCentre
                ? _PartsCentreShell(
                    api: widget.api,
                    session: _session!,
                    languageCode: _languageCode,
                    onLanguageChanged: (code) =>
                        setState(() => _languageCode = code),
                    themeLabel: _themeLabel(_themePreset),
                    onCycleTheme: _cycleTheme,
                    onSignOut: _signOut,
                  )
                : _TechnicianShell(
                    api: widget.api,
                    session: _session!,
                    outbox: _outbox,
                    languageCode: _languageCode,
                    onLanguageChanged: (code) =>
                        setState(() => _languageCode = code),
                    themeLabel: _themeLabel(_themePreset),
                    onCycleTheme: _cycleTheme,
                    onSignOut: _signOut,
                  ),
      ),
    );
  }
}

class _ChromeActions extends StatelessWidget {
  const _ChromeActions({
    required this.languageCode,
    required this.onLanguageChanged,
    required this.themeLabel,
    required this.onCycleTheme,
    this.onSignOut,
  });

  final String languageCode;
  final ValueChanged<String> onLanguageChanged;
  final String themeLabel;
  final VoidCallback onCycleTheme;
  final VoidCallback? onSignOut;

  @override
  Widget build(BuildContext context) {
    final strings = FieldStrings.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        PopupMenuButton<String>(
          key: const Key('kw_language_menu'),
          tooltip: 'Language',
          initialValue: languageCode,
          onSelected: onLanguageChanged,
          icon: const Icon(Icons.translate_rounded),
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'en', child: Text('English (EN)')),
            PopupMenuItem(value: 'hi', child: Text('हिन्दी (HI)')),
            PopupMenuItem(value: 'te', child: Text('తెలుగు (TE)')),
          ],
        ),
        IconButton(
          key: const Key('kw_theme_button'),
          tooltip: 'Theme: $themeLabel',
          onPressed: onCycleTheme,
          icon: const Icon(Icons.contrast_rounded),
        ),
        if (onSignOut != null)
          IconButton(
            key: const Key('kw_signout_button'),
            tooltip: strings.signOutTooltip,
            onPressed: onSignOut,
            icon: const Icon(Icons.logout_rounded),
          ),
      ],
    );
  }
}

class _FieldSignInScreen extends StatefulWidget {
  const _FieldSignInScreen({
    required this.onSignIn,
    required this.languageCode,
    required this.onLanguageChanged,
    required this.themeLabel,
    required this.onCycleTheme,
  });

  final Future<void> Function(String email) onSignIn;
  final String languageCode;
  final ValueChanged<String> onLanguageChanged;
  final String themeLabel;
  final VoidCallback onCycleTheme;

  @override
  State<_FieldSignInScreen> createState() => _FieldSignInScreenState();
}

class _FieldSignInScreenState extends State<_FieldSignInScreen> {
  final TextEditingController _emailController = TextEditingController(
    text: 'tech1.c_fw@keepwell.demo',
  );
  bool _signingIn = false;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _submit([String? overrideEmail]) async {
    final target = (overrideEmail ?? _emailController.text).trim();
    if (target.isEmpty) return;
    setState(() => _signingIn = true);
    await widget.onSignIn(target);
    if (mounted) {
      setState(() => _signingIn = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = FieldStrings.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(strings.appTitle),
        actions: [
          _ChromeActions(
            languageCode: widget.languageCode,
            onLanguageChanged: widget.onLanguageChanged,
            themeLabel: widget.themeLabel,
            onCycleTheme: widget.onCycleTheme,
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(KwSpacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(
                  Icons.engineering_rounded,
                  size: 48,
                  color: cs.primary,
                ),
                const SizedBox(height: KwSpacing.md),
                Text(
                  strings.appTitle,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.xs),
                Text(
                  strings.signInSubtitle,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: cs.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: KwSpacing.lg),
                TextField(
                  key: const Key('kw_signin_email'),
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: strings.emailLabel,
                    hintText: 'tech1.c_fw@keepwell.demo or parts.demo@keepwell.demo',
                    prefixIcon: const Icon(Icons.alternate_email_rounded),
                  ),
                  onSubmitted: (_) => _submit(),
                ),
                const SizedBox(height: KwSpacing.md),
                FilledButton(
                  key: const Key('kw_signin_submit'),
                  onPressed: _signingIn ? null : () => _submit(),
                  child: Text(strings.signInButton),
                ),
                const SizedBox(height: KwSpacing.lg),
                Text(
                  'Quick role personas',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: cs.onSurfaceVariant,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.xs),
                Wrap(
                  spacing: KwSpacing.xs,
                  runSpacing: KwSpacing.xs,
                  children: [
                    ActionChip(
                      key: const Key('kw_quick_tech_fw'),
                      avatar: const Icon(Icons.build_rounded, size: 18),
                      label: const Text('tech1.c_fw@keepwell.demo'),
                      onPressed: _signingIn
                          ? null
                          : () => _submit('tech1.c_fw@keepwell.demo'),
                    ),
                    ActionChip(
                      key: const Key('kw_quick_tech_av'),
                      avatar: const Icon(Icons.build_rounded, size: 18),
                      label: const Text('tech1.c_av@keepwell.demo'),
                      onPressed: _signingIn
                          ? null
                          : () => _submit('tech1.c_av@keepwell.demo'),
                    ),
                    ActionChip(
                      key: const Key('kw_quick_parts'),
                      avatar: const Icon(Icons.warehouse_rounded, size: 18),
                      label: const Text('parts.demo@keepwell.demo'),
                      onPressed: _signingIn
                          ? null
                          : () => _submit('parts.demo@keepwell.demo'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TechnicianShell extends StatelessWidget {
  const _TechnicianShell({
    required this.api,
    required this.session,
    required this.outbox,
    required this.languageCode,
    required this.onLanguageChanged,
    required this.themeLabel,
    required this.onCycleTheme,
    required this.onSignOut,
  });

  final KwApiClient api;
  final KwUserSession session;
  final OfflineOutboxController outbox;
  final String languageCode;
  final ValueChanged<String> onLanguageChanged;
  final String themeLabel;
  final VoidCallback onCycleTheme;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final strings = FieldStrings.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(strings.todaysJobsTitle),
            Text(
              session.displayName ?? session.email,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
        actions: [
          _ChromeActions(
            languageCode: languageCode,
            onLanguageChanged: onLanguageChanged,
            themeLabel: themeLabel,
            onCycleTheme: onCycleTheme,
            onSignOut: onSignOut,
          ),
        ],
      ),
      body: TechJobsScreen(
        api: api,
        session: session,
        outbox: outbox,
      ),
    );
  }
}

class _PartsCentreShell extends StatefulWidget {
  const _PartsCentreShell({
    required this.api,
    required this.session,
    required this.languageCode,
    required this.onLanguageChanged,
    required this.themeLabel,
    required this.onCycleTheme,
    required this.onSignOut,
  });

  final KwApiClient api;
  final KwUserSession session;
  final String languageCode;
  final ValueChanged<String> onLanguageChanged;
  final String themeLabel;
  final VoidCallback onCycleTheme;
  final VoidCallback onSignOut;

  @override
  State<_PartsCentreShell> createState() => _PartsCentreShellState();
}

class _PartsCentreShellState extends State<_PartsCentreShell> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final strings = FieldStrings.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(strings.rolePartsCentre),
            Text(
              widget.session.displayName ?? widget.session.email,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
        actions: [
          _ChromeActions(
            languageCode: widget.languageCode,
            onLanguageChanged: widget.onLanguageChanged,
            themeLabel: widget.themeLabel,
            onCycleTheme: widget.onCycleTheme,
            onSignOut: widget.onSignOut,
          ),
        ],
      ),
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          PartsRequestsScreen(api: widget.api),
          PartsStockScreen(api: widget.api),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (i) => setState(() => _selectedIndex = i),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.assignment_outlined),
            selectedIcon: const Icon(Icons.assignment_rounded),
            label: strings.partsRequestsTab,
          ),
          NavigationDestination(
            icon: const Icon(Icons.inventory_2_outlined),
            selectedIcon: const Icon(Icons.inventory_2_rounded),
            label: strings.partsStockTab,
          ),
        ],
      ),
    );
  }
}
