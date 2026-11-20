import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:kw_client/kw_client.dart';

import 'src/field_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();

  final config = KwConfig.fromEnvironment();
  final authHelper = KwAuthHelper(config: config);
  final api = KwApiClient(config: config);

  runApp(
    KeepwellFieldApp(
      api: api,
      authHelper: authHelper,
    ),
  );
}
