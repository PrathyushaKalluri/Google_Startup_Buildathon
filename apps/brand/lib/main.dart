import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:kw_client/kw_client.dart';

import 'src/brand_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();
  runApp(
    BrandPortalApp(
      config: KwConfig.fromEnvironment(),
    ),
  );
}
