<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Abstract

We study graph transformers for reasoning over citation networks. Our model combines structural attention with scalable sampling.

# Introduction

Recent graph neural networks struggle with long range dependencies. We aim to improve relational reasoning for academic graphs.

# Methods

We propose a sparse attention architecture with subgraph sampling and positional encodings. Training uses masked node prediction and supervised classification.

# Results

On three citation datasets, our approach improves macro F1 by 4 to 6 points. Runtime remains within a 10 percent overhead compared with baselines.

Figure 1. Overview of the graph transformer pipeline.

# Discussion

Gains are largest on sparse graphs where neighborhood depth matters. Ablations show attention sparsity is critical.

Table 1. Benchmark accuracy on three citation datasets.

# Conclusion

Graph transformers provide consistent improvements for citation analysis and link prediction. Future work will explore adaptive sparsity.

# References

[1] A. Author. Graph attention in citation networks. 2021.
[2] B. Author. Scalable sampling for GNNs. 2020.
