# Keepwell Design Specification (`docs/design/DESIGN_SPEC.md`)

Grounded in **Material Design 3 & Material 3 Expressive** (`m3.material.io`), **Google People + AI Guidebook (PAIR)**, **WCAG 2.2 AA**, and **Flutter Adaptive Design**.

---

## 1. Design Principles

1. **One obvious next thing:** Every screen highlights a single primary action; secondary actions stay quiet. Works equally for a centre admin in a rush, a technician on a stair landing, and a homeowner on a video call.
2. **Show the agent's work, calmly (PAIR Explainability):** Every agent decision is one tap from its reason, rule codes, evidence, and manual citation. Uncertainty is displayed honestly (confidence meter + abstention state). Centre overrides (reclassify/reassign) are framed as valuable training signals, never errors.
3. **Urgency is felt, never colour-only:** `safety`, `urgent`, `standard`, and `planned` combine distinct tonal colour roles, unique icon shapes, elevated borders/badges, and spring motion.
4. **Time and place are first-class:** Technician schedules, slots, and routes render visually on timelines and maps (with accessible table/keyboard alternatives).
5. **Language is a feature:** Instant runtime switching across English (`en`), Hindi (`hi`), and Telugu (`te`) with bundled Noto scripts, zero truncation at 200% text scale, and `en-IN` lakh currency formatting (`₹1,25,400`).
6. **Motion explains (M3 Expressive Springs):** Spatial springs animate world-state changes (case reordering, gate resolution, technician slot assignment); effects springs animate opacity/colour. Strictly honours `MediaQuery.disableAnimations` (reduce motion).
7. **Delight is quiet:** Subtle shape morph on resolution, calm OTP closure confirmation, haptics on field check-ins, purposeful empty states.
8. **Trust in the first five seconds:** Every household surface displays the service centre's name and identity, what is happening right now, and what happens next (never "AI-powered" marketing hype).

---

## 2. Colour Tokens (Material Theme Builder + Dynamic Colour)

- **Brand Seed:** `#0B57D0` (Calm Google-grade Cobalt Blue — trustworthy, high legibility in bright outdoor light and dark projector rooms).
- **Themes:** Light, Dark, High-Contrast Light, High-Contrast Dark, plus **Projector Mode** (Stage view: boosted contrast ≥ 7:1, 1.35× base scale, hidden navigation chrome).
- **Semantic Urgency Palette (always paired with icon + label):**

| Urgency Class | Light Container / On-Container | Dark Container / On-Container | Icon Shape (Material Symbols) |
| :--- | :--- | :--- | :--- |
| `safety` | `#FFDAD6` / `#410002` (Accent `#BA1A1A`) | `#93000A` / `#FFDAD6` | Filled Octagon (`report` / `warning`) |
| `urgent` | `#FFE0B2` / `#4E2600` (Accent `#C25900`) | `#6E3800` / `#FFE0B2` | Rounded Triangle (`priority_high`) |
| `standard` | `#D3E3FD` / `#041E49` (Accent `#0B57D0`) | `#0842A0` / `#D3E3FD` | Pill / Circle (`schedule`) |
| `planned` | `#C4EED0` / `#072711` (Accent `#146C2E`) | `#0F5223` / `#C4EED0` | Rounded Square (`event_available`) |

- **Semantic Event & Status Roles:**
  - `verified / fixed / paid`: Emerald tonal (`#146C2E` / `#C4EED0`)
  - `needs_checking / provisional / review_due`: Amber tonal (`#8D4E00` / `#FFDCBE`)
  - `declined / failed / safety_stop`: Error tonal (`#BA1A1A` / `#FFDAD6`)
  - `video_active / live_call`: Tertiary Indigo/Teal tonal (`#006A6A` / `#9CF1F0`)

---

## 3. Typography & Scripts

- **UI Sans:** `Roboto Flex` (fallback `Google Sans Flex` where licensed) for Latin numerals and UI chrome.
- **Devanagari (Hindi):** `Noto Sans Devanagari` (bundled via Google Fonts / assets).
- **Telugu:** `Noto Sans Telugu` (bundled via Google Fonts / assets).
- **Monospace (IDs, Serials, Error Codes, Part Numbers, OTP):** `Noto Sans Mono` (`tabularFigures` enabled).
- **Line Height Guard:** Increase line-height multiplier by `1.15×` for `hi` and `te` locales to prevent matra/vowel-sign clipping.

---

## 4. Shape & Motion Spec (M3 Expressive)

### Shape Scale
- `extraSmall`: `4 dp` (tooltips, badges)
- `small`: `8 dp` (chips, code tags)
- `medium`: `16 dp` (case cards, input fields)
- `large`: `24 dp` (sheets, consent gate cards, stage panels)
- `extraLarge`: `32 dp` (projector hero cards, call controls)
- `full`: `999 dp` (pills, avatars, primary CTA morph)

### Physics-Based Springs (`SpringDescription` / `SpringSimulation`)
- **Expressive Fast Spatial:** `stiffness: 800`, `dampingRatio: 0.6` (chip toggles, button morphs)
- **Expressive Default Spatial:** `stiffness: 380`, `dampingRatio: 0.8` (case card reorder on board, gate stepper transitions, technician chip landing on slot)
- **Expressive Slow Spatial:** `stiffness: 200`, `dampingRatio: 0.8` (container transforms, projector stage panel entrances)
- **Effects Fast / Default:** `stiffness: 1600 / 800`, `dampingRatio: 1.0` (critically damped — colour, opacity, focus ring)
- **Reduce Motion Fallback:** When `MediaQuery.disableAnimations` is true, snap or use 120ms linear fade with zero spatial translation.

---

## 5. Adaptive Window Size Classes

| Class | Width | Console Layout | Household / Field Layout |
| :--- | :--- | :--- | :--- |
| **Compact** | `< 600 dp` | Single-column + Navigation Bar | Full-bleed mobile-first + Bottom Bar |
| **Medium** | `600–839 dp` | Navigation Rail + Single-pane / Modal detail | Centered 560 dp card column |
| **Expanded** | `840–1199 dp` | Navigation Rail + List-Detail (40/60) | Two-pane brief + actions |
| **Large / XL** | `≥ 1200 dp` | Expanded Rail + List-Detail + Activity Supporting Pane (Stage View 3-column) | Max-width 1280 dp grid |

---

## 6. Component Inventory (`apps/kw_ui`)

1. `KwUrgencyChip` — icon + tonal container + accessible label + live-region priority
2. `KwCaseCard` — ticket summary, appliance badge, urgency chip, trigger tag, needed-by, unread dot, swipe/keyboard actions
3. `KwStatusStepper` — 6-phase horizontal/vertical progress indicator
4. `KwConsentGateCard` — two-step visual (Gate 1 safe-fix, Gate 2 video/here, silence/skipped-for-safety states)
5. `KwConfidenceMeter` — PAIR-compliant probability bar + explicit abstention/uncertainty banner
6. `KwSourceCitationChip` — document title, page badge, tap-to-open snippet sheet
7. `KwCandidateScoreBar` — 6-factor stacked bar (`fix_confidence` 30, `parts_readiness` 25, `time_to_visit` 20, `route_cost` 15, `reliability` 5, `household_fit` 5) with tooltip + accessible table breakdown
8. `KwTranscriptBubble` — speaker avatar, language chip (`en`/`hi`/`te`), modality badge, final/interim state
9. `KwWaveformControls` — Google Meet-style call bar (mute, speaker, video switch, end) + live audio meter
10. `KwEventRow` — distinct icon/treatment for all 34 Contract C8 event types + safe generic fallback
11. `KwSlotPicker` — 1 recommended + up to 2 alternative windows with price range (`en-IN`)
12. `KwRouteEtaBar` — drive-time & distance pill with static fallback when Maps key absent
13. `KwMoneyLine` — paise-to-rupee formatter (`₹1,250.00`), payer chip (`Brand`, `Plan`, `Household`), `"Needs checking"` treatment for unmatched parts
14. `KwOtpInput` — 6-digit accessible OTP entry with autofill & screen-reader announcements
15. `KwFvrGauge` — radial FVR-14 gauge with accessible numeric/table fallback
16. `KwEmptyState`, `KwErrorState`, `KwSkeletonLoader` — calm, actionable states with retry

---

## 7. WCAG 2.2 AA Accessibility Checklist

- [ ] Contrast ≥ 4.5:1 normal text, ≥ 3:1 large text & UI components in all 4 themes
- [ ] Touch targets ≥ 48 × 48 dp (never < 24 × 24 px)
- [ ] Visible focus ring (`3 dp` high-contrast outline) on every interactive control
- [ ] Full keyboard navigation including non-drag rescheduling on Calendar
- [ ] `SemanticsBinding.instance.ensureSemantics()` called on web startup
- [ ] `Semantics(liveRegion: true)` on Live Stage feed and call transcript
- [ ] Language-tagged `AttributedString` / locale wrappers for Hindi & Telugu spans
- [ ] 200% text scale tested in `kw_ui/example` gallery with zero overflow
- [ ] Captions for all spoken audio; plain-language mic/camera permission prompts
