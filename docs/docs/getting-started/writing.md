# Writing Manuscripts

## Markdown Format

Markdown is the recommended input format. It's human-readable, version-control friendly, and supports all manuscript structures.

### Structure

```markdown
# Title of Your Manuscript

By Author Name, Co-Author Name

## Abstract

A concise summary of your research (150-250 words).

**Keywords:** keyword1; keyword2; keyword3

## Introduction

Context, gap, and research question.

## Methods

Design, participants, materials, procedure, analysis.

## Results

Findings with statistical outcomes.

## Discussion

Interpretation, implications, limitations.

## Conclusion

Summary and future directions.

## References

Author, A. A. (Year). Title. *Journal*, Volume(Issue), Pages. https://doi.org/xxx
```

### Rules

1. **Title**: The first `# Heading` becomes the manuscript title
2. **Authors**: `By Name, Name` on the line after the title
3. **Abstract**: Under `## Abstract` heading
4. **Keywords**: After abstract, prefixed with `Keywords:` or `**Keywords:**`
5. **Sections**: `## Heading` for top-level, `### Heading` for subsections
6. **References**: Under `## References` heading, one per line

## LaTeX Format

```latex
\documentclass[12pt]{article}
\title{Your Manuscript Title}
\author{Author Name}
\begin{document}
\maketitle
\begin{abstract}
Abstract text here.
\end{abstract}
\section{Introduction}
Content here.
\section{Methods}
Content here.
\bibliographystyle{apalike}
\bibliography{references}
\end{document}
```

## Plain Text

For plain text, AMF attempts to detect structure from:

- ALL-CAPS lines as section headings
- First line as title
- Line breaks as paragraph separators

## Best Practices

1. **Use Markdown**: It produces the best parsing results
2. **Add an abstract**: Required for APA, MLA, Chicago, Vancouver, AMA
3. **Include keywords**: Recommended for all styles
4. **Structure clearly**: Use proper heading hierarchy
5. **Complete references**: Include DOI where available
