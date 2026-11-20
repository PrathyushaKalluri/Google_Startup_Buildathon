import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'analytics_screen.dart';
import 'brand_strings.dart';
import 'intake_forms_screen.dart';
import 'requests_screen.dart';

/// Root Material 3 Expressive application for the Keepwell Brand & Retailer Portal.
class BrandPortalApp extends StatefulWidget {
  const BrandPortalApp({
    super.key,
    required this.config,
    this.apiClient,
    this.authHelper,
    this.initialSession,
    this.initialLanguageCode = 'en',
    this.initialThemePreset = KwThemePreset.light,
  });

  final KwConfig config;
  final KwApiClient? apiClient;
  final KwAuthHelper? authHelper;
  final KwUserSession? initialSession;
  final String initialLanguageCode;
  final KwThemePreset initialThemePreset;

  @override
  State<BrandPortalApp> createState() => _BrandPortalAppState();
}

class _BrandPortalAppState extends State<BrandPortalApp> {
  static const List<String> _featuredEmails = [
    'brand.aerovane@keepwell.demo',
    'brand.zenith@keepwell.demo',
    'brand.wavecrest@keepwell.demo',
    'platform@keepwell.demo',
  ];

  late final KwAuthHelper _authHelper;
  late final KwApiClient _apiClient;
  late final bool _ownsApiClient;
  late final bool _ownsAuthHelper;

  KwUserSession? _session;
  late KwThemePreset _themePreset;
  late String _languageCode;
  int _selectedIndex = 0;
  bool _signingIn = false;
  final TextEditingController _emailController = TextEditingController(
    text: 'brand.aerovane@keepwell.demo',
  );

  @override
  void initState() {
    super.initState();
    _session = widget.initialSession;
    _themePreset = widget.initialThemePreset;
    _languageCode = widget.initialLanguageCode;
    _ownsAuthHelper = widget.authHelper == null;
    _authHelper = widget.authHelper ?? KwAuthHelper(config: widget.config);
    _ownsApiClient = widget.apiClient == null;
    _apiClient = widget.apiClient ??
        KwApiClient(
          config: widget.config,
          tokenProvider: () => _session?.idToken,
        );
  }

  @override
  void dispose() {
    _emailController.dispose();
    if (_ownsApiClient) _apiClient.close();
    if (_ownsAuthHelper) _authHelper.close();
    super.dispose();
  }

  Future<void> _signIn(String email) async {
    final trimmed = email.trim();
    if (trimmed.isEmpty) return;
    setState(() => _signingIn = true);
    try {
      final session = await _authHelper.signInDemoPersona(trimmed);
      if (!mounted) return;
      setState(() {
        _session = session;
        _selectedIndex = 0;
        _signingIn = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _signingIn = false);
    }
  }

  void _signOut() {
    setState(() {
      _session = null;
      _selectedIndex = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    final locale = Locale(_languageCode);
    final brandStrings = BrandStrings.forLanguageCode(_languageCode);

    return KwLocaleScope(
      languageCode: _languageCode,
      child: MaterialApp(
        title: brandStrings.appTitle,
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
            ? _buildSignInScaffold(brandStrings)
            : _buildPortalShell(brandStrings, _session!),
      ),
    );
  }

  Widget _buildSignInScaffold(BrandStrings bs) {
    return Scaffold(
      appBar: AppBar(
        title: Text(bs.appTitle),
        actions: [
          _buildLanguageMenu(),
          _buildThemeMenu(bs),
          const SizedBox(width: KwSpacing.xs),
        ],
      ),
      body: Builder(
        builder: (context) {
          final theme = Theme.of(context);
          final cs = theme.colorScheme;
          return Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(KwSpacing.lg),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 680),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(KwSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: cs.primaryContainer,
                                borderRadius: KwShapes.radiusMedium,
                              ),
                              child: Icon(
                                Icons.business_center_rounded,
                                color: cs.onPrimaryContainer,
                              ),
                            ),
                            const SizedBox(width: KwSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    bs.signInTitle,
                                    style: theme.textTheme.headlineSmall
                                        ?.copyWith(fontWeight: FontWeight.w700),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    bs.signInSubtitle,
                                    style: theme.textTheme.bodyMedium?.copyWith(
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
                          bs.quickPersonasHeading,
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: KwSpacing.sm),
                        Wrap(
                          spacing: KwSpacing.sm,
                          runSpacing: KwSpacing.sm,
                          children: [
                            for (final email in _featuredEmails)
                              _PersonaSignInTile(
                                email: email,
                                disabled: _signingIn,
                                onPressed: () => _signIn(email),
                              ),
                          ],
                        ),
                        const SizedBox(height: KwSpacing.lg),
                        const Divider(),
                        const SizedBox(height: KwSpacing.md),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: InputDecoration(
                                  labelText: bs.customEmailLabel,
                                  prefixIcon:
                                      const Icon(Icons.alternate_email_rounded),
                                ),
                                onSubmitted: _signIn,
                              ),
                            ),
                            const SizedBox(width: KwSpacing.sm),
                            FilledButton(
                              key: const ValueKey('custom-sign-in-btn'),
                              onPressed: _signingIn
                                  ? null
                                  : () => _signIn(_emailController.text),
                              child: _signingIn
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Text(bs.signInButton),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPortalShell(BrandStrings bs, KwUserSession session) {
    final destinations = [
      (
        icon: Icons.forward_to_inbox_outlined,
        selectedIcon: Icons.forward_to_inbox_rounded,
        label: bs.navRequests,
      ),
      (
        icon: Icons.add_box_outlined,
        selectedIcon: Icons.add_box_rounded,
        label: bs.navSubmit,
      ),
      (
        icon: Icons.analytics_outlined,
        selectedIcon: Icons.analytics_rounded,
        label: bs.navAnalytics,
      ),
    ];

    final pages = [
      ForwardedRequestsScreen(
        api: _apiClient,
        session: session,
        brandStrings: bs,
      ),
      IntakeFormsScreen(
        api: _apiClient,
        session: session,
        brandStrings: bs,
      ),
      BrandAnalyticsScreen(
        api: _apiClient,
        config: widget.config,
        session: session,
        brandStrings: bs,
      ),
    ];

    return Builder(
      builder: (context) {
        final windowSize = KwWindowSize.of(context);
        final cs = Theme.of(context).colorScheme;

        return Scaffold(
          appBar: AppBar(
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(bs.appTitle),
                Text(
                  '${bs.signedInAsPrefix} ${session.email}',
                  key: const ValueKey('signed-in-as-label'),
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                ),
              ],
            ),
            actions: [
              _buildLanguageMenu(),
              _buildThemeMenu(bs),
              const SizedBox(width: KwSpacing.xs),
              TextButton.icon(
                key: const ValueKey('sign-out-btn'),
                onPressed: _signOut,
                icon: const Icon(Icons.logout_rounded),
                label: Text(bs.signOutLabel),
              ),
              const SizedBox(width: KwSpacing.xs),
            ],
          ),
          body: Row(
            children: [
              if (!windowSize.isCompact) ...[
                NavigationRail(
                  extended: windowSize.isLarge,
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (idx) =>
                      setState(() => _selectedIndex = idx),
                  destinations: [
                    for (final d in destinations)
                      NavigationRailDestination(
                        icon: Icon(d.icon),
                        selectedIcon: Icon(d.selectedIcon),
                        label: Text(d.label),
                      ),
                  ],
                ),
                const VerticalDivider(width: 1),
              ],
              Expanded(child: pages[_selectedIndex]),
            ],
          ),
          bottomNavigationBar: windowSize.isCompact
              ? NavigationBar(
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (idx) =>
                      setState(() => _selectedIndex = idx),
                  destinations: [
                    for (final d in destinations)
                      NavigationDestination(
                        icon: Icon(d.icon),
                        selectedIcon: Icon(d.selectedIcon),
                        label: d.label,
                      ),
                  ],
                )
              : null,
        );
      },
    );
  }

  Widget _buildLanguageMenu() {
    return PopupMenuButton<String>(
      key: const ValueKey('language-menu-btn'),
      tooltip: 'Language',
      initialValue: _languageCode,
      onSelected: (code) => setState(() => _languageCode = code),
      icon: const Icon(Icons.translate_rounded),
      itemBuilder: (context) => const [
        PopupMenuItem(value: 'en', child: Text('English (en)')),
        PopupMenuItem(value: 'hi', child: Text('हिन्दी (hi)')),
        PopupMenuItem(value: 'te', child: Text('తెలుగు (te)')),
      ],
    );
  }

  Widget _buildThemeMenu(BrandStrings bs) {
    return PopupMenuButton<KwThemePreset>(
      key: const ValueKey('theme-menu-btn'),
      tooltip: 'Theme',
      initialValue: _themePreset,
      onSelected: (preset) => setState(() => _themePreset = preset),
      icon: const Icon(Icons.contrast_rounded),
      itemBuilder: (context) => [
        PopupMenuItem(
          value: KwThemePreset.light,
          child: Text(bs.themeLight),
        ),
        PopupMenuItem(
          value: KwThemePreset.dark,
          child: Text(bs.themeDark),
        ),
        PopupMenuItem(
          value: KwThemePreset.highContrastLight,
          child: Text(bs.themeHighContrastLight),
        ),
        PopupMenuItem(
          value: KwThemePreset.highContrastDark,
          child: Text(bs.themeHighContrastDark),
        ),
      ],
    );
  }
}

class _PersonaSignInTile extends StatelessWidget {
  const _PersonaSignInTile({
    required this.email,
    required this.disabled,
    required this.onPressed,
  });

  final String email;
  final bool disabled;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final persona = KwAuthHelper.findPersonaByEmail(email);
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final isPlatform = persona?.role == KwRole.platform;

    return SizedBox(
      width: 295,
      child: OutlinedButton(
        key: ValueKey('persona-$email'),
        onPressed: disabled ? null : onPressed,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.all(KwSpacing.md),
          shape: KwShapes.rounded(KwShapes.medium),
          alignment: Alignment.centerLeft,
        ),
        child: Row(
          children: [
            Icon(
              isPlatform
                  ? Icons.admin_panel_settings_outlined
                  : Icons.verified_outlined,
              color: cs.primary,
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    persona?.displayName ?? email,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    email,
                    style: KwTheme.monoStyle(
                      context,
                      fontSize: 11,
                      color: cs.onSurfaceVariant,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
