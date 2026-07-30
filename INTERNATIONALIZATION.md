# Internationalization

## Current Status

AMF currently supports English as the primary language for:
- API responses and error messages
- CLI output
- Web UI text
- Documentation

## Architecture

### Backend

- All user-facing strings are in English
- Error messages use consistent English templates
- Style names follow their original language conventions (APA, MLA, etc.)

### Frontend

- Built with i18n-ready architecture using Next.js
- Text strings are centralized in components

## Planned i18n Support

### Phase 1 (Q4 2026)
- CLI output translations
- API error message translations
- Documentation translations

### Phase 2 (Q1 2027)
- Web UI translations via next-intl
- Locale detection (Accept-Language header)
- RTL support for Arabic, Hebrew, etc.

## Contributing Translations

Translation files will be stored in:

```
frontend/messages/{locale}.json
docs/docs/{locale}/
```

To contribute:
1. Create a translation file for your language
2. Submit a PR with the translation
3. Translation quality will be verified by native speakers

## Locale Support Roadmap

| Language | CLI | API | Web UI | Docs |
|----------|:---:|:---:|:------:|:----:|
| English | ✅ | ✅ | ✅ | ✅ |
| Spanish | 🔄 | 🔄 | 📋 | 📋 |
| French | 🔄 | 🔄 | 📋 | 📋 |
| German | 📋 | 📋 | 📋 | 📋 |
| Chinese | 📋 | 📋 | 📋 | 📋 |
| Japanese | 📋 | 📋 | 📋 | 📋 |
| Arabic | 📋 | 📋 | 📋 | 📋 |

✅ = Available, 🔄 = In Progress, 📋 = Planned
