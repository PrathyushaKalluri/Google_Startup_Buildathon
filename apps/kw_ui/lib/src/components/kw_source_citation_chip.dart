import 'package:flutter/material.dart';

import '../l10n/kw_strings.dart';
import '../theme/kw_shapes.dart';
import '../theme/kw_spacing.dart';
import '../theme/kw_theme.dart';

/// Manual / KB citation chip with document title, optional page badge,
/// and tap-to-open excerpt sheet (Design Spec §6, PAIR Explainability).
class KwSourceCitationChip extends StatelessWidget {
  const KwSourceCitationChip({
    super.key,
    required this.docTitle,
    required this.snippet,
    this.page,
    this.uri,
    this.onTap,
  });

  final String docTitle;
  final String snippet;
  final int? page;
  final String? uri;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = KwStrings.of(context);
    final pageLabel = page != null ? '${strings.sourcePagePrefix}$page' : null;

    return Semantics(
      button: true,
      label: pageLabel != null ? '$docTitle, $pageLabel' : docTitle,
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          minHeight: KwSpacing.minTouchTarget,
        ),
        child: Material(
          color: cs.secondaryContainer.withValues(alpha: 0.6),
          borderRadius: KwShapes.radiusSmall,
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap ?? () => _showSnippetSheet(context),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: KwSpacing.sm,
                vertical: KwSpacing.xs,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.menu_book_rounded,
                    size: 18,
                    color: cs.onSecondaryContainer,
                  ),
                  const SizedBox(width: KwSpacing.xs),
                  Flexible(
                    child: Text(
                      docTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: cs.onSecondaryContainer,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (pageLabel != null) ...[
                    const SizedBox(width: KwSpacing.xs),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: cs.surface,
                        borderRadius: KwShapes.radiusExtraSmall,
                      ),
                      child: Text(
                        pageLabel,
                        style: KwTheme.monoStyle(
                          context,
                          fontSize: theme.textTheme.labelSmall?.fontSize,
                          color: cs.onSurface,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _showSnippetSheet(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final strings = KwStrings.of(context);
    final pageLabel = page != null ? '${strings.sourcePagePrefix}$page' : null;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              KwSpacing.lg,
              KwSpacing.xs,
              KwSpacing.lg,
              KwSpacing.lg,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  strings.sourceSnippetTitle,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: cs.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: KwSpacing.xxs),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        docTitle,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (pageLabel != null)
                      Text(
                        pageLabel,
                        style: KwTheme.monoStyle(
                          sheetContext,
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: KwSpacing.md),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(KwSpacing.md),
                  decoration: BoxDecoration(
                    color: cs.surface,
                    borderRadius: KwShapes.radiusMedium,
                    border: Border.all(color: cs.outlineVariant),
                  ),
                  child: Text(
                    snippet,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
                if (uri != null && uri!.isNotEmpty) ...[
                  const SizedBox(height: KwSpacing.sm),
                  Text(
                    uri!,
                    style: KwTheme.monoStyle(
                      sheetContext,
                      fontSize: theme.textTheme.bodySmall?.fontSize,
                      color: cs.onSurfaceVariant,
                    ),
                  ),
                ],
                const SizedBox(height: KwSpacing.md),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.tonal(
                    onPressed: () => Navigator.of(sheetContext).pop(),
                    child: Text(strings.closeLabel),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
