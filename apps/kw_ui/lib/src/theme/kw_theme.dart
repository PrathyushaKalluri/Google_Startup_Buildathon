import 'package:flutter/material.dart';

import 'kw_shapes.dart';
import 'kw_spacing.dart';

/// A tonal colour triple for a semantic role.
@immutable
class KwColorRole {
  const KwColorRole({
    required this.accent,
    required this.container,
    required this.onContainer,
  });

  final Color accent;
  final Color container;
  final Color onContainer;

  static KwColorRole lerp(KwColorRole a, KwColorRole b, double t) {
    return KwColorRole(
      accent: Color.lerp(a.accent, b.accent, t) ?? a.accent,
      container: Color.lerp(a.container, b.container, t) ?? a.container,
      onContainer: Color.lerp(a.onContainer, b.onContainer, t) ?? a.onContainer,
    );
  }
}

/// Semantic colour tokens exposed via [ThemeExtension].
///
/// Components should read from `Theme.of(context).kwColors` rather than
/// hardcoding hex literals.
@immutable
class KwSemanticColors extends ThemeExtension<KwSemanticColors> {
  const KwSemanticColors({
    required this.safety,
    required this.urgent,
    required this.standard,
    required this.planned,
    required this.verified,
    required this.needsChecking,
    required this.declined,
    required this.liveVideo,
    required this.focusRing,
    required this.isProjectorMode,
  });

  final KwColorRole safety;
  final KwColorRole urgent;
  final KwColorRole standard;
  final KwColorRole planned;
  final KwColorRole verified;
  final KwColorRole needsChecking;
  final KwColorRole declined;
  final KwColorRole liveVideo;
  final Color focusRing;
  final bool isProjectorMode;

  static const KwSemanticColors light = KwSemanticColors(
    safety: KwColorRole(
      accent: Color(0xFFBA1A1A),
      container: Color(0xFFFFDAD6),
      onContainer: Color(0xFF410002),
    ),
    urgent: KwColorRole(
      accent: Color(0xFFC25900),
      container: Color(0xFFFFE0B2),
      onContainer: Color(0xFF4E2600),
    ),
    standard: KwColorRole(
      accent: Color(0xFF0B57D0),
      container: Color(0xFFD3E3FD),
      onContainer: Color(0xFF041E49),
    ),
    planned: KwColorRole(
      accent: Color(0xFF146C2E),
      container: Color(0xFFC4EED0),
      onContainer: Color(0xFF072711),
    ),
    verified: KwColorRole(
      accent: Color(0xFF146C2E),
      container: Color(0xFFC4EED0),
      onContainer: Color(0xFF072711),
    ),
    needsChecking: KwColorRole(
      accent: Color(0xFF8D4E00),
      container: Color(0xFFFFDCBE),
      onContainer: Color(0xFF2E1500),
    ),
    declined: KwColorRole(
      accent: Color(0xFFBA1A1A),
      container: Color(0xFFFFDAD6),
      onContainer: Color(0xFF410002),
    ),
    liveVideo: KwColorRole(
      accent: Color(0xFF006A6A),
      container: Color(0xFF9CF1F0),
      onContainer: Color(0xFF002020),
    ),
    focusRing: Color(0xFF0B57D0),
    isProjectorMode: false,
  );

  static const KwSemanticColors dark = KwSemanticColors(
    safety: KwColorRole(
      accent: Color(0xFFFFB4AB),
      container: Color(0xFF93000A),
      onContainer: Color(0xFFFFDAD6),
    ),
    urgent: KwColorRole(
      accent: Color(0xFFFFB77C),
      container: Color(0xFF6E3800),
      onContainer: Color(0xFFFFE0B2),
    ),
    standard: KwColorRole(
      accent: Color(0xFFA8C7FA),
      container: Color(0xFF0842A0),
      onContainer: Color(0xFFD3E3FD),
    ),
    planned: KwColorRole(
      accent: Color(0xFF6DD58C),
      container: Color(0xFF0F5223),
      onContainer: Color(0xFFC4EED0),
    ),
    verified: KwColorRole(
      accent: Color(0xFF6DD58C),
      container: Color(0xFF0F5223),
      onContainer: Color(0xFFC4EED0),
    ),
    needsChecking: KwColorRole(
      accent: Color(0xFFFFB870),
      container: Color(0xFF6A3B00),
      onContainer: Color(0xFFFFDCBE),
    ),
    declined: KwColorRole(
      accent: Color(0xFFFFB4AB),
      container: Color(0xFF93000A),
      onContainer: Color(0xFFFFDAD6),
    ),
    liveVideo: KwColorRole(
      accent: Color(0xFF4CDADB),
      container: Color(0xFF004F4F),
      onContainer: Color(0xFF9CF1F0),
    ),
    focusRing: Color(0xFFA8C7FA),
    isProjectorMode: false,
  );

  static const KwSemanticColors highContrastLight = KwSemanticColors(
    safety: KwColorRole(
      accent: Color(0xFF8C0009),
      container: Color(0xFFFFE5E2),
      onContainer: Color(0xFF280001),
    ),
    urgent: KwColorRole(
      accent: Color(0xFF8A3D00),
      container: Color(0xFFFFE7C7),
      onContainer: Color(0xFF2B1300),
    ),
    standard: KwColorRole(
      accent: Color(0xFF003B99),
      container: Color(0xFFDCE8FF),
      onContainer: Color(0xFF001438),
    ),
    planned: KwColorRole(
      accent: Color(0xFF0A4F1E),
      container: Color(0xFFD1F5DC),
      onContainer: Color(0xFF031B0A),
    ),
    verified: KwColorRole(
      accent: Color(0xFF0A4F1E),
      container: Color(0xFFD1F5DC),
      onContainer: Color(0xFF031B0A),
    ),
    needsChecking: KwColorRole(
      accent: Color(0xFF6B3900),
      container: Color(0xFFFFE3C9),
      onContainer: Color(0xFF1F0E00),
    ),
    declined: KwColorRole(
      accent: Color(0xFF8C0009),
      container: Color(0xFFFFE5E2),
      onContainer: Color(0xFF280001),
    ),
    liveVideo: KwColorRole(
      accent: Color(0xFF004F4F),
      container: Color(0xFFB5F7F6),
      onContainer: Color(0xFF001717),
    ),
    focusRing: Color(0xFF000000),
    isProjectorMode: false,
  );

  static const KwSemanticColors highContrastDark = KwSemanticColors(
    safety: KwColorRole(
      accent: Color(0xFFFFD2CC),
      container: Color(0xFF690005),
      onContainer: Color(0xFFFFFFFF),
    ),
    urgent: KwColorRole(
      accent: Color(0xFFFFD0A6),
      container: Color(0xFF542900),
      onContainer: Color(0xFFFFFFFF),
    ),
    standard: KwColorRole(
      accent: Color(0xFFCFE0FF),
      container: Color(0xFF002F7A),
      onContainer: Color(0xFFFFFFFF),
    ),
    planned: KwColorRole(
      accent: Color(0xFF9DF0B5),
      container: Color(0xFF003D16),
      onContainer: Color(0xFFFFFFFF),
    ),
    verified: KwColorRole(
      accent: Color(0xFF9DF0B5),
      container: Color(0xFF003D16),
      onContainer: Color(0xFFFFFFFF),
    ),
    needsChecking: KwColorRole(
      accent: Color(0xFFFFD09E),
      container: Color(0xFF522D00),
      onContainer: Color(0xFFFFFFFF),
    ),
    declined: KwColorRole(
      accent: Color(0xFFFFD2CC),
      container: Color(0xFF690005),
      onContainer: Color(0xFFFFFFFF),
    ),
    liveVideo: KwColorRole(
      accent: Color(0xFF8BF2F2),
      container: Color(0xFF003838),
      onContainer: Color(0xFFFFFFFF),
    ),
    focusRing: Color(0xFFFFFFFF),
    isProjectorMode: false,
  );

  static const KwSemanticColors projector = KwSemanticColors(
    safety: KwColorRole(
      accent: Color(0xFFFF6B6B),
      container: Color(0xFF5C0005),
      onContainer: Color(0xFFFFFFFF),
    ),
    urgent: KwColorRole(
      accent: Color(0xFFFFB74D),
      container: Color(0xFF4F2600),
      onContainer: Color(0xFFFFFFFF),
    ),
    standard: KwColorRole(
      accent: Color(0xFF8AB4F8),
      container: Color(0xFF002B6B),
      onContainer: Color(0xFFFFFFFF),
    ),
    planned: KwColorRole(
      accent: Color(0xFF81C995),
      container: Color(0xFF003D16),
      onContainer: Color(0xFFFFFFFF),
    ),
    verified: KwColorRole(
      accent: Color(0xFF81C995),
      container: Color(0xFF003D16),
      onContainer: Color(0xFFFFFFFF),
    ),
    needsChecking: KwColorRole(
      accent: Color(0xFFFFCC80),
      container: Color(0xFF4A2800),
      onContainer: Color(0xFFFFFFFF),
    ),
    declined: KwColorRole(
      accent: Color(0xFFFF6B6B),
      container: Color(0xFF5C0005),
      onContainer: Color(0xFFFFFFFF),
    ),
    liveVideo: KwColorRole(
      accent: Color(0xFF5CE1E6),
      container: Color(0xFF003638),
      onContainer: Color(0xFFFFFFFF),
    ),
    focusRing: Color(0xFFFFEB3B),
    isProjectorMode: true,
  );

  @override
  KwSemanticColors copyWith({
    KwColorRole? safety,
    KwColorRole? urgent,
    KwColorRole? standard,
    KwColorRole? planned,
    KwColorRole? verified,
    KwColorRole? needsChecking,
    KwColorRole? declined,
    KwColorRole? liveVideo,
    Color? focusRing,
    bool? isProjectorMode,
  }) {
    return KwSemanticColors(
      safety: safety ?? this.safety,
      urgent: urgent ?? this.urgent,
      standard: standard ?? this.standard,
      planned: planned ?? this.planned,
      verified: verified ?? this.verified,
      needsChecking: needsChecking ?? this.needsChecking,
      declined: declined ?? this.declined,
      liveVideo: liveVideo ?? this.liveVideo,
      focusRing: focusRing ?? this.focusRing,
      isProjectorMode: isProjectorMode ?? this.isProjectorMode,
    );
  }

  @override
  KwSemanticColors lerp(ThemeExtension<KwSemanticColors>? other, double t) {
    if (other is! KwSemanticColors) return this;
    return KwSemanticColors(
      safety: KwColorRole.lerp(safety, other.safety, t),
      urgent: KwColorRole.lerp(urgent, other.urgent, t),
      standard: KwColorRole.lerp(standard, other.standard, t),
      planned: KwColorRole.lerp(planned, other.planned, t),
      verified: KwColorRole.lerp(verified, other.verified, t),
      needsChecking: KwColorRole.lerp(needsChecking, other.needsChecking, t),
      declined: KwColorRole.lerp(declined, other.declined, t),
      liveVideo: KwColorRole.lerp(liveVideo, other.liveVideo, t),
      focusRing: Color.lerp(focusRing, other.focusRing, t) ?? focusRing,
      isProjectorMode: t < 0.5 ? isProjectorMode : other.isProjectorMode,
    );
  }
}

/// Convenience accessor for [KwSemanticColors] on [ThemeData].
extension KwThemeDataX on ThemeData {
  KwSemanticColors get kwColors =>
      extension<KwSemanticColors>() ??
      (brightness == Brightness.dark
          ? KwSemanticColors.dark
          : KwSemanticColors.light);
}

/// Supported Keepwell theme presets.
enum KwThemePreset {
  light,
  dark,
  highContrastLight,
  highContrastDark,
  projector,
}

/// Keepwell Material 3 Expressive theme builder (Design Spec §2–§4).
abstract final class KwTheme {
  static const Color brandSeed = Color(0xFF0B57D0);

  static ThemeData light({Locale? locale}) => _buildTheme(
        colorScheme: ColorScheme.fromSeed(
          seedColor: brandSeed,
          brightness: Brightness.light,
        ),
        semanticColors: KwSemanticColors.light,
        locale: locale,
      );

  static ThemeData dark({Locale? locale}) => _buildTheme(
        colorScheme: ColorScheme.fromSeed(
          seedColor: brandSeed,
          brightness: Brightness.dark,
        ),
        semanticColors: KwSemanticColors.dark,
        locale: locale,
      );

  static ThemeData highContrastLight({Locale? locale}) {
    final base = ColorScheme.fromSeed(
      seedColor: brandSeed,
      brightness: Brightness.light,
      contrastLevel: 1.0,
    );
    return _buildTheme(
      colorScheme: base.copyWith(
        surface: const Color(0xFFFFFFFF),
        onSurface: const Color(0xFF000000),
        outline: const Color(0xFF2B2B2B),
      ),
      semanticColors: KwSemanticColors.highContrastLight,
      locale: locale,
    );
  }

  static ThemeData highContrastDark({Locale? locale}) {
    final base = ColorScheme.fromSeed(
      seedColor: brandSeed,
      brightness: Brightness.dark,
      contrastLevel: 1.0,
    );
    return _buildTheme(
      colorScheme: base.copyWith(
        surface: const Color(0xFF0A0A0D),
        onSurface: const Color(0xFFFFFFFF),
        outline: const Color(0xFFD0D5DD),
      ),
      semanticColors: KwSemanticColors.highContrastDark,
      locale: locale,
    );
  }

  /// Stage Projector Mode: dark high-contrast (>= 7:1) with 1.35x base scale.
  static ThemeData projector({Locale? locale}) {
    final base = ColorScheme.fromSeed(
      seedColor: brandSeed,
      brightness: Brightness.dark,
      contrastLevel: 1.0,
    );
    return _buildTheme(
      colorScheme: base.copyWith(
        primary: const Color(0xFF8AB4F8),
        onPrimary: const Color(0xFF001B44),
        surface: const Color(0xFF090D16),
        surfaceContainerLowest: const Color(0xFF05080F),
        surfaceContainerLow: const Color(0xFF101726),
        surfaceContainer: const Color(0xFF162033),
        surfaceContainerHigh: const Color(0xFF1E2B42),
        onSurface: const Color(0xFFFFFFFF),
        onSurfaceVariant: const Color(0xFFE0E6F0),
        outline: const Color(0xFFAAB8D0),
      ),
      semanticColors: KwSemanticColors.projector,
      locale: locale,
      scaleFactor: 1.35,
    );
  }

  static ThemeData fromPreset(KwThemePreset preset, {Locale? locale}) {
    return switch (preset) {
      KwThemePreset.light => light(locale: locale),
      KwThemePreset.dark => dark(locale: locale),
      KwThemePreset.highContrastLight => highContrastLight(locale: locale),
      KwThemePreset.highContrastDark => highContrastDark(locale: locale),
      KwThemePreset.projector => projector(locale: locale),
    };
  }

  /// Monospace style with tabular figures for IDs, serials, error codes, OTPs.
  static TextStyle monoStyle(
    BuildContext context, {
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
  }) {
    final base = Theme.of(context).textTheme.bodyMedium ?? const TextStyle();
    return base.copyWith(
      fontFamily: 'monospace',
      fontSize: fontSize ?? base.fontSize,
      fontWeight: fontWeight ?? FontWeight.w600,
      color: color,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
  }

  static ThemeData _buildTheme({
    required ColorScheme colorScheme,
    required KwSemanticColors semanticColors,
    Locale? locale,
    double scaleFactor = 1.0,
  }) {
    final isIndic =
        locale?.languageCode == 'hi' || locale?.languageCode == 'te';
    final lineHeightMultiplier = isIndic ? 1.15 : 1.0;

    final baseTextTheme = colorScheme.brightness == Brightness.dark
        ? Typography.material2021().white
        : Typography.material2021().black;

    final scaledTextTheme = _scaleTextTheme(
      baseTextTheme,
      sizeScale: scaleFactor,
      heightMultiplier: lineHeightMultiplier,
      bodyColor: colorScheme.onSurface,
      displayColor: colorScheme.onSurface,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      textTheme: scaledTextTheme,
      extensions: <ThemeExtension<dynamic>>[semanticColors],
      focusColor: semanticColors.focusRing.withValues(alpha: 0.24),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: colorScheme.surfaceContainerLow,
        shape: KwShapes.rounded(
          KwShapes.medium,
          side: BorderSide(color: colorScheme.outlineVariant),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: KwShapes.rounded(KwShapes.small),
        side: BorderSide(color: colorScheme.outlineVariant),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(
            KwSpacing.minTouchTarget,
            KwSpacing.minTouchTarget,
          ),
          shape: KwShapes.rounded(KwShapes.full),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(
            KwSpacing.minTouchTarget,
            KwSpacing.minTouchTarget,
          ),
          shape: KwShapes.rounded(KwShapes.full),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: const Size(
            KwSpacing.minTouchTarget,
            KwSpacing.minTouchTarget,
          ),
          shape: KwShapes.rounded(KwShapes.full),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: const Size(
            KwSpacing.minTouchTarget,
            KwSpacing.minTouchTarget,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceContainerHighest.withValues(alpha: 0.45),
        border: OutlineInputBorder(
          borderRadius: KwShapes.radiusMedium,
          borderSide: BorderSide(color: colorScheme.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: KwShapes.radiusMedium,
          borderSide: BorderSide(color: semanticColors.focusRing, width: 2.5),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        showDragHandle: true,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(KwShapes.large),
          ),
        ),
        backgroundColor: colorScheme.surfaceContainerLow,
      ),
    );
  }

  static TextTheme _scaleTextTheme(
    TextTheme base, {
    required double sizeScale,
    required double heightMultiplier,
    required Color bodyColor,
    required Color displayColor,
  }) {
    TextStyle? adjust(TextStyle? style, Color color) {
      if (style == null) return null;
      final baseSize = style.fontSize ?? 14;
      final baseHeight = style.height ?? 1.35;
      return style.copyWith(
        fontSize: baseSize * sizeScale,
        height: baseHeight * heightMultiplier,
        color: color,
      );
    }

    return TextTheme(
      displayLarge: adjust(base.displayLarge, displayColor),
      displayMedium: adjust(base.displayMedium, displayColor),
      displaySmall: adjust(base.displaySmall, displayColor),
      headlineLarge: adjust(base.headlineLarge, displayColor),
      headlineMedium: adjust(base.headlineMedium, displayColor),
      headlineSmall: adjust(base.headlineSmall, displayColor),
      titleLarge: adjust(base.titleLarge, bodyColor),
      titleMedium: adjust(base.titleMedium, bodyColor),
      titleSmall: adjust(base.titleSmall, bodyColor),
      bodyLarge: adjust(base.bodyLarge, bodyColor),
      bodyMedium: adjust(base.bodyMedium, bodyColor),
      bodySmall: adjust(base.bodySmall, bodyColor),
      labelLarge: adjust(base.labelLarge, bodyColor),
      labelMedium: adjust(base.labelMedium, bodyColor),
      labelSmall: adjust(base.labelSmall, bodyColor),
    );
  }
}
