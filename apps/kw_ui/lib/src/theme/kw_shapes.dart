import 'package:flutter/widgets.dart';

/// Material 3 Expressive corner radius scale (Design Spec §4).
abstract final class KwShapes {
  static const double extraSmall = 4;
  static const double small = 8;
  static const double medium = 16;
  static const double large = 24;
  static const double extraLarge = 32;
  static const double full = 999;

  static const BorderRadius radiusExtraSmall =
      BorderRadius.all(Radius.circular(extraSmall));
  static const BorderRadius radiusSmall =
      BorderRadius.all(Radius.circular(small));
  static const BorderRadius radiusMedium =
      BorderRadius.all(Radius.circular(medium));
  static const BorderRadius radiusLarge =
      BorderRadius.all(Radius.circular(large));
  static const BorderRadius radiusExtraLarge =
      BorderRadius.all(Radius.circular(extraLarge));
  static const BorderRadius radiusFull =
      BorderRadius.all(Radius.circular(full));

  static RoundedRectangleBorder rounded(double radius, {BorderSide side = BorderSide.none}) {
    return RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(radius),
      side: side,
    );
  }
}
