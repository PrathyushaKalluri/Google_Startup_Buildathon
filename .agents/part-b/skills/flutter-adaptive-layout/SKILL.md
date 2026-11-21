---
name: flutter-adaptive-layout
description: Build responsive Material 3 adaptive layouts across compact, medium, expanded, large, and extra-large window size classes in Keepwell Flutter apps.
---

# Flutter Adaptive Layout (Keepwell)

Use this skill when creating or refactoring top-level pages, navigation shells, or multi-pane layouts in any Keepwell app.

## 1. M3 Window Size Classes
Evaluate `MediaQuery.sizeOf(context).width` via a shared `KwWindowSizeClass` helper in `kw_ui`:
- **Compact** (`< 600 dp`): Phone portrait — single column, bottom `NavigationBar`, modal sheets for detail/filters.
- **Medium** (`600–839 dp`): Tablet portrait / foldable — `NavigationRail`, single or split pane with collapsible side sheet.
- **Expanded** (`840–1199 dp`): Tablet landscape / small desktop — `NavigationRail` + canonical **list-detail** or **supporting pane** layout.
- **Large** (`1200–1599 dp`) & **Extra-Large** (`>= 1600 dp`): Desktop / projector — extended `NavigationRail` (or hidden chrome in Live Stage projector mode), multi-pane list-detail + activity strip.

## 2. Canonical Layouts per Surface
- **`apps/console` (Case Board):** List-detail (case queue on left, full Case Detail on right) + collapsible live `feed` activity strip.
- **`apps/console` (Live Stage `/stage`):** Supporting-pane hero layout (live transcript + "what the agent knows" + gate stepper + diagnosis/scoring + day timeline). Includes **Projector Mode** (hides chrome, bumps typography scale, maximizes contrast).
- **`apps/field` (Technician & Parts):** Mobile-first single-column with large >= 48 dp one-handed touch targets; adapts to two-column brief + actions on tablets.
- **`apps/household`:** Mobile-first centered container (`maxWidth: 480 dp` on desktop) for WhatsApp simulator, Meet-style dialer, `/v/<token>` video page, Home Memory, and Quote/OTP flow.
- **`apps/brand`:** Desktop-first data table + analytics grid that gracefully stacks to cards on compact widths.

## 3. Interaction & Performance Rules
- **Keyboard-accessible drag alternatives:** Every drag-to-reschedule interaction (e.g., technician calendar) must provide a keyboard/button "Move to slot..." dialog alternative (WCAG 2.2 AA).
- **200% text scale:** Never use fixed pixel heights on rows/cards containing text; use `Wrap`, `Flexible`, and scrollable containers so text scales to 200% without overflow.
- **Deferred loading:** Lazy-load heavy map widgets and Looker Studio embeds so first interactive stays under 3s on broadband.
