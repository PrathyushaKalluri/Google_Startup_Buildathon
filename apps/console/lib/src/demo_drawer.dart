import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'console_state.dart';

/// Demo Control Drawer visible when `DEMO_MODE=true`.
///
/// Lists the 20 seeded Keepwell demo cases (`GET /v1/admin/demo/cases`),
/// supports Play Case, Reset Demo, language switching, theme presets, and
/// Projector Mode toggle.
class DemoControlDrawer extends StatefulWidget {
  const DemoControlDrawer({
    super.key,
    required this.controller,
  });

  final ConsoleController controller;

  @override
  State<DemoControlDrawer> createState() => _DemoControlDrawerState();
}

class _DemoControlDrawerState extends State<DemoControlDrawer> {
  List<DemoCase> _cases = const [];
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await widget.controller.apiClient.listDemoCases();
      if (mounted) {
        setState(() {
          _cases = page.items;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString();
        });
      }
    }
  }

  Future<void> _playCase(DemoCase demoCase) async {
    setState(() => _busy = true);
    try {
      await widget.controller.apiClient.playDemoCase(demoCase.caseId);
      await widget.controller.loadTickets();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Played ${demoCase.caseId} (${demoCase.centreKey}): ${demoCase.summary}',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not play ${demoCase.caseId}: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resetDemo() async {
    setState(() => _busy = true);
    try {
      await widget.controller.apiClient.resetDemo();
      await widget.controller.loadTickets();
      await _loadCases();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Demo environment reset cleanly.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Demo reset failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final ctrl = widget.controller;

    return Drawer(
      width: 390,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                KwSpacing.md,
                KwSpacing.md,
                KwSpacing.sm,
                KwSpacing.sm,
              ),
              child: Row(
                children: [
                  Icon(Icons.science_rounded, color: cs.primary),
                  const SizedBox(width: KwSpacing.xs),
                  Expanded(
                    child: Text(
                      'Demo Control',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: _busy ? null : _resetDemo,
                    icon: const Icon(Icons.restart_alt_rounded, size: 18),
                    label: const Text('Reset'),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(KwSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Projector Mode'),
                    subtitle: const Text('1.35x scale, high-contrast dark, clean stage'),
                    value: ctrl.projectorMode,
                    onChanged: ctrl.setProjectorMode,
                  ),
                  const SizedBox(height: KwSpacing.xs),
                  Text('Language', style: theme.textTheme.labelLarge),
                  const SizedBox(height: KwSpacing.xxs),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'en', label: Text('EN')),
                      ButtonSegment(value: 'hi', label: Text('हिन्दी')),
                      ButtonSegment(value: 'te', label: Text('తెలుగు')),
                    ],
                    selected: {ctrl.languageCode},
                    onSelectionChanged: (set) => ctrl.setLanguage(set.first),
                  ),
                  const SizedBox(height: KwSpacing.sm),
                  Text('Theme Preset', style: theme.textTheme.labelLarge),
                  const SizedBox(height: KwSpacing.xxs),
                  Wrap(
                    spacing: KwSpacing.xs,
                    runSpacing: KwSpacing.xs,
                    children: [
                      for (final preset in KwThemePreset.values)
                        ChoiceChip(
                          label: Text(_presetLabel(preset)),
                          selected: ctrl.themePreset == preset,
                          onSelected: (_) => ctrl.setThemePreset(preset),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                KwSpacing.md,
                KwSpacing.sm,
                KwSpacing.md,
                KwSpacing.xs,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Seeded Cases (${_cases.length})',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Reload demo cases',
                    onPressed: _loading ? null : _loadCases,
                    icon: const Icon(Icons.refresh_rounded, size: 20),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _loading
                  ? const Padding(
                      padding: EdgeInsets.all(KwSpacing.md),
                      child: KwSkeletonLoader(lines: 6),
                    )
                  : _error != null
                      ? KwErrorState(
                          title: 'Demo cases unavailable',
                          body: _error,
                          onRetry: _loadCases,
                        )
                      : _cases.isEmpty
                          ? const KwEmptyState(
                              title: 'No demo cases loaded',
                              body: 'Start the mock API server or reset demo data.',
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.fromLTRB(
                                KwSpacing.md,
                                0,
                                KwSpacing.md,
                                KwSpacing.md,
                              ),
                              itemCount: _cases.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: KwSpacing.xs),
                              itemBuilder: (context, index) {
                                final item = _cases[index];
                                return Card(
                                  child: Padding(
                                    padding: const EdgeInsets.all(KwSpacing.sm),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Wrap(
                                          spacing: KwSpacing.xs,
                                          runSpacing: KwSpacing.xxs,
                                          crossAxisAlignment:
                                              WrapCrossAlignment.center,
                                          children: [
                                            Text(
                                              item.caseId,
                                              style: KwTheme.monoStyle(
                                                context,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            KwUrgencyChip(
                                              urgency: KwUrgencyClass.fromWire(
                                                item.urgencyClass,
                                              ),
                                              compact: true,
                                            ),
                                            if (item.stageCandidate)
                                              Container(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                  horizontal: 6,
                                                  vertical: 2,
                                                ),
                                                decoration: BoxDecoration(
                                                  color: cs.primaryContainer,
                                                  borderRadius:
                                                      KwShapes.radiusSmall,
                                                ),
                                                child: Text(
                                                  'STAGE',
                                                  style: theme
                                                      .textTheme.labelSmall
                                                      ?.copyWith(
                                                    color:
                                                        cs.onPrimaryContainer,
                                                    fontWeight: FontWeight.w700,
                                                  ),
                                                ),
                                              ),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          item.summary,
                                          style: theme.textTheme.bodySmall,
                                        ),
                                        const SizedBox(height: 6),
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                '${item.centreKey} · ${item.channel}',
                                                style: theme
                                                    .textTheme.labelSmall
                                                    ?.copyWith(
                                                  color: cs.onSurfaceVariant,
                                                ),
                                              ),
                                            ),
                                            FilledButton.tonal(
                                              onPressed: _busy
                                                  ? null
                                                  : () => _playCase(item),
                                              child: const Text('Play Case'),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
    );
  }

  String _presetLabel(KwThemePreset preset) {
    return switch (preset) {
      KwThemePreset.light => 'Light',
      KwThemePreset.dark => 'Dark',
      KwThemePreset.highContrastLight => 'HC Light',
      KwThemePreset.highContrastDark => 'HC Dark',
      KwThemePreset.projector => 'Projector',
    };
  }
}
