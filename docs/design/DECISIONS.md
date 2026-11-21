# Keepwell Part B — Design Decisions (`docs/design/DECISIONS.md`)

Key experience decisions and the primary Google guidelines behind them.

| # | Decision | Google Guideline / Source | Where Implemented |
|---|---|---|---|
| 1 | **Brand seed `#0B57D0` with Light, Dark, High-Contrast Light/Dark, and Projector themes** | Material Design 3 Colour Roles & Tonal Palettes (`m3.material.io`) + WCAG 2.2 AA (≥4.5:1 text, ≥7:1 projector) | `apps/kw_ui/lib/src/theme/kw_theme.dart` |
| 2 | **Native `SpringSimulation` motion tokens (spatial fast/default/slow & effects fast/default) with `MediaQuery.disableAnimations` guard** | Material 3 Expressive Motion Physics (`m3.material.io`) + WCAG 2.2 Reduce Motion | `apps/kw_ui/lib/src/theme/kw_motion.dart` |
| 3 | **Urgency never colour-only: tonal container + distinct Material Symbol shape + label + live-region Semantics** | Material 3 Accessibility & WCAG 2.2 SC 1.4.1 (Use of Colour) | `apps/kw_ui/lib/src/components/kw_urgency_chip.dart` |
| 4 | **Explicit abstention banner & source citation chips opening verbatim snippets** | Google People + AI Guidebook (PAIR): Explainability & Trust Calibration | `kw_confidence_meter.dart`, `kw_source_citation_chip.dart` |
| 5 | **6-factor stacked candidate score bar (price never scored) + Reclassify/Reassign with 10s Undo SnackBar** | PAIR Feedback & Control + Gmail Undo Snackbar pattern | `kw_candidate_score_bar.dart`, `apps/console/lib/src/case_detail_pane.dart` |
| 6 | **Keyboard-accessible Reschedule dialog alongside Calendar timeline** | WCAG 2.2 SC 2.5.7 (Dragging Movements) | `apps/console/lib/src/calendar_screen.dart` |
| 7 | **1.15× line-height multiplier for Hindi (`hi`) and Telugu (`te`) + bundled Noto Sans Devanagari/Telugu/Mono** | Google Fonts Indic script legibility + WCAG 2.2 SC 1.4.4 (200% text resize) | `kw_theme.dart`, `kw_strings.dart`, `web/index.html` |
| 8 | **WhatsApp simulator uses Material 3 tonal palette without WhatsApp logo or green trade dress** | Prompt §6.2 & Google Messages conversation layout pattern | `apps/household/lib/src/whatsapp_simulator_screen.dart` |
| 9 | **Unmatched parts styled in amber `"Needs checking"` treatment and excluded from normal quote totals** | Contract §11 (Zero Invented Parts invariant) | `kw_money_line.dart`, `visit_detail_screen.dart`, `quote_approval_screen.dart` |
| 10 | **Payment explicitly separated from OTP closure with persistent boundary banner** | Contract §0 & §5.2 (Closure by OTP only) | `apps/household/lib/src/quote_approval_screen.dart` |
| 11 | **Web semantics enabled at startup (`SemanticsBinding.instance.ensureSemantics()`) + `liveRegion: true` on Stage feed & captions** | Flutter Web Accessibility documentation & WCAG 2.2 SC 4.1.3 | All 4 `lib/main.dart` files + `kw_transcript_bubble.dart` |
| 12 | **Minimum 48dp touch targets across call controls, parts-centre one-handed actions, and video stop controls** | WCAG 2.2 SC 2.5.8 (Target Size) & Material 3 touch guidelines | `kw_waveform_controls.dart`, `parts_requests_screen.dart`, `video_link_screen.dart` |
