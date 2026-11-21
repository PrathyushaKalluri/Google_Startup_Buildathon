import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'src/board_screen.dart';
import 'src/calendar_screen.dart' deferred as calendar_deferred;
import 'src/console_state.dart';
import 'src/demo_drawer.dart';
import 'src/operations_screen.dart';
import 'src/overview_screen.dart' deferred as overview_deferred;
import 'src/sign_in_screen.dart';
import 'src/stage_view_screen.dart';
import 'src/test_call_sheet.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();

  final uri = Uri.base;
  final params = uri.queryParameters;
  final initialDestination = _resolveInitialDestination(uri);
  final themeParam = params['theme']?.toLowerCase();
  final langParam = params['lang']?.toLowerCase();
  final demoAutoSignIn = params['signin'] != '1' && params['signin'] != 'true';

  final controller = ConsoleController(
    initialDestination: initialDestination,
    initialProjectorMode: themeParam == 'projector',
    initialSession: demoAutoSignIn
        ? KwAuthHelper.findPersonaByEmail('console.c_fw@keepwell.demo')
        : null,
  );
  if (themeParam == 'dark') {
    controller.setThemePreset(KwThemePreset.dark);
  } else if (themeParam == 'hc_light') {
    controller.setThemePreset(KwThemePreset.highContrastLight);
  } else if (themeParam == 'hc_dark') {
    controller.setThemePreset(KwThemePreset.highContrastDark);
  }
  if (langParam == 'hi' || langParam == 'te' || langParam == 'en') {
    controller.setLanguage(langParam!);
  }
  runApp(KeepwellConsoleApp(controller: controller));
}

ConsoleDestination _resolveInitialDestination(Uri uri) {
  final path = uri.path.toLowerCase();
  final fragment = uri.fragment.toLowerCase();
  if (path.endsWith('/stage') ||
      fragment == '/stage' ||
      fragment == 'stage' ||
      fragment.startsWith('/stage?')) {
    return ConsoleDestination.stage;
  }
  return ConsoleDestination.board;
}

/// Root widget for Keepwell Centre Console & Live Stage View.
class KeepwellConsoleApp extends StatelessWidget {
  const KeepwellConsoleApp({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final theme = KwTheme.fromPreset(
          controller.themePreset,
          locale: controller.locale,
        );
        return KwLocaleScope(
          languageCode: controller.languageCode,
          child: MaterialApp(
            title: 'Keepwell Centre Console',
            debugShowCheckedModeBanner: false,
            theme: theme,
            locale: controller.locale,
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
            onGenerateRoute: (settings) {
              if (settings.name == '/stage') {
                controller.setDestination(ConsoleDestination.stage);
              }
              return MaterialPageRoute<void>(
                settings: settings,
                builder: (_) => controller.isSignedIn
                    ? ConsoleShell(controller: controller)
                    : SignInScreen(controller: controller),
              );
            },
            home: controller.isSignedIn
                ? ConsoleShell(controller: controller)
                : SignInScreen(controller: controller),
          ),
        );
      },
    );
  }
}

/// Adaptive shell supporting compact, medium, expanded, and large viewports,
/// plus clean Projector Mode chrome hiding for Live Stage View.
class ConsoleShell extends StatelessWidget {
  const ConsoleShell({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  Widget build(BuildContext context) {
    final size = KwWindowSize.of(context);
    final hideChrome = controller.projectorMode &&
        controller.destination == ConsoleDestination.stage;
    final selectedIndex = controller.destination.index;

    final body = switch (controller.destination) {
      ConsoleDestination.board => BoardScreen(controller: controller),
      ConsoleDestination.stage => StageViewScreen(controller: controller),
      ConsoleDestination.calendar => _DeferredPane(
          load: calendar_deferred.loadLibrary,
          builder: () => calendar_deferred.CalendarScreen(controller: controller),
        ),
      ConsoleDestination.overview => _DeferredPane(
          load: overview_deferred.loadLibrary,
          builder: () => overview_deferred.OverviewScreen(controller: controller),
        ),
      ConsoleDestination.operations => OperationsScreen(controller: controller),
    };

    if (hideChrome) {
      return Scaffold(
        endDrawer: controller.config.demoMode
            ? DemoControlDrawer(controller: controller)
            : null,
        body: SafeArea(child: body),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.support_agent_rounded),
            const SizedBox(width: KwSpacing.xs),
            Flexible(
              child: Text(
                controller.session?.displayName ?? 'Keepwell Centre Console',
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          FilledButton.tonalIcon(
            onPressed: () =>
                showTestCallSheet(context, controller: controller),
            icon: const Icon(Icons.phone_in_talk_rounded, size: 18),
            label: const Text('Test Call'),
          ),
          const SizedBox(width: KwSpacing.xs),
          PopupMenuButton<String>(
            tooltip: 'Language',
            icon: const Icon(Icons.translate_rounded),
            onSelected: controller.setLanguage,
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'en', child: Text('English (en)')),
              PopupMenuItem(value: 'hi', child: Text('हिन्दी (hi)')),
              PopupMenuItem(value: 'te', child: Text('తెలుగు (te)')),
            ],
          ),
          PopupMenuButton<KwThemePreset>(
            tooltip: 'Theme',
            icon: const Icon(Icons.contrast_rounded),
            onSelected: controller.setThemePreset,
            itemBuilder: (_) => const [
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
          ),
          if (controller.config.demoMode)
            Builder(
              builder: (ctx) => IconButton(
                key: const Key('open_demo_drawer_button'),
                tooltip: 'Demo Control Drawer',
                onPressed: () => Scaffold.of(ctx).openEndDrawer(),
                icon: const Icon(Icons.science_rounded),
              ),
            ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: controller.signOut,
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      endDrawer: controller.config.demoMode
          ? DemoControlDrawer(controller: controller)
          : null,
      bottomNavigationBar: size.isCompact
          ? NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: (i) =>
                  controller.setDestination(ConsoleDestination.values[i]),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.view_kanban_outlined),
                  selectedIcon: Icon(Icons.view_kanban_rounded),
                  label: 'Board',
                ),
                NavigationDestination(
                  icon: Icon(Icons.live_tv_outlined),
                  selectedIcon: Icon(Icons.live_tv_rounded),
                  label: 'Stage',
                ),
                NavigationDestination(
                  icon: Icon(Icons.calendar_month_outlined),
                  selectedIcon: Icon(Icons.calendar_month_rounded),
                  label: 'Calendar',
                ),
                NavigationDestination(
                  icon: Icon(Icons.insights_outlined),
                  selectedIcon: Icon(Icons.insights_rounded),
                  label: 'Overview',
                ),
                NavigationDestination(
                  icon: Icon(Icons.table_chart_outlined),
                  selectedIcon: Icon(Icons.table_chart_rounded),
                  label: 'Ops',
                ),
              ],
            )
          : null,
      body: size.isCompact
          ? body
          : Row(
              children: [
                NavigationRail(
                  extended: size.isLarge,
                  selectedIndex: selectedIndex,
                  onDestinationSelected: (i) =>
                      controller.setDestination(ConsoleDestination.values[i]),
                  destinations: const [
                    NavigationRailDestination(
                      icon: Icon(Icons.view_kanban_outlined),
                      selectedIcon: Icon(Icons.view_kanban_rounded),
                      label: Text('Case Board'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.live_tv_outlined),
                      selectedIcon: Icon(Icons.live_tv_rounded),
                      label: Text('Live Stage'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.calendar_month_outlined),
                      selectedIcon: Icon(Icons.calendar_month_rounded),
                      label: Text('Calendar'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.insights_outlined),
                      selectedIcon: Icon(Icons.insights_rounded),
                      label: Text('Overview'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.table_chart_outlined),
                      selectedIcon: Icon(Icons.table_chart_rounded),
                      label: Text('Operations'),
                    ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: body),
              ],
            ),
    );
  }
}

class _DeferredPane extends StatefulWidget {
  const _DeferredPane({required this.load, required this.builder});

  final Future<void> Function() load;
  final Widget Function() builder;

  @override
  State<_DeferredPane> createState() => _DeferredPaneState();
}

class _DeferredPaneState extends State<_DeferredPane> {
  late Future<void> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  @override
  void didUpdateWidget(covariant _DeferredPane oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.load != widget.load) {
      _future = widget.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.done) {
          return widget.builder();
        }
        return const Center(child: CircularProgressIndicator());
      },
    );
  }
}
