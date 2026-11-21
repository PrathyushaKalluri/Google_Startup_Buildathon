---
name: golden-test
description: Write, run, and update deterministic Flutter golden tests across themes, locales, viewports, and 200% text scale for Keepwell components and screens.
---

# Golden Testing (Keepwell)

Use this skill when adding or updating visual regression golden tests in `apps/kw_ui` and the four Keepwell apps.

## 1. Determinism Setup
- Disable runtime HTTP font fetching in `flutter_test_config.dart` (`GoogleFonts.config.allowRuntimeFetching = false`) and load bundled font assets (`RobotoFlex`/`GoogleSansFlex`, `NotoSansDevanagari`, `NotoSansTelugu`, `NotoSansMono`) via `FontLoader` before pumping widgets.
- Pin `DateTime` / clock values and disable infinite animations (or pump a fixed timestamp) so snapshots never flake.
- Always wrap test pumps in a fixed `SurfaceSize` (`tester.view.physicalSize` + `devicePixelRatio = 1.0`, reset via `addTearDown`).

## 2. Required Matrix for `kw_ui` Components
Every component in `apps/kw_ui` should cover:
- **Themes:** Light, Dark, High-Contrast.
- **Locales:** `en`, `hi` (Devanagari), `te` (Telugu).
- **Text Scale:** `1.0x` and `2.0x` (`MediaQuery` with `TextScaler.linear(2.0)`).
- **Key States:** e.g., urgency (`safety`, `urgent`, `standard`, `planned`), unmatched part (`"needs checking"`), gate states (`yes`, `no`, `silence`, `not_asked`).

For app screens (`console`, `field`, `household`, `brand`), test at Compact (`390x844`), Medium (`834x1194`), and Expanded (`1440x900`) viewports.

## 3. Running & Updating Goldens
- **Verify:**
  ```bash
  flutter test test/goldens/
  ```
- **Update intentionally after approved design changes:**
  ```bash
  flutter test --update-goldens test/goldens/
  ```
- Inspect generated PNG diffs visually before committing; never blindly overwrite failing goldens without confirming the visual change matches `docs/design/DESIGN_SPEC.md`.
