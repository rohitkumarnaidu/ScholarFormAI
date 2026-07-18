<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
template: harvard
title: Figure-Group Layout Analysis for Multi-Panel Scientific Figures
authors:
  - Oliver Thompson
  - Sofia Martinez
affiliations:
  - Visual Analytics Lab, University of Cambridge
keywords:
  - figure grouping
  - sub-figures
  - Harvard referencing
  - multi-panel layout
---

# Abstract

Multi-panel scientific figures present unique layout challenges for automated formatting. We propose a comprehensive framework for figure-group detection, sub-figure labelling, and caption nesting.

# Introduction

Scientific manuscripts increasingly rely on multi-panel figures to convey complex results[1,2]. However, automated formatting pipelines frequently fail to preserve figure-group layout structures[3,4]: sub-figure labels are misplaced, shared legends are duplicated, and cross-references are broken.

## Related Work

Existing figure analysis tools[5,6] focus on single-image extraction rather than group layout. The Harvard referencing style[7] requires precise figure numbering and caption placement.

# Methods

We developed a hierarchical figure-group model supporting four layout types:

- **Grid layout:** Uniform row × column arrangement (e.g., Figure 1)
- **Nested layout:** Sub-figures within sub-figures (e.g., Figure 2)
- **Freeform layout:** Arbitrary panel positioning (e.g., Figure 3)
- **Sequential layout:** Linear panel ordering (e.g., Figure 4)

**Figure 1: Grid layout example.** A 2×3 grid showing model performance across six conditions.

**Figure 2: Nested sub-figure structure.** (a) Main experimental setup with (a.1) sensor array, (a.2) data acquisition; (b) Control system layout.

**Figure 3: Freeform panel arrangement.** (A) Top-left: architecture diagram; (B) Top-right: latency graph; (C) Bottom-span: comparison table.

## Figure 4: Sequential pipeline stages.

Stage 1 (left) shows data ingestion; Stage 2 (center) shows preprocessing; Stage 3 (right) shows classification output.

Each sub-figure maintains an individual caption while participating in the parent group's overall caption.

# Results

We evaluated our framework on 500 multi-panel figures from 200 published articles[8,9,10]. Figure 5 summarises the detection accuracy.

**Figure 5: Detection accuracy by layout type.** Grid: 96.2%, Nested: 88.7%, Freeform: 79.4%, Sequential: 93.1%.

# Discussion

Our figure-group model achieves high accuracy for grid and sequential layouts but struggles with freeform arrangements[11,12]. Future work should incorporate deep learning-based panel segmentation[13].

# Conclusion

Hierarchical figure-group models significantly improve multi-panel figure handling in automated formatting pipelines. The proposed framework establishes a reproducible benchmark for figure layout evaluation.

# References

Allen, P. (2023) 'Multi-panel figure detection in scholarly articles', *Journal of Visual Communication*, 45(3), pp. 234-251.

Baker, S. and Chen, L. (2024) 'Layout preservation in automated document formatting', *IEEE Transactions on Visualization*, 30(2), pp. 112-128.

Carter, D., Singh, R. and Park, M. (2022) 'Figure-group integrity in publishing pipelines', *International Journal of Document Analysis*, 18(4), pp. 301-318.

Davies, H. and Kumar, A. (2023) 'Sub-figure label detection using convolutional networks', *Pattern Recognition*, 135, p. 109012.

Evans, N. (2024) 'Single-image extraction from compound scientific figures', *J. Digital Libraries*, 25(1), pp. 45-62.

Fernandez, G. and O'Brien, T. (2023) 'Figure analysis tools for automated publishing', *Software: Practice and Experience*, 53(8), pp. 1678-1695.

Harvard University Press (2025) *Harvard referencing style guide*, 5th edn. Cambridge, MA: Harvard University Press.

Garcia, M. and Lee, J. (2024) 'Grid layout detection in multi-panel figures', *Computer Vision and Image Understanding*, 238, p. 103876.

Hughes, D. and Patel, S. (2023) 'Large-scale evaluation of figure extraction accuracy', *Scientometrics*, 128(5), pp. 2891-2912.

Ito, K. and Svensson, E. (2024) 'Panel detection in biomedical visualisations', *BMC Bioinformatics*, 25(1), p. 112.

Jackson, F. and White, R. (2023) 'Freeform panel arrangement challenges', *ACM Trans. Graph.*, 42(4), pp. 1-15.

Kim, S. and Thompson, L. (2024) 'Limitations of existing figure processing tools', *J. Assoc. Inf. Sci. Technol.*, 75(2), pp. 189-204.

Liu, Y. and Ahmed, S. (2023) 'Deep learning for panel segmentation in compound figures', *Neural Networks*, 162, pp. 234-249.
