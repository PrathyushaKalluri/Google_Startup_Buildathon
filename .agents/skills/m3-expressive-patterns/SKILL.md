---
name: m3-expressive-patterns
description: Apply Material 3 Expressive colour, shape, typography, spring physics, and PAIR explainability patterns across Keepwell Flutter apps.
---

# Material 3 Expressive Patterns (Keepwell)

Use this skill when designing or styling any screen or widget in `apps/kw_ui`, `apps/console`, `apps/field`, `apps/household`, or `apps/brand`.

## 1. Colour & Semantic Roles
- Generate tonal palettes via Material Theme Builder + `dynamic_color` (light, dark, high-contrast).
- Never hardcode hex values inside feature widgets; read from `Theme.of(context).colorScheme` and `KwThemeExtension`.
- **Urgency palette (`safety`, `urgent`, `standard`, `planned`):** always pair colour with a distinct Material Symbol shape and text label (never colour-only, WCAG 2.2 AA).
- **Safety path (`safety`):** highest visual contrast, distinct shape badge, top-of-board placement, and polite/assertive alert cue.

## 2. Expressive Shapes & Motion Physics
- Use the M3 Expressive corner scale and shape morphing (e.g., morphing pill/squircle on OTP close or gate resolution).
- Distinguish **spatial springs** (position/size changes: case rising up board, technician chip landing on slot) from **effects springs** (opacity/colour transitions, no overshoot).
- Always check `MediaQuery.disableAnimationsOf(context)` (Reduce Motion) and fall back to instant/cross-fade transitions when enabled.

## 3. Typography & Scripts
- Use embedded Google Fonts (`Google Sans Flex` / `Roboto Flex` for UI, `Noto Sans Devanagari` for Hindi, `Noto Sans Telugu` for Telugu, `Noto Sans Mono` for IDs, part numbers, error codes).
- Ensure generous line-height (`height >= 1.4`) for Devanagari and Telugu matras so ascenders/descenders never clip.

## 4. People + AI Guidebook (PAIR) Patterns
- **Explainability:** Every agent decision (urgency, diagnosis hypothesis, candidate score) is one tap from its reason, evidence, and manual citations.
- **Uncertainty:** Display probability bars and abstention states honestly; never smooth uncertainty into false confidence.
- **Control & Override:** Reclassify urgency and reassign technician actions require a short reason, show a 10-second Undo snackbar, and frame overrides as training signal ("what the agent learned from you").
- **Zero Invented Parts:** Render any unmatched part as `"needs checking"`, never as a normal quote line.
