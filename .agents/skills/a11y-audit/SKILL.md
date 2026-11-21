---
name: a11y-audit
description: Audit Keepwell Flutter web and Android surfaces against WCAG 2.2 AA, Flutter semantics, screen readers, and Lighthouse accessibility gates.
---

# Accessibility Audit (WCAG 2.2 AA — Keepwell)

Use this skill during development and before every milestone walkthrough to verify WCAG 2.2 AA compliance across all surfaces.

## 1. Non-Negotiable WCAG 2.2 AA Gates
- **Contrast:** >= 4.5:1 for normal text, >= 3:1 for large text and UI components across Light, Dark, and High-Contrast themes.
- **Target Size:** >= 48x48 dp touch targets on all interactive controls (never below 24 px).
- **Focus & Keyboard:** Visible focus ring on every focusable widget; full keyboard navigation (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Esc`) including keyboard alternatives for drag-to-reschedule on the technician calendar.
- **No Colour-Only Meaning:** Urgency (`safety`, `urgent`, `standard`, `planned`), gate states, and chart series must pair colour with icon shapes, patterns, or explicit text labels; charts must provide an accessible table alternative.
- **200% Text Scale:** Verify every screen at `textScaler: TextScaler.linear(2.0)` with zero clipping, overlap, or horizontal overflow.
- **Reduce Motion:** Respect `MediaQuery.disableAnimationsOf(context)` everywhere.
- **Captions & Live Regions:** Captions for all spoken content in dialer/video; `Semantics(liveRegion: true)` polite announcements for live transcript turns and `feed` updates.

## 2. Flutter Web Semantics & Multilingual Tags
- Call `SemanticsBinding.instance.ensureSemantics()` at web app startup so screen readers and automated tools (Lighthouse, axe, Chrome DevTools MCP) inspect the semantic tree.
- Tag Devanagari (`hi`) and Telugu (`te`) text spans with their BCP 47 locale so screen readers switch pronunciation engines accurately.

## 3. Automated & Visual Verification Procedure
1. Run widget tests with `tester.getSemantics(...)` and `meetsGuideline(textContrastGuideline)`, `meetsGuideline(androidTapTargetGuideline)`, `meetsGuideline(labeledTapTargetGuideline)`.
2. Run Lighthouse accessibility audit (or Chrome DevTools MCP accessibility tree inspection) on each built web surface (`console`, `field`, `household`, `brand`).
3. Save JSON/HTML reports to `docs/design/lighthouse/`.
4. Fix every serious or critical finding before marking the milestone done.
