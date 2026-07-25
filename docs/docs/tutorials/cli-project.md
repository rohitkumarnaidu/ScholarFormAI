# CLI Project Setup

## Step 1: Initialize

```bash
# Create a new manuscript project
amf init -n my-thesis -s apa

# Navigate to project
cd my-thesis
```

## Step 2: Write Your Manuscript

Edit `manuscript.md`:

```markdown
# The Impact of Climate Change on Coastal Ecosystems

By Jane Smith

## Abstract

This study examines the effects of climate change on coastal ecosystems.

**Keywords:** climate change, coastal ecosystems, biodiversity

## Introduction

Coastal ecosystems are among the most vulnerable to climate change.

## Methods

We analyzed 50 years of coastal ecosystem data.

## Results

Significant biodiversity loss was observed.

## Discussion

These findings have important implications for conservation.

## References

Smith, J. (2023). Coastal ecosystem changes. *Marine Biology*, 45(2), 123-135.
```

## Step 3: Validate

```bash
amf validate -i manuscript.md -s apa
```

## Step 4: Format

```bash
amf format -i manuscript.md -s apa -o thesis_chapter1.docx
```

## Step 5: Generate Preview

```bash
amf preview -i manuscript.md -s apa --open
```

## Step 6: Iterate with Watch Mode

```bash
amf format -i manuscript.md -s apa -o thesis_chapter1.docx --watch
```

Now edit `manuscript.md` — AMF will auto-reformat on each save.
