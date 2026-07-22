<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Accessibility

## Statement

ScholarForm AI is committed to making its platform accessible to all users, including those with disabilities. We follow accessibility best practices to ensure that persons with disabilities can participate in the project and use the project results.

## Standards Followed

### Web Application

The ScholarForm AI frontend follows the [Web Content Accessibility Guidelines (WCAG) 2.1](https://www.w3.org/TR/WCAG21/) at Level AA:

| Guideline | Status | Implementation |
|-----------|--------|---------------|
| Perceivable (1.1-1.4) | ✅ | Alt text on images, color contrast ratios, text alternatives |
| Operable (2.1-2.5) | ✅ | Full keyboard navigation, focus indicators, skip links |
| Understandable (3.1-3.3) | ✅ | Clear labels, error identification, consistent navigation |
| Robust (4.1) | ✅ | Semantic HTML, ARIA landmarks and roles |

### Key Accessibility Features

- **Skip-to-content link** at the top of every page.
- **Semantic HTML** structure (`<header>`, `<nav>`, `<main>`, `<section>`) throughout the application.
- **ARIA labels** on all interactive elements — navigation items, buttons, icons, form fields.
- **Focus management** — visible focus indicators, logical tab order, focus trapping in modals.
- **Color contrast** — all text meets minimum 4.5:1 contrast ratio against backgrounds.
- **Reduced motion** — animations respect `prefers-reduced-motion: reduce`.
- **Screen reader support** — tested with NVDA (Windows) and VoiceOver (macOS).
- **Error announcements** — `aria-live="polite"` regions for dynamic content updates.
- **Responsive design** — content is accessible across screen sizes, including zoom up to 200%.

## Automated Accessibility Testing

The project includes Lighthouse CI accessibility assertions in CI:

```bash
npm run lhci:accessibility  # Runs Lighthouse with accessibility assertions
```

Minimum accessibility score: **90/100** (enforced in CI).

## Testing

Accessibility testing is performed through:

1. **Automated**: Lighthouse CI accessibility audits on every PR.
2. **Manual**: Periodic manual testing with screen readers (NVDA, VoiceOver).
3. **Keyboard**: Full keyboard navigation verification for all user flows.

## Reporting Issues

If you encounter accessibility barriers, please:

1. Open a GitHub issue with the `accessibility` label.
2. Include the page URL, the issue encountered, and your assistive technology setup.
3. Alternatively, email accessibility@scholarform.ai.

---

*Last updated: July 2026*
