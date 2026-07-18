<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
template: vancouver
title: Multi-Level Reference Analysis in Computational Biomedicine
authors:
  - Akiko Tanaka
  - James Rodriguez
affiliations:
  - Department of Computational Biomedicine, University of Tokyo
  - Centre for Health Informatics, University of Manchester
keywords:
  - computational biomedicine
  - citation analysis
  - Vancouver style
footnotes:
  - "This work was supported by JSPS KAKENHI Grant No. 24K12345."
  - "Presented in part at the 2025 International Conference on Biomedical Informatics."
corresponding_author: Akiko Tanaka (tanaka@compbio.u-tokyo.ac.jp)
orcid:
  - 0000-0002-1234-5678
  - 0000-0003-8765-4321
---

# Abstract

**Background:** Multi-level reference structures are common in computational biomedicine manuscripts. **Methods:** We evaluated citation patterns across 500 articles using the Vancouver numbering system[1]. **Results:** Nested citations (references within references) occur in 12.3% of publications. **Conclusion:** Vancouver-style formatting must handle three or more levels of citation depth.

# Introduction

Biomedical literature frequently employs nested citation chains where a primary reference[1] cites secondary sources[2,3], which in turn cite tertiary material[4-6]. This multi-level structure is poorly handled by existing formatting pipelines[7]. The Vancouver style[8] mandates sequential numbering, but footnotes[^1] and equations require additional care.

Consider the logistic regression model:

$$P(y=1|x) = \frac{1}{1 + e^{-(\beta_0 + \beta_1 x_1 + \cdots + \beta_p x_p)}}$$

This equation is adapted from previous work[9] with modifications for multi-level analysis[^2].

## Methods

### Dataset

We analysed 500 articles indexed in PubMed[10,11] published between 2020 and 2025. The inclusion criteria followed PRISMA guidelines[12].

### Statistical Analysis

The chi-squared statistic was computed as:

$$\chi^2 = \sum_{i=1}^{k} \frac{(O_i - E_i)^2}{E_i}$$

where $O_i$ is the observed frequency and $E_i$ is the expected frequency under the null hypothesis[13]. The significance threshold was set at $\alpha = 0.05$[14].

## Results

Our analysis revealed that 12.3% of articles contain at least one nested citation[1,2,15]. Among these, 4.1% contain three or more levels of nesting[3,5,6,16].

$$\text{Prevalence} = \frac{n_{\text{nested}}}{N_{\text{total}}} = 0.123$$

## Discussion

The Vancouver numbering system[8] remains the standard for biomedical citations[17], but our findings suggest that formatting tools require enhancement to handle deep citation chains[7,18]. Future work should explore hierarchical reference displays[19].

## Conclusion

Multi-level citations are a significant formatting challenge. We recommend that automated formatters support at least four levels of citation depth.

# Acknowledgements

The authors thank Dr. Sarah Chen for statistical consultation[^3].

# References

1. Smith JA, Lee K. Deep citation networks in biomedical literature. *J Biomed Inform*. 2023;140:104321.
2. Brown TL, Garcia M, Williams R, Chen X, Patel S, Kumar A, et al. Nested referencing patterns. *Nature Methods*. 2022;19(4):412-419.
3. Johnson P. Tertiary citations in systematic reviews. *BMC Med Res Methodol*. 2021;21:156.
4. Davis R, Thompson K. Fourth-level citation analysis. *Stat Med*. 2020;39(12):1789-1801.
5. Kim S, Park J-H, Lee M, Tanaka A, O'Brien T, Hughes D, et al. Multi-level reference structures. *PLoS One*. 2024;19(3):e0298765.
6. Wilson E, Anderson B, Taylor M, Clark J, Wright P, Hall R, et al. Deep citation indexing. *J Am Med Inform Assoc*. 2023;30(7):1234-1245.
7. Martinez L, White S. Automated formatting for biomedical manuscripts. *Bioinformatics*. 2024;40(2):btae045.
8. International Committee of Medical Journal Editors. Recommendations for the conduct, reporting, editing, and publication of scholarly work in medical journals. *ICMJE*. 2023.
9. Zhang Y, Chen L, Wang H. Logistic regression in biomedical research. *Am J Epidemiol*. 2022;191(5):876-889.
10. PubMed Central. Open access subset. National Library of Medicine; 2025.
11. Landis JR, Koch GG. The measurement of observer agreement for categorical data. *Biometrics*. 1977;33(1):159-174.
12. Page MJ, McKenzie JE, Bossuyt PM, Boutron I, Hoffmann TC, Mulrow CD, et al. The PRISMA 2020 statement. *BMJ*. 2021;372:n71.
13. Pearson K. On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling. *Philos Mag*. 1900;50(302):157-175.
14. Fisher RA. Statistical methods for research workers. Oliver and Boyd; 1925.
15. Lopez-Garcia G, Martinez-Ruiz A, Fernandez-Lopez P, Garcia-Torres M, Rodriguez-Sanchez L. Nested citation prevalence analysis. *J Informetr*. 2023;17(4):101456.
16. Thomas H, Jackson O, Lee S, Wang Y, Park J, Brown F, et al. Tertiary citation depth in biomedical publications. *Scientometrics*. 2024;129(2):987-1004.
17. Patrias K. Citing medicine: the NLM style guide for authors, editors, and publishers. 2nd ed. National Library of Medicine; 2007.
18. O'Brien M, Walsh T, Kelly D, Murray P, Ryan J, Brennan A, et al. Reference chain depth in academic publishing. *Learned Publishing*. 2023;36(3):345-358.
19. Harper R, Aerts J. Hierarchical reference displays for scientific literature. *Inf Vis*. 2024;23(1):45-61.

[^1]: Funding disclosure: this project received no external funding beyond the JSPS grant.
[^2]: Full model specifications are available in the supplementary materials.
[^3]: Dr. Chen served as independent statistical reviewer.
