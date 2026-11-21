# 200% text-scale and keyboard evidence — findings (honest)

Method: the existing hero-journey tests were cloned with
`tester.platformDispatcher.textScaleFactorTestValue = 2.0` (Stage view + reclassify/reassign,
household call/video/home/quote/OTP, field technician + parts) and run at the same viewport sizes.
These clones FAILED and were therefore **not committed** (they would break the green suite).

Overflow locations found at 200% text scale (to fix next):

| Journey | File:line | Symptom |
|---|---|---|
| Stage view / case detail | `kw_ui/lib/src/components/kw_candidate_score_bar.dart:125` | Row overflows 157-212 px |
| Reassign dialog | `console/lib/src/case_detail_pane.dart:275` | button Row overflows |
| Quote -> Google Pay sheet | `household/lib/src/quote_approval_screen.dart:679` | Row overflows 366 px |
| Home memory header | `household/lib/src/home_memory_screen.dart:197` | Row overflows 93 px |
| Video page | `household/lib/src/video_link_screen.dart:516, :582` | chips Row overflow 101-291 px |
| WhatsApp simulator | `household/lib/src/whatsapp_simulator_screen.dart:490` | Row overflow |
| Stage view column | `console/lib/src/stage_view_screen.dart` | 641 px vertical overflow in test viewport |
| Field close-out | `field/test` clone | finders for "Today's Jobs" / parts line not found at 2.0 (layout/scroll) |

Status: 200% text scale NOT verified clean for the three hero journeys. `kw_ui` component tests
at 200% (en/hi/te) still pass (`apps/kw_ui/test/kw_ui_test.dart`).
Keyboard path: Tab/Enter is covered only by Flutter default focus traversal on standard Material
buttons; no dedicated end-to-end keyboard-only test exists. NOT DONE.
