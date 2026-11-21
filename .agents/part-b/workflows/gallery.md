---
description: Launch the kw_ui design system gallery app and run component golden and semantics tests.
---

# /gallery — Design System Gallery & Goldens

1. Run analyzer and unit/golden tests for `apps/kw_ui`:
   ```bash
   cd apps/kw_ui && dart analyze && flutter test
   ```
2. Launch the interactive gallery on Chrome:
   ```bash
   cd apps/kw_ui/example && flutter run -d chrome --web-port 5101
   ```
3. Verify every component in the gallery across:
   - Light, Dark, and High-Contrast themes
   - `en`, `hi`, and `te` locales (confirm Devanagari & Telugu glyphs render cleanly)
   - `100%` and `200%` text scale (zero overflow or clipping)
   - Reduce-motion toggle enabled
4. If updating approved visuals, run `flutter test --update-goldens` in `apps/kw_ui` and inspect diffs before committing.
