import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'src/field_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();

  final params = Uri.base.queryParameters;
  final themeParam = params['theme']?.toLowerCase();
  final langParam = params['lang']?.toLowerCase();
  final demoAutoSignIn = params['demo'] == '1' || params['demo'] == 'true';

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

  final config = KwConfig.fromEnvironment();
  final authHelper = KwAuthHelper(config: config);
  final api = KwApiClient(config: config);

  runApp(
    KeepwellFieldApp(
      api: api,
      authHelper: authHelper,
      initialLanguageCode: lang,
      initialThemePreset: preset,
      initialSession: demoAutoSignIn
          ? KwAuthHelper.findPersonaByEmail('tech1.c_fw@keepwell.demo')
          : null,
    ),
  );
}
