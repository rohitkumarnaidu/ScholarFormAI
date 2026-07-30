# User Guide

## Getting Started

AMF provides three ways to format your manuscripts: a web interface, a command-line tool, and a Python API.

### Web Interface

1. Open `http://localhost:3000` (or the hosted version)
2. Click "Format" in the navigation
3. Paste or upload your manuscript text
4. Select your citation style
5. Adjust formatting options
6. Click "Download DOCX" or "Preview"

### Command Line

```bash
# Create a new project
amf init -n my-paper

# Format it
amf format -i my-paper/manuscript.md -s apa

# Validate first
amf validate -i my-paper/manuscript.md -s apa

# Generate preview
amf preview -i my-paper/manuscript.md -s apa --open
```

## Writing Your Manuscript

### Markdown (Recommended)

```markdown
# Your Paper Title

By Author Name

## Abstract
Write your abstract here.

Keywords: keyword1, keyword2

## Introduction
Start writing your paper.

## Methods
Describe your methods.

## Results
Present your findings.

## References
Author, A. (Year). Title. Journal, Volume(Issue), Pages.
```

### LaTeX

```latex
\title{Your Paper Title}
\author{Author Name}
\begin{document}
\maketitle
\begin{abstract}
Write your abstract here.
\end{abstract}
\section{Introduction}
Start writing.
\section{Methods}
Describe methods.
\end{document}
```

## Formatting Options

### Page Size

- **A4** (210 × 297 mm) — Standard for Europe/Asia
- **Letter** (8.5 × 11 in) — Standard for North America
- **Legal** (8.5 × 14 in) — Legal documents

### Font

- Times New Roman (standard for most academic styles)
- Arial, Calibri, Georgia, Palatino

### Line Spacing

- 1.0 (single), 1.15, 1.5, 2.0 (double — standard for APA/MLA)

### Margins

- Default: 1 inch (2.54 cm) on all sides
- Adjustable from 0.5 to 2 inches

## Style-Specific Features

### APA 7th Edition

- Running head on every page
- Title page with author affiliation
- Abstract on page 2
- Level 1-5 headings with specific formats
- Hanging indent references
- Page numbers top right

### MLA 9th Edition

- No title page (header with name/professor/class/date)
- Last name + page numbers top right
- Works Cited with hanging indent
- 1-inch margins throughout

### Chicago 17th Edition

- Title page
- Notes-Bibliography style
- Footnotes support
- Bibliography with hanging indent

### IEEE

- Two-column format (optional)
- Numbered references [1], [2], etc.
- 10pt font standard
- Abstract and keywords
