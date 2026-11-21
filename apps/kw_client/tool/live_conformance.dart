// Consumer-driven contract check: Part B's kw_client against a running Part A.
// Usage: dart run tool/live_conformance.dart http://localhost:8000/v1
import 'dart:io';

import 'package:kw_client/kw_client.dart';

Future<void> main(List<String> args) async {
  final base = args.isNotEmpty ? args.first : 'http://localhost:8000/v1';
  final failures = <String>[];
  var passed = 0;

  Future<T?> check<T>(String name, Future<T> Function() fn) async {
    try {
      final v = await fn();
      passed++;
      stdout.writeln('PASS $name');
      return v;
    } catch (e) {
      failures.add('$name: $e');
      stdout.writeln('FAIL $name: $e');
      return null;
    }
  }

  KwApiClient client(String email) => KwApiClient(
        config: KwConfig(apiBaseUrl: base, demoMode: true),
        tokenProvider: () => 'demo:$email',
      );

  final fw = client('console.c_fw@keepwell.demo');
  final platform = client('platform@keepwell.demo');
  final tech = client('tech1.c_fw@keepwell.demo');
  final parts = client('parts.demo@keepwell.demo');
  final brand = client('brand.aerovane@keepwell.demo');

  await check('healthz', () => fw.healthz());
  await check('readyz', () => fw.readyz());
  await check('version', () => fw.version());
  final tickets = await check('listTickets', () => fw.listTickets(limit: 20));
  if (tickets != null && tickets.items.isNotEmpty) {
    final t = tickets.items.first;
    await check('getTicket', () => fw.getTicket(t.id));
    if (t.appliance != null) {
      await check('applianceTimeline', () => fw.getApplianceTimeline(t.appliance!.id));
    }
  } else {
    failures.add('listTickets: no tickets for c_fw');
  }
  await check('centreOverview', () => fw.getCentreOverview());
  await check('centreTechnicians', () => fw.getCentreTechnicians());
  await check('centreCalendar', () => fw.getCentreCalendar());
  await check('centreStock', () => fw.getCentreStock());
  await check('centrePrices', () => fw.getCentrePrices());
  await check('centreOverrides', () => fw.getCentreOverrides());
  final fixes = await check('listSafeFixes', () => fw.listSafeFixes());
  if (fixes != null && fixes.items.isNotEmpty) {
    await check('getSafeFix', () => fw.getSafeFix(fixes.items.first.code));
  }
  await check('myJobs', () => tech.getMyJobs());
  await check('partsRequests', () => parts.listPartsRequests());
  await check('brandRequests', () => brand.listBrandRequests());
  await check('brandAnalytics', () => brand.getBrandAnalytics());
  await check('demoCases', () => platform.listDemoCases());
  final hh = await check('demoHouseholds', () => platform.listDemoHouseholds(centreKey: 'c_fw'));
  if (hh != null && hh.items.isNotEmpty) {
    final token = hh.items.first.magicToken;
    await check('publicHome', () => fw.getPublicHome(token));
    await check('publicSession', () => fw.createPublicSession(token));
  }

  stdout.writeln('\nconformance: $passed passed, ${failures.length} failed');
  for (final f in failures) {
    stdout.writeln(' - $f');
  }
  exit(failures.isEmpty ? 0 : 1);
}
