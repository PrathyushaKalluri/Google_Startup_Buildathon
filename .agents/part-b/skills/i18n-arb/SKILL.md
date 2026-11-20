---
name: i18n-arb
description: Author and maintain English, Hindi, and Telugu ARB localization files, en-IN formatting, and embedded multilingual fonts for Keepwell Flutter apps.
---

# Internationalisation & ARB Workflow (Keepwell)

Use this skill whenever adding UI strings, formatting numbers/currency/dates, or verifying `en`, `hi`, and `te` translations.

## 1. ARB Structure & Codegen
- Maintain `app_en.arb` (template), `app_hi.arb` (Hindi), and `app_te.arb` (Telugu) using `flutter_localizations` and `intl`.
- Every key in `app_en.arb` MUST have a matching entry in `app_hi.arb` and `app_te.arb` plus a `@key` metadata description.
- Mark draft translations for human review in metadata (`"@key": { "description": "... [DRAFT_REVIEW]" }`).
- Run `flutter gen-l10n` after editing any `.arb` file and commit the generated localization outputs if tracked.

## 2. Verbatim Agent Copy vs. UI Chrome
- **UI chrome (Part B owns):** buttons, navigation labels, filters, empty/error states, table headers, KPI labels (matching Contract Section 11 metric names exactly).
- **Agent-emitted household copy (Part A owns):** recording notice, Gate 1 ("Are you okay to try a quick, safe fix yourself first?"), Gate 2 ("Would you like to switch to video, or carry on here?"), safety stop ("Please stop using it and switch it off at the wall..."). **Display verbatim; never rewrite or re-translate in Flutter.**
- **Forbidden words:** Never include `"staff"`, `"dispatcher"`, `"human approval"`, or `"AI-powered"` marketing copy in any ARB file.

## 3. Indian Formatting (`en-IN`) & Fonts
- **Money:** All wire values are integer paise (`*_paise`). Format with `NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 2)` (lakh/crore grouping, e.g., `₹1,25,000.00` or `₹850.00`).
- **Dates & Times:** Wire timestamps are UTC ISO 8601; convert to IST (`+05:30`) for display using `en_IN` date/time patterns.
- **Embedded Fonts:** Bundle `Google Sans Flex` / `Roboto Flex`, `Noto Sans Devanagari`, `Noto Sans Telugu`, and `Noto Sans Mono` as local assets; never rely on system fonts.
- **Runtime Switching:** Allow instant language switching (`en` / `hi` / `te`) from the app bar / demo drawer without losing navigation state.
