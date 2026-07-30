<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Internationalization & Localization (i18n)

ScholarForm AI supports internationalization across both the web application interface and manuscript formatting engines.

---

## Architecture Overview

- **Frontend i18n Engine**: `next-intl` integrated with Next.js 16 App Router for dynamic locale routing and translation dictionary loading.
- **Backend Formatting Locales**: Supports locale-aware date, author name, and bibliographic citation formatting across standard CSL styles.

---

## Supported Languages

| Locale Code | Language | Interface Coverage | Formatting Engine |
|---|---|---|---|
| `en` | English (Default) | 100% | ✅ Full Support |
| `es` | Spanish | 100% | ✅ Full Support |
| `fr` | French | 100% | ✅ Full Support |
| `de` | German | 100% | ✅ Full Support |
| `zh` | Chinese (Simplified) | 100% | ✅ Full Support |
| `ja` | Japanese | 100% | ✅ Full Support |

---

## Adding Translations

Translation files reside in `frontend/src/locales/<locale>.json`.

To add a new translation string:
1. Update `frontend/src/locales/en.json` with the new key.
2. Add corresponding translations to target language dictionaries.
3. Use the `useTranslations` hook in Next.js components:

```tsx
import { useTranslations } from 'next-intl';

export function Header() {
  const t = useTranslations('Header');
  return <h1>{t('title')}</h1>;
}
```
