<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Accessibility Statement

**ScholarForm AI** is committed to ensuring digital accessibility for people with disabilities. We continually improve the user experience for everyone and apply relevant accessibility standards across our frontend web dashboard, real-time split-pane editor, and generated output documents.

---

## 1. Standards Followed

The ScholarForm AI frontend adheres to the **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA**:

| Guideline | Status | Implementation |
| :--- | :---: | :--- |
| **Perceivable (1.1-1.4)** | ✅ | Alt text on images, WCAG AA contrast ratios, text alternatives for non-text items. |
| **Operable (2.1-2.5)** | ✅ | Full keyboard navigation, logical focus indicators, skip-to-content links, modal focus trapping. |
| **Understandable (3.1-3.3)** | ✅ | Clear field labels, error identification, input validation announcements, consistent navigation. |
| **Robust (4.1)** | ✅ | Semantic HTML5 structure, ARIA landmarks, and live regions. |

---

## 2. Key Accessibility Features

- **Skip-to-Content Link:** Integrated at the top of every page for fast keyboard traversal.
- **Semantic HTML:** Strict structure (`<header>`, `<nav>`, `<main>`, `<section>`) throughout the Next.js App Router.
- **ARIA Labels:** Explicit labels across interactive controls, navigation tabs, buttons, icons, and form inputs.
- **Focus Management:** Visible high-contrast focus rings, logical tab order, and active focus trapping in dialogs.
- **Color Contrast:** All typography meets or exceeds the minimum 4.5:1 contrast ratio against backgrounds in both light and dark modes.
- **Reduced Motion:** Fluid transitions and animations strictly respect the user's `prefers-reduced-motion: reduce` OS setting.
- **Screen Reader Support:** Validated with NVDA (Windows) and VoiceOver (macOS).
- **Dynamic Announcements:** `aria-live="polite"` regions for streaming generation tokens, status progress, and toast updates.
- **Accessible Outputs:** Generated DOCX and HTML documents maintain structural heading tags and semantic hierarchies to assist assistive technology consumption.

---

## 3. Automated Accessibility Testing

The project incorporates automated Lighthouse CI accessibility checks enforced during pull request builds:

```bash
npm run lhci:accessibility  # Runs Lighthouse with accessibility assertions
```

Minimum accessibility score: **90/100** (enforced in CI).

---

## 4. Known Limitations & Roadmap

We are actively working to resolve the following known limitations:
- **Complex Equation Rendering:** Live previews of complex LaTeX equations may currently lack full descriptive ARIA speech tags for some screen readers.
- **PDF Tagging:** While HTML and DOCX outputs maintain semantic structure, certain legacy publisher styles may require specialized post-processing for PDF/UA compliance.

---

## 5. Feedback and Reporting Issues

We welcome feedback on the accessibility of ScholarForm AI. If you encounter an accessibility barrier:

1. Open an issue on our GitHub repository with the `accessibility` label.
2. Describe the barrier, the page URL, and the assistive technology you are using.
3. Alternatively, email <accessibility@scholarform.ai>.

We strive to respond to accessibility inquiries within 2 business days. Thank you for helping us keep ScholarForm AI inclusive for all researchers.
