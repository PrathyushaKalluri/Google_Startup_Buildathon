import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:kw_ui/kw_ui.dart';

import 'src/household_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();

  final uri = Uri.base;
  final params = uri.queryParameters;
  final themeParam = params['theme']?.toLowerCase();
  final langParam = params['lang']?.toLowerCase();
  final preset = switch (themeParam) {
    'dark' => KwThemePreset.dark,
    'hc_light' => KwThemePreset.highContrastLight,
    'hc_dark' => KwThemePreset.highContrastDark,
    _ => KwThemePreset.light,
  };
  final lang =
      (langParam == 'hi' || langParam == 'te' || langParam == 'en')
          ? langParam!
          : 'en';
  final route = uri.fragment.isNotEmpty ? uri.fragment : uri.path;

  runApp(
    KeepwellHouseholdApp(
      initialRoute: route,
      initialLanguage: lang,
      initialThemePreset: preset,
    ),
  );
}
