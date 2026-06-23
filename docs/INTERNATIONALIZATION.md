<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Internationalization (i18n)

## Overview

ScholarForm AI is designed with internationalization (i18n) in mind to enable easy localization for the target audience's culture, region, or language. This document describes the current i18n implementation and future plans.

## Current State

### Language Support

- **Primary language**: English (en)
- **Right-to-left support**: Architecture supports RTL layout switching for future localization.

### Codebase Internationalization

The codebase follows i18n best practices:

| Area | Practice |
|------|----------|
| User-facing strings | All user-facing strings are externalized to locale files (not hardcoded). |
| Date/time formatting | Uses `Intl.DateTimeFormat` for locale-aware date/time formatting. |
| Number formatting | Uses `Intl.NumberFormat` for locale-aware number, currency, and percentage formatting. |
| Sorting | String comparison uses `Intl.Collator` for locale-aware sorting. |
| Pluralization | Pluralization rules are handled through the i18n library. |
| Character encoding | UTF-8 throughout the entire stack. |

### Text Direction

The frontend supports `dir` attribute switching for RTL languages. The layout system is designed with logical CSS properties (`margin-inline-start`, `padding-inline-end`) rather than physical directions (`margin-left`, `padding-right`).

## Internationalization Files

Locale files are stored in `frontend/src/locales/`:

```
frontend/src/locales/
  en.json       # English (default)
  es.json       # Spanish (planned)
  fr.json       # French (planned)
  de.json       # German (planned)
  zh.json       # Chinese (planned)
  ja.json       # Japanese (planned)
```

## Technical Implementation

### Frontend (Next.js/React)

- **Library**: Uses `next-intl` for internationalized routing and translations.
- **Locale detection**: Automatic detection via `Accept-Language` header with manual override.
- **Translation keys**: Namespaced by component/feature for maintainability.

### Backend (FastAPI/Python)

- **Error messages**: All API error messages are in English with structured error codes for client-side localization.
- **Content negotiation**: API responses include `Content-Language` header.

## Future Plans

1. Complete translation coverage for es, fr, de, zh, ja locales.
2. Implement locale-specific formatting for document output (date formats, number formats).
3. Add RTL layout support for Arabic, Hebrew, and other RTL languages.
4. Internationalize PDF and DOCX output templates for locale-specific formatting.

---

*Last updated: June 2026*
