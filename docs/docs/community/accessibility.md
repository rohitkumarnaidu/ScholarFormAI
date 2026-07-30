<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Accessibility Statement & Conformance Report

ScholarForm AI is committed to ensuring digital accessibility for people with disabilities. We continuously improve the user experience for everyone and apply the relevant accessibility standards.

---

## Standards Compliance

The ScholarForm AI web application strives to conform to **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA** standards.

### Compliance Scorecard

| Area | Standards / Guidelines | Status | Verification Method |
|---|---|---|---|
| **Semantic HTML** | WAI-ARIA 1.2 / HTML5 | ✅ Compliant | Axe DevTools, Lighthouse CI |
| **Keyboard Navigation** | WCAG 2.1 SC 2.1.1 | ✅ Compliant | Manual Keyboard Audit |
| **Color Contrast** | WCAG 2.1 SC 1.4.3 (4.5:1 ratio) | ✅ Compliant | Contrast Checker |
| **Screen Reader Support** | NVDA / VoiceOver compatibility | ✅ Compliant | Manual VoiceOver Testing |
| **Focus Indicators** | Visible focus rings (`focus-visible`) | ✅ Compliant | Visual Inspection |

---

## Accessibility Features

- **Keyboard Navigation**: Full application navigation using `Tab`, `Shift+Tab`, `Enter`, and `Space`. Focus traps are implemented in modal dialogs.
- **Skip Links**: Accessible "Skip to main content" link for keyboard users.
- **Screen Reader Announcements**: `aria-live` regions communicate dynamic async operations (file upload progress, formatting completion, AI status messages).
- **Dark/Light Mode Contrast**: Both themes are tuned to satisfy minimum contrast ratios across all text elements.
- **Responsive Layout**: Supports zooming up to 200% without loss of content or horizontal scrolling.

---

## Automated Verification

Accessibility regressions are automatically guarded against using Lighthouse CI in our E2E testing pipeline:

```bash
cd frontend
npm run test:accessibility
```

---

## Feedback & Contact

If you experience accessibility barriers while using ScholarForm AI, please report them to **accessibility@scholarform.ai**.
