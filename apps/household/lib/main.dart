import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import 'src/household_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SemanticsBinding.instance.ensureSemantics();
  runApp(const KeepwellHouseholdApp());
}
