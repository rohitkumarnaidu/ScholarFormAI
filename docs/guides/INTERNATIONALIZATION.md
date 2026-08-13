# Internationalization (i18n)

ScholarFormAI is used globally. This guide explains how our localization and internationalization system works for both the platform and generated documents.

## Document Internationalization

When formatting a `.docx` file, you can specify the target language of the document. This ensures that generated text (like "Table of Contents", "References", "Figure") is localized appropriately according to the scholarly template's standards for that language.

### API Usage

Pass the `language` parameter in your API request:

```json
{
  "file": "thesis.docx",
  "template_id": "apa-7",
  "options": {
    "language": "es-ES"
  }
}
```

### Supported Languages
We currently fully support the following locales:
- `en-US` (English, US)
- `en-GB` (English, UK)
- `es-ES` (Spanish)
- `fr-FR` (French)
- `de-DE` (German)

## Platform Localization

If you are contributing to the ScholarFormAI frontend or CLI, all user-facing strings must be extracted into translation files.

### 1. Adding Keys
Add your string to `locales/en.json`:
```json
{
  "CLI_ERROR_NOT_FOUND": "The specified file could not be found."
}
```

### 2. Using Keys
Use the internationalization wrapper in the codebase:
```javascript
import { t } from '@/i18n';

console.error(t('CLI_ERROR_NOT_FOUND'));
```

We utilize a third-party translation platform for translations; please do not manually edit non-English JSON files unless fixing a glaring typo.

## References
- [Developer Guide](DEVELOPER_GUIDE.md)
