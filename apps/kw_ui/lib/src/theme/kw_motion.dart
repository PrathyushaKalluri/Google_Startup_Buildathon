import 'package:flutter/physics.dart';
import 'package:flutter/widgets.dart';

/// Material 3 Expressive physics-based spring tokens (Design Spec §4).
abstract final class KwMotion {
  /// Expressive Fast Spatial: chip toggles, button morphs.
  static final SpringDescription spatialFast =
      SpringDescription.withDampingRatio(
    mass: 1.0,
    stiffness: 800.0,
    ratio: 0.6,
  );

  /// Expressive Default Spatial: case card reorder, gate stepper, slot landing.
  static final SpringDescription spatialDefault =
      SpringDescription.withDampingRatio(
    mass: 1.0,
    stiffness: 380.0,
    ratio: 0.8,
  );

  /// Expressive Slow Spatial: container transforms, projector stage entrances.
  static final SpringDescription spatialSlow =
      SpringDescription.withDampingRatio(
    mass: 1.0,
    stiffness: 200.0,
    ratio: 0.8,
  );

  /// Effects Fast (critically damped): colour, opacity, focus ring.
  static final SpringDescription effectsFast =
      SpringDescription.withDampingRatio(
    mass: 1.0,
    stiffness: 1600.0,
    ratio: 1.0,
  );

  /// Effects Default (critically damped): surface cross-fades.
  static final SpringDescription effectsDefault =
      SpringDescription.withDampingRatio(
    mass: 1.0,
    stiffness: 800.0,
    ratio: 1.0,
  );

  /// Reduce-motion fallback duration (120 ms linear fade, zero spatial shift).
  static const Duration reducedMotionFade = Duration(milliseconds: 120);

  /// Standard fallback duration when animating non-spring properties.
  static const Duration fastDuration = Duration(milliseconds: 180);
  static const Duration defaultDuration = Duration(milliseconds: 300);

  /// Returns `true` when the platform or user requests reduced motion.
  static bool shouldReduceMotion(BuildContext context) {
    return MediaQuery.disableAnimationsOf(context);
  }

  /// Returns [Duration.zero] when reduced motion is active.
  static Duration durationFor(BuildContext context, Duration normal) {
    return shouldReduceMotion(context) ? Duration.zero : normal;
  }

  /// Returns [Curves.linear] when reduced motion is active, otherwise [normal].
  static Curve curveFor(
    BuildContext context, [
    Curve normal = Curves.easeOutCubic,
  ]) {
    return shouldReduceMotion(context) ? Curves.linear : normal;
  }
}

/// Animates a scalar [value] using an M3 Expressive [SpringSimulation],
/// automatically snapping when [KwMotion.shouldReduceMotion] is enabled.
class KwSpringValueBuilder extends StatefulWidget {
  const KwSpringValueBuilder({
    super.key,
    required this.value,
    required this.builder,
    this.spring,
    this.child,
  });

  final double value;
  final SpringDescription? spring;
  final Widget Function(BuildContext context, double value, Widget? child)
      builder;
  final Widget? child;

  @override
  State<KwSpringValueBuilder> createState() => _KwSpringValueBuilderState();
}

class _KwSpringValueBuilderState extends State<KwSpringValueBuilder>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController.unbounded(
      vsync: this,
      value: widget.value,
    );
  }

  @override
  void didUpdateWidget(covariant KwSpringValueBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) {
      if (KwMotion.shouldReduceMotion(context)) {
        _controller.value = widget.value;
      } else {
        final sim = SpringSimulation(
          widget.spring ?? KwMotion.spatialDefault,
          _controller.value,
          widget.value,
          _controller.velocity,
        );
        _controller.animateWith(sim);
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      child: widget.child,
      builder: (context, child) =>
          widget.builder(context, _controller.value, child),
    );
  }
}
