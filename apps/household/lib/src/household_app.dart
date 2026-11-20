import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'call_dialer_screen.dart';
import 'home_memory_screen.dart';
import 'household_l10n.dart';
import 'quote_approval_screen.dart';
import 'video_link_screen.dart';
import 'whatsapp_simulator_screen.dart';

/// Parsed deep route for Keepwell Household surfaces.
@immutable
class HouseholdRoute {
  const HouseholdRoute({
    required this.surface,
    this.token = 'demo-magic-token',
    this.otpOnly = false,
  });

  final HouseholdSurface surface;
  final String token;
  final bool otpOnly;

  static HouseholdRoute parse(String? rawPath) {
    final uri = Uri.tryParse(rawPath ?? '/') ?? Uri(path: '/');
    final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segments.isEmpty || segments.first == 'whatsapp') {
      return const HouseholdRoute(surface: HouseholdSurface.whatsapp);
    }
    final head = segments.first.toLowerCase();
    final token =
        segments.length > 1 && segments[1].isNotEmpty ? segments[1] : 'demo-token';
    return switch (head) {
      'call' => const HouseholdRoute(surface: HouseholdSurface.call),
      'v' => HouseholdRoute(surface: HouseholdSurface.video, token: token),
      'home' => HouseholdRoute(surface: HouseholdSurface.home, token: token),
      'quotes' => HouseholdRoute(
          surface: HouseholdSurface.quoteOtp,
          token: token,
          otpOnly: false,
        ),
      'otp' => HouseholdRoute(
          surface: HouseholdSurface.quoteOtp,
          token: token,
          otpOnly: true,
        ),
      _ => const HouseholdRoute(surface: HouseholdSurface.whatsapp),
    };
  }
}

enum HouseholdSurface {
  whatsapp,
  call,
  video,
  home,
  quoteOtp,
}

/// Root widget for the Keepwell Zero-Sign-In Household Surfaces web app.
class KeepwellHouseholdApp extends StatefulWidget {
  const KeepwellHouseholdApp({
    super.key,
    this.config,
    this.apiClient,
    this.liveCallClient,
    this.initialRoute,
    this.initialLanguage = 'en',
    this.initialThemePreset = KwThemePreset.light,
  });

  final KwConfig? config;
  final KwApiClient? apiClient;
  final LiveCallClient? liveCallClient;
  final String? initialRoute;
  final String initialLanguage;
  final KwThemePreset initialThemePreset;

  @override
  State<KeepwellHouseholdApp> createState() => _KeepwellHouseholdAppState();
}

class _KeepwellHouseholdAppState extends State<KeepwellHouseholdApp> {
  late final KwConfig _config;
  late final KwApiClient _apiClient;
  late final LiveCallClient _liveCallClient;
  late final bool _ownsApiClient;
  late final bool _ownsLiveCallClient;

  late String _languageCode;
  late KwThemePreset _themePreset;
  late HouseholdRoute _activeRoute;

  // Default to Frost and Wave Service Point, Kukatpally (c_fw) per Contract §3.
  KwCentreIdentity _activeCentre = KwAuthHelper.demoCentres[2];
  DemoHousehold? _activeHousehold;

  @override
  void initState() {
    super.initState();
    _config = widget.config ?? KwConfig.fromEnvironment();
    _ownsApiClient = widget.apiClient == null;
    _ownsLiveCallClient = widget.liveCallClient == null;
    _apiClient = widget.apiClient ?? KwApiClient(config: _config);
    _liveCallClient = widget.liveCallClient ?? LiveCallClient(config: _config);

    _languageCode = widget.initialLanguage;
    _themePreset = widget.initialThemePreset;

    final browserRoute = widget.initialRoute ??
        WidgetsBinding.instance.platformDispatcher.defaultRouteName;
    _activeRoute = HouseholdRoute.parse(browserRoute);
  }

  @override
  void dispose() {
    if (_ownsApiClient) {
      _apiClient.close();
    }
    if (_ownsLiveCallClient) {
      unawaited(_liveCallClient.dispose());
    }
    super.dispose();
  }

  String get _effectiveToken {
    final hhToken = _activeHousehold?.magicToken;
    if (hhToken != null && hhToken.isNotEmpty) return hhToken;
    return _activeRoute.token;
  }

  void _navigateToPath(String path) {
    setState(() {
      _activeRoute = HouseholdRoute.parse(path);
    });
  }

  void _selectSurface(HouseholdSurface surface) {
    setState(() {
      _activeRoute = HouseholdRoute(
        surface: surface,
        token: _effectiveToken,
        otpOnly: false,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final locale = Locale(_languageCode);
    final theme = KwTheme.fromPreset(_themePreset, locale: locale);

    return KwLocaleScope(
      languageCode: _languageCode,
      child: MaterialApp(
        title: 'Keepwell Household',
        debugShowCheckedModeBanner: false,
        locale: locale,
        supportedLocales: const <Locale>[
          Locale('en'),
          Locale('hi'),
          Locale('te'),
        ],
        localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        theme: theme,
        onGenerateRoute: (settings) {
          final parsed = settings.name != null && settings.name != '/'
              ? HouseholdRoute.parse(settings.name)
              : _activeRoute;
          return MaterialPageRoute<void>(
            settings: settings,
            builder: (context) => _HouseholdShell(
              route: parsed,
              activeCentre: _activeCentre,
              activeHousehold: _activeHousehold,
              languageCode: _languageCode,
              themePreset: _themePreset,
              apiClient: _apiClient,
              liveCallClient: _liveCallClient,
              onSelectSurface: _selectSurface,
              onNavigatePath: _navigateToPath,
              onCentreChanged: (centre) {
                setState(() {
                  _activeCentre = centre;
                });
              },
              onHouseholdChanged: (household) {
                setState(() {
                  _activeHousehold = household;
                });
              },
              onLanguageChanged: (lang) {
                setState(() {
                  _languageCode = lang;
                });
              },
              onThemePresetChanged: (preset) {
                setState(() {
                  _themePreset = preset;
                });
              },
            ),
          );
        },
        home: _HouseholdShell(
          route: _activeRoute,
          activeCentre: _activeCentre,
          activeHousehold: _activeHousehold,
          languageCode: _languageCode,
          themePreset: _themePreset,
          apiClient: _apiClient,
          liveCallClient: _liveCallClient,
          onSelectSurface: _selectSurface,
          onNavigatePath: _navigateToPath,
          onCentreChanged: (centre) {
            setState(() {
              _activeCentre = centre;
            });
          },
          onHouseholdChanged: (household) {
            setState(() {
              _activeHousehold = household;
            });
          },
          onLanguageChanged: (lang) {
            setState(() {
              _languageCode = lang;
            });
          },
          onThemePresetChanged: (preset) {
            setState(() {
              _themePreset = preset;
            });
          },
        ),
      ),
    );
  }
}

class _HouseholdShell extends StatelessWidget {
  const _HouseholdShell({
    required this.route,
    required this.activeCentre,
    required this.activeHousehold,
    required this.languageCode,
    required this.themePreset,
    required this.apiClient,
    required this.liveCallClient,
    required this.onSelectSurface,
    required this.onNavigatePath,
    required this.onCentreChanged,
    required this.onHouseholdChanged,
    required this.onLanguageChanged,
    required this.onThemePresetChanged,
  });

  final HouseholdRoute route;
  final KwCentreIdentity activeCentre;
  final DemoHousehold? activeHousehold;
  final String languageCode;
  final KwThemePreset themePreset;
  final KwApiClient apiClient;
  final LiveCallClient liveCallClient;
  final ValueChanged<HouseholdSurface> onSelectSurface;
  final ValueChanged<String> onNavigatePath;
  final ValueChanged<KwCentreIdentity> onCentreChanged;
  final ValueChanged<DemoHousehold?> onHouseholdChanged;
  final ValueChanged<String> onLanguageChanged;
  final ValueChanged<KwThemePreset> onThemePresetChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final hStrings = HouseholdStrings.of(context);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: cs.surfaceContainerLow,
        surfaceTintColor: Colors.transparent,
        titleSpacing: KwSpacing.md,
        title: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: cs.primaryContainer,
                borderRadius: KwShapes.radiusSmall,
              ),
              child: Icon(
                Icons.home_repair_service_rounded,
                color: cs.onPrimaryContainer,
                size: 20,
              ),
            ),
            const SizedBox(width: KwSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    activeCentre.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '${activeCentre.locality} · ${hStrings.zeroSignInBadge}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Switch language',
            initialValue: languageCode,
            onSelected: onLanguageChanged,
            icon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.translate_rounded, size: 18),
                const SizedBox(width: 4),
                Text(
                  languageCode.toUpperCase(),
                  style: KwTheme.monoStyle(context, fontSize: 12),
                ),
              ],
            ),
            itemBuilder: (_) => const <PopupMenuEntry<String>>[
              PopupMenuItem<String>(value: 'en', child: Text('English (EN)')),
              PopupMenuItem<String>(value: 'hi', child: Text('हिन्दी (HI)')),
              PopupMenuItem<String>(value: 'te', child: Text('తెలుగు (TE)')),
            ],
          ),
          PopupMenuButton<KwThemePreset>(
            tooltip: 'Switch theme',
            initialValue: themePreset,
            onSelected: onThemePresetChanged,
            icon: Icon(
              themePreset == KwThemePreset.dark ||
                      themePreset == KwThemePreset.highContrastDark
                  ? Icons.dark_mode_rounded
                  : Icons.light_mode_rounded,
            ),
            itemBuilder: (_) => <PopupMenuEntry<KwThemePreset>>[
              PopupMenuItem<KwThemePreset>(
                value: KwThemePreset.light,
                child: Text(hStrings.themeLight),
              ),
              PopupMenuItem<KwThemePreset>(
                value: KwThemePreset.dark,
                child: Text(hStrings.themeDark),
              ),
              PopupMenuItem<KwThemePreset>(
                value: KwThemePreset.highContrastLight,
                child: Text('${hStrings.themeHighContrast} (Light)'),
              ),
              PopupMenuItem<KwThemePreset>(
                value: KwThemePreset.highContrastDark,
                child: Text('${hStrings.themeHighContrast} (Dark)'),
              ),
            ],
          ),
          const SizedBox(width: KwSpacing.xs),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(54),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(
              KwSpacing.md,
              0,
              KwSpacing.md,
              KwSpacing.xs,
            ),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: cs.outlineVariant)),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _NavPill(
                    icon: Icons.chat_bubble_outline_rounded,
                    label: hStrings.navWhatsApp,
                    selected: route.surface == HouseholdSurface.whatsapp,
                    onTap: () => onSelectSurface(HouseholdSurface.whatsapp),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  _NavPill(
                    icon: Icons.call_rounded,
                    label: hStrings.navCall,
                    selected: route.surface == HouseholdSurface.call,
                    onTap: () => onSelectSurface(HouseholdSurface.call),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  _NavPill(
                    icon: Icons.videocam_rounded,
                    label: hStrings.navVideo,
                    selected: route.surface == HouseholdSurface.video,
                    onTap: () => onSelectSurface(HouseholdSurface.video),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  _NavPill(
                    icon: Icons.home_outlined,
                    label: hStrings.navHome,
                    selected: route.surface == HouseholdSurface.home,
                    onTap: () => onSelectSurface(HouseholdSurface.home),
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  _NavPill(
                    icon: Icons.receipt_long_rounded,
                    label: hStrings.navQuoteOtp,
                    selected: route.surface == HouseholdSurface.quoteOtp,
                    onTap: () => onSelectSurface(HouseholdSurface.quoteOtp),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      body: SafeArea(
        child: switch (route.surface) {
          HouseholdSurface.whatsapp => WhatsAppSimulatorScreen(
              apiClient: apiClient,
              activeCentre: activeCentre,
              onCentreChanged: onCentreChanged,
              activeHousehold: activeHousehold,
              onHouseholdChanged: onHouseholdChanged,
              onOpenRoute: onNavigatePath,
            ),
          HouseholdSurface.call => CallDialerScreen(
              liveCallClient: liveCallClient,
              activeCentre: activeCentre,
              callerNumber: activeHousehold?.phoneMasked ?? '+919848000001',
              languageHint: languageCode,
              onSwitchToVideoToken: (token) => onNavigatePath('/v/$token'),
            ),
          HouseholdSurface.video => VideoLinkScreen(
              token: route.token,
              liveCallClient: liveCallClient,
              activeCentre: activeCentre,
              onStopVideoToVoice: () => onSelectSurface(HouseholdSurface.call),
            ),
          HouseholdSurface.home => HomeMemoryScreen(
              token: route.token,
              apiClient: apiClient,
              activeCentre: activeCentre,
            ),
          HouseholdSurface.quoteOtp => QuoteApprovalScreen(
              token: route.token,
              apiClient: apiClient,
              activeCentre: activeCentre,
              otpOnly: route.otpOnly,
            ),
        },
      ),
    );
  }
}

class _NavPill extends StatelessWidget {
  const _NavPill({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: ChoiceChip(
        avatar: Icon(
          icon,
          size: 18,
          color: selected ? cs.onSecondaryContainer : cs.onSurfaceVariant,
        ),
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
      ),
    );
  }
}
