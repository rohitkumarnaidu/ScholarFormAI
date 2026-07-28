# Simple Manuscript Formatting Example

This example demonstrates how to format a single academic manuscript file into a publication-ready `.docx` document using ScholarForm AI (AMF).

## Overview

Whether writing in Markdown or LaTeX, ScholarForm AI automatically parses headings, abstracts, tables, figures, footnotes, and bibliographic citations, applying strict academic formatting guidelines (e.g., APA 7th Edition, IEEE, MLA 9th Edition).

---

## 1. Input Manuscript (`manuscript.md`)

Create a Markdown file containing your manuscript content:

```markdown
---
title: "Impact of Automated Formatting on Academic Publishing Efficiency"
author:
  - name: "Dr. Jane Doe"
    affiliation: "Department of Computer Science, University of Science"
  - name: "John Smith"
    affiliation: "Institute of Information Systems"
abstract: |
  Academic document preparation consumes significant researcher time.
  This study evaluates the automated transformation of Markdown and LaTeX source
  files into strictly styled Microsoft Word documents compliant with journal guidelines.
keywords: [Automated Formatting, Academic Publishing, DOCX, Citation Style Language]
---

# Introduction

Academic publishing demands strict adherence to document styling specifications [@doe2024automated]. Formatting errors frequently lead to desk rejections or prolonged editorial review cycles [@smith2025journal].

## Research Question

How efficiently can natural language processing and structural parsing eliminate manual document preparation overhead?

# Methodology

We evaluated **ScholarForm AI** across 500 academic manuscripts written in Markdown and LaTeX.

| Metric | Manual Preparation | ScholarForm AI | Improvement |
| :--- | :---: | :---: | :---: |
| Average Time (min) | 145 | 1.2 | 99.2% |
| Error Rate (%) | 18.4% | 0.1% | 99.5% |

# Results

Figure 1 illustrates the time savings achieved across various citation styles.

![Formatting Speed Comparison](images/speed_comparison.png)

# Conclusion

Automated manuscript formatting significantly decreases administrative overhead for researchers and publishers alike.

# References

- Doe, J. (2024). *Automated Document Workflows in Science*. Academic Press.
- Smith, J. (2025). *Journal Publishing Metrics and Efficiency*. Publishing Quarterly, 12(3), 45-58.
```

---

## 2. Formatting via CLI

Run the `amf format` command to transform your manuscript into APA 7th Edition format:

```bash
amf format -i manuscript.md -o output_apa7.docx -s apa7
```

### CLI Command Options

- `-i, --input`: Path to input Markdown or LaTeX file.
- `-o, --output`: Path where the output `.docx` file will be saved.
- `-s, --style`: Target citation/formatting style (`apa7`, `ieee`, `mla9`, `chicago`, `harvard`).
- `--include-toc`: (Optional) Auto-generate a Table of Contents.

---

## 3. Formatting via Python SDK

You can also perform simple document formatting using the synchronous `AMFClient` Python SDK:

```python
from amf_sdk import AMFClient

# Initialize client pointing to your backend server
client = AMFClient(base_url="http://localhost:8000", api_key="your_api_key_here")

# Format manuscript
response = client.format_document(
    file_path="manuscript.md",
    output_path="output_apa7.docx",
    style="apa7"
)

print(f"Status: {response['status']}")
print(f"Output saved to: {response['output_path']}")
```

---

## 4. Expected Output Features

The generated `output_apa7.docx` file will contain:
- **Title Page**: Correctly formatted title, author affiliations, and running header.
- **Abstract & Keywords**: Styled abstract section with 0.5-inch indents.
- **Body & Headings**: Title 1, Heading 1, Heading 2 styled according to APA 7th rules (12pt Times New Roman, double-spaced).
- **Tables & Figures**: Auto-numbered tables with top/bottom borders and captioned figures.
- **References**: Hanging indents (0.5 inch) and sorted bibliographical references.
