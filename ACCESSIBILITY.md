# Accessibility Statement

**ScholarForm AI** is committed to ensuring digital accessibility for people with disabilities. We are continually improving the user experience for everyone and applying the relevant accessibility standards to our frontend interfaces, live editors, and generated outputs.

## Our Commitment

Academic publishing should be accessible to all researchers. Our goal is to ensure that the ScholarForm AI web dashboard (built with Next.js) and the generated output documents comply with the **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA**.

## Current Accessibility Features

- **Semantic HTML:** Our web application relies on robust, semantic HTML to ensure screen readers can navigate the application efficiently.
- **Keyboard Navigation:** The real-time split-pane editor, dashboard, and settings menus are fully operable via keyboard interfaces.
- **Color Contrast:** We utilize design systems that adhere to WCAG AA contrast ratios, including full support for high-contrast dark modes.
- **Accessible Outputs:** Documents generated via HTML, Markdown, and compliant PDF templates include structural tags and semantic hierarchies to assist assistive technologies.

## Known Limitations

We are actively working to resolve the following known limitations:

- **Complex Equation Rendering:** Live previews of complex LaTeX equations may currently lack comprehensive ARIA descriptions for screen readers.
- **PDF Tagging:** While we strive for accessible PDFs, certain niche publisher templates may not yet produce fully tagged, PDF/UA compliant documents.

## Continuous Improvement and VPAT

We are integrating automated accessibility audits (e.g., axe-core) into our CI/CD pipeline to catch regressions early. A formal Voluntary Product Accessibility Template (VPAT) will be provided in a future release to assist institutional procurement.

## Feedback and Reporting Issues

We welcome your feedback on the accessibility of ScholarForm AI. If you encounter accessibility barriers, please:

- Open an issue on our GitHub repository with the label `accessibility`.
- Describe the barrier and the assistive technology you are using.

We try to respond to accessibility feedback within 2 business days. Thank you for helping us make ScholarForm AI inclusive for all researchers.
