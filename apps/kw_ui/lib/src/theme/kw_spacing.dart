import 'package:flutter/widgets.dart';

/// Keepwell spacing scale in logical pixels (dp).
abstract final class KwSpacing {
  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  /// Minimum interactive touch target size (WCAG 2.2 AA).
  static const double minTouchTarget = 48;
}

/// Adaptive window size classes per Keepwell Design Spec §5.
enum KwWindowSize {
  /// `< 600 dp`
  compact,

  /// `600–839 dp`
  medium,

  /// `840–1199 dp`
  expanded,

  /// `>= 1200 dp`
  large;

  static KwWindowSize fromWidth(double width) {
    if (width < 600) return KwWindowSize.compact;
    if (width < 840) return KwWindowSize.medium;
    if (width < 1200) return KwWindowSize.expanded;
    return KwWindowSize.large;
  }

  static KwWindowSize of(BuildContext context) {
    return fromWidth(MediaQuery.sizeOf(context).width);
  }

  bool get isCompact => this == KwWindowSize.compact;
  bool get isMedium => this == KwWindowSize.medium;
  bool get isExpanded => this == KwWindowSize.expanded;
  bool get isLarge => this == KwWindowSize.large;
  bool get isWide => this == KwWindowSize.expanded || this == KwWindowSize.large;
}
