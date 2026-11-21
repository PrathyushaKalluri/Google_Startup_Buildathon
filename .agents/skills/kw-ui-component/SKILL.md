---
name: kw-ui-component
description: Author, document, showcase, and golden-test a reusable design-system component in apps/kw_ui following Keepwell standards.
---

# Authoring a `kw_ui` Component

Use this skill whenever adding or modifying a component in `apps/kw_ui/`.

## 1. Strict Conventions
- **Tokens only:** Read colours, typography, spacing, corner radii, and motion springs from `kw_ui` theme tokens. Never hardcode `Color(0x...)` or magic durations.
- **No hardcoded UI strings:** Accept localized labels via parameters (caller supplies ARB strings). Never rewrite agent-emitted copy; display verbatim.
- **Forbidden words:** Never use `"staff"`, `"dispatcher"`, or `"human approval"` in copy, semantics labels, or comments.
- **Domain invariants:**
  - Urgency widgets always pair colour + icon shape + text.
  - Parts rows highlight unmatched / `compatibility_unverified` items with a distinct `"needs checking"` badge and exclude them from normal quote totals.
  - Candidate score bars display the exact 6 weighted factors (`fix_confidence`, `parts_readiness`, `time_to_visit`, `route_cost`, `reliability`, `household_fit`) — never price.

## 2. Accessibility Checklist (Required Before Merge)
- Wrap custom painted or composite widgets in `Semantics` with clear `label`, `value`, `button`/`header`/`liveRegion` flags.
- Enforce minimum `48x48 dp` touch targets for all interactive controls.
- Ensure visible keyboard focus indicators (`FocusTraversalOrder` / `FocusableActionDetector`).
- Respect `MediaQuery.disableAnimationsOf(context)` for all spring/morph animations.

## 3. Gallery & Golden Verification
1. Export the widget from `apps/kw_ui/lib/kw_ui.dart`.
2. Add an interactive showcase entry in `apps/kw_ui/example/` demonstrating all states (default, loading/skeleton, empty, error, disabled).
3. Verify in the gallery across:
   - Light, Dark, and High-Contrast themes
   - `en`, `hi`, and `te` locales
   - `1.0x` and `2.0x` text scale
4. Add a widget test with `Semantics` assertions and a golden test (see `golden-test` skill).
5. Run `dart analyze` and `flutter test` inside `apps/kw_ui/` with zero warnings.
