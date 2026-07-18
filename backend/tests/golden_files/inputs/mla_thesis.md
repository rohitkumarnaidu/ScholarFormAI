<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
template: mla
title: A Framework for Diachronic Corpus Analysis of Early Modern English Scientific Texts
authors:
  - Rebecca Hamilton
affiliations:
  - Department of English Linguistics, University of Edinburgh
keywords:
  - diachronic linguistics
  - corpus analysis
  - early modern English
  - MLA style
  - PhD thesis
abstract: "This thesis presents a computational framework for analysing diachronic linguistic change in early modern English scientific texts (1500-1700). Using a 5-million-word corpus drawn from the Early English Books Online database, we apply distributional semantic models to track semantic shift in technical vocabulary across two centuries of scientific writing."
acknowledgements: "I thank my supervisor, Prof. James Whitaker, for his invaluable guidance throughout this research. I am grateful to the University of Edinburgh's School of Philosophy, Psychology and Language Sciences for funding. Special thanks to the EEBO-TCP project for making their corpus publicly available."
---

# Abstract

This thesis presents a computational framework for analysing diachronic linguistic change in early modern English scientific texts (1500-1700). Using a 5-million-word corpus drawn from the Early English Books Online database, we apply distributional semantic models to track semantic shift in technical vocabulary across two centuries of scientific writing.

# Acknowledgements

I thank my supervisor, Prof. James Whitaker, for his invaluable guidance throughout this research. I am grateful to the University of Edinburgh's School of Philosophy, Psychology and Language Sciences for funding. Special thanks to the EEBO-TCP project for making their corpus publicly available.

# Table of Contents

1. Introduction
2. Literature Review
3. Methodology
4. Corpus Compilation
5. Results
6. Discussion
7. Conclusion
Appendices

# Introduction

The early modern period (1500-1700) witnessed a dramatic expansion of scientific vocabulary in English (Crystal 2004; Nevalainen 2006). This thesis investigates how computational methods can illuminate the processes of semantic change that accompanied the emergence of modern scientific discourse.

## Research Questions

This study addresses three primary research questions: (1) How did scientific terminology evolve between 1500 and 1700? (2) Can distributional semantic models detect diachronic semantic shift in historical corpora? (3) What patterns of metaphorical extension characterise early modern scientific writing?

## Thesis Structure

Chapter 2 reviews the relevant literature on historical linguistics and computational semantics. Chapter 3 describes our methodology, including corpus preprocessing and model architecture. Chapter 4 details corpus compilation procedures. Chapters 5 through 7 present results, discussion, and conclusions.

# Literature Review

## Historical Background

Early modern English underwent significant lexical expansion driven by the Renaissance and the Scientific Revolution (Barber 1997). The period saw a influx of Latin and Greek loanwords, as well as semantic narrowing of existing terms (Durkin 2009).

## Computational Approaches

Recent advances in distributional semantics (Mikolov et al. 2013; Pennington et al. 2014) have enabled large-scale analysis of semantic change (Hamilton et al. 2016; Kutuzov et al. 2018).

# Methodology

## Corpus Preprocessing

Texts were tokenised, lemmatised, and tagged for part of speech using the VARD normalisation tool for historical English (Rogos-Hansen 2019).

## Semantic Modelling

We trained word2vec skip-gram models (Mikolov et al. 2013) on 50-year sub-periods of the corpus, using 300-dimensional embeddings. Semantic shift was quantified using cosine distance between time-specific vectors (Hamilton et al. 2016).

# Results

## Semantic Shift Scores

Our analysis identified 847 lexical items with statistically significant semantic change (p < 0.01). The domains most affected were alchemy-to-chemistry terminology and anatomical vocabulary.

## Case Studies

The term "spirit" underwent semantic narrowing from a broad concept encompassing all subtle fluids to a primarily religious/psychological term. Conversely, "cell" expanded from a small room or monastic dwelling to the fundamental unit of biological organisation.

# Discussion

The results confirm that distributional semantic models can capture known patterns of semantic change while also revealing previously undocumented shifts. However, the sparsity of historical data presents significant methodological challenges.

# Conclusion

This thesis demonstrates that computational diachronic semantics offers powerful tools for understanding the evolution of scientific language. Future work should extend the analysis to other genres and periods.

# Appendices

## Appendix A: Corpus Metadata

Complete bibliographic records for all 2,341 texts included in the corpus.

## Appendix B: Model Hyperparameters

Full specification of word2vec training parameters and evaluation metrics.

## Appendix C: Supplementary Results

Complete list of 847 lexical items with semantic shift scores and significance values.

# Works Cited

Barber, Charles. *Early Modern English*. Edinburgh UP, 1997.

Crystal, David. *The Stories of English*. Penguin, 2004.

Durkin, Philip. *The Oxford Guide to Etymology*. Oxford UP, 2009.

Hamilton, William L., et al. "Diachronic Word Embeddings Reveal Statistical Laws of Semantic Change." *Proceedings of ACL*, 2016, pp. 1489-1501.

Kutuzov, Andrey, et al. "Diachronic Word Embeddings and Semantic Shifts: A Survey." *Proceedings of COLING*, 2018, pp. 1384-1397.

Mikolov, Tomas, et al. "Efficient Estimation of Word Representations in Vector Space." *arXiv:1301.3781*, 2013.

Nevalainen, Terttu. *An Introduction to Early Modern English*. Edinburgh UP, 2006.

Pennington, Jeffrey, et al. "GloVe: Global Vectors for Word Representation." *Proceedings of EMNLP*, 2014, pp. 1532-1543.

Rogos-Hansen, Jacob. "VARD: A Tool for the Normalisation of Historical English." *Digital Scholarship in the Humanities*, vol. 34, no. 2, 2019, pp. 432-445.
