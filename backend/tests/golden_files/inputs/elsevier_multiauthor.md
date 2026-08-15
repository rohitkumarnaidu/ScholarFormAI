<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---
template: elsevier
title: Multi-Centre Clinical Validation of Transformer-Based Histopathology Classification
authors:

- Maria Santos
- Priya Kapoor
- David Chen
- Hassan Al-Rashid
- Ingrid Johansson
- Thomas Mueller
- Aisha Okafor
- Yuki Tanaka
affiliations:
- Department of Pathology, University of São Paulo
- Centre for AI in Medicine, Indian Institute of Technology Delhi
- Division of Computational Pathology, University of Cambridge
- College of Medicine, Qatar University
- Department of Medical Epidemiology, Karolinska Institutet
- Institute of Pathology, Charité Universitätsmedizin Berlin
- Faculty of Medical Sciences, University of Lagos
- Graduate School of Medicine, University of Tokyo
corresponding_author: Maria Santos (<m.santos@pathol.usp.br>)
orcid:
- 0000-0001-2345-6789
- 0000-0002-3456-7890
- 0000-0003-4567-8901
- 0000-0004-5678-9012
- 0000-0005-6789-0123
- 0000-0006-7890-1234
- 0000-0007-8901-2345
- 0000-0008-9012-3456
keywords:
- histopathology
- transformer
- clinical validation
- multi-centre study
- whole-slide imaging
data_availability: "The datasets generated and analysed during the current study are available in the TCGA repository (<https://portal.gdc.cancer.gov/>). Code is available at <https://github.com/scholarform/histo-transformer>. All other data are available from the corresponding author on reasonable request."
funding: "This work was supported by the São Paulo Research Foundation (FAPESP) Grant No. 2024/12345-6, the Swedish Research Council Grant No. 2024-06789, and the German Research Foundation (DFG) Grant No. MU-4567/1."

---

# Abstract

**Background:** Transformer-based models have shown promise in histopathology image analysis, but multi-centre clinical validation remains limited. **Methods:** We conducted a retrospective study across eight centres spanning four continents, evaluating a Vision Transformer (ViT-L/16) on 12,847 whole-slide images. **Findings:** The model achieved a mean AUC of 0.941 (95% CI: 0.928-0.954) across all centres, with minimal performance degradation across domains. **Interpretation:** Transformer-based histopathology classification generalises effectively across diverse clinical settings, supporting its potential for clinical deployment.

# Introduction

Computational pathology has undergone rapid transformation with the advent of deep learning[1,2], particularly transformer architectures[3,4]. However, most published studies report single-centre results with limited external validation[5,6]. This gap between promising model performance and real-world clinical deployment necessitates rigorous multi-centre evaluation[7].

## Clinical Need

Histopathology remains the gold standard for cancer diagnosis[8], but inter-observer variability and workload constraints drive demand for automated decision support[9,10]. Transformer models offer superior feature extraction compared to convolutional alternatives[11,12].

# Methods

## Study Design

We conducted a retrospective, multi-centre diagnostic accuracy study following the STARD guidelines[13]. The study protocol was approved by institutional review boards at all eight participating centres.

## Data Collection

Each centre contributed whole-slide images from three cancer types: breast carcinoma, prostate adenocarcinoma, and lung squamous cell carcinoma. The final dataset comprised 12,847 slides (Table 1).

| Cancer Type | Centres | Slides | Positive % |
| ------------- | --------- | -------- | ------------ |
| Breast | 8 | 5,234 | 47.2% |
| Prostate | 6 | 4,156 | 51.8% |
| Lung | 5 | 3,457 | 43.6% |

## Model Architecture

We employed a Vision Transformer (ViT-L/16) with 307M parameters, pretrained on ImageNet-21K and fine-tuned on the combined training set (60% of slides per centre). Patches of size 16×16 at 20× magnification were used as input tokens.

## Statistical Analysis

Primary analysis used receiver operating characteristic (ROC) analysis with DeLong's method[14] for AUC comparison. Secondary analyses included calibration assessment[15] and subgroup analysis by cancer type and centre.

# Results

## Overall Performance

The ViT-L/16 model achieved an AUC of 0.941 (95% CI: 0.928-0.954), with sensitivity of 89.3% and specificity of 91.2% at the optimal operating point. Performance was consistent across all eight centres (range: 0.912-0.968).

## Subgroup Analysis

| Subgroup | AUC | 95% CI | n |
| ---------- | ----- | -------- | --- |
| Breast | 0.953 | 0.938-0.968 | 5,234 |
| Prostate | 0.934 | 0.912-0.956 | 4,156 |
| Lung | 0.928 | 0.901-0.955 | 3,457 |

## Data Availability Statement

The datasets generated and analysed during the current study are available in the TCGA repository (<https://portal.gdc.cancer.gov/>). Code is available at <https://github.com/scholarform/histo-transformer>.

# Discussion

This multi-centre study provides robust evidence for the generalisability of transformer-based histopathology classification. The consistent performance across diverse clinical settings, staining protocols, and patient populations supports clinical translation[16,17].

## Limitations

Despite the large sample size, our study has limitations. The retrospective design introduces potential selection bias, and all slides originated from tertiary care centres, limiting generalisability to community practice.

# Conclusion

Vision Transformer models demonstrate strong and consistent performance across multiple international centres for histopathology classification. Prospective validation studies are warranted prior to clinical deployment.

# Data Availability

The datasets generated and analysed during the current study are available in the TCGA repository (<https://portal.gdc.cancer.gov/>). Code is available at <https://github.com/scholarform/histo-transformer>. All other data are available from the corresponding author on reasonable request.

# Acknowledgements

This work was supported by the São Paulo Research Foundation (FAPESP) Grant No. 2024/12345-6, the Swedish Research Council Grant No. 2024-06789, and the German Research Foundation (DFG) Grant No. MU-4567/1.

# Declaration of Competing Interests

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

# References

1. Esteva A, et al. Dermatologist-level classification of skin cancer with deep neural networks. *Nature*. 2017;542(7639):115-118.
2. Campanella G, et al. Clinical-grade computational pathology using weakly supervised deep learning. *Nat Med*. 2019;25(8):1301-1309.
3. Dosovitskiy A, et al. An image is worth 16x16 words: transformers for image recognition at scale. *ICLR*. 2021.
4. Chen C, et al. TransUNet: transformers make strong encoders for medical image segmentation. *arXiv:2102.04306*. 2021.
5. Liu Y, et al. A comparison of deep learning performance across healthcare systems. *Lancet Digit Health*. 2023;5(4):e218-e228.
6. Topol EJ. High-performance medicine: the convergence of human and artificial intelligence. *Nat Med*. 2019;25(1):44-56.
7. Rajpurkar P, et al. The need for rigorous evaluation of AI in clinical medicine. *NEJM AI*. 2024;1(1):AIra2300123.
8. WHO Classification of Tumours Editorial Board. WHO classification of tumours of the breast. 5th ed. IARC; 2024.
9. Elmore JG, et al. Diagnostic concordance among pathologists interpreting breast biopsy specimens. *JAMA*. 2015;313(11):1122-1132.
10. Tizhoosh HR, Pantanowitz L. Artificial intelligence and digital pathology: challenges and opportunities. *J Pathol Inform*. 2018;9:38.
11. Caron M, et al. Emerging properties in self-supervised vision transformers. *ICCV*. 2021.
12. Lu MY, et al. Data-efficient and weakly supervised computational pathology on whole-slide images. *Nat Biomed Eng*. 2021;5(6):555-570.
13. Bossuyt PM, et al. STARD 2015: an updated list of essential items for reporting diagnostic accuracy studies. *BMJ*. 2015;351:h5527.
14. DeLong ER, et al. Comparing the areas under two or more correlated receiver operating characteristic curves. *Biometrics*. 1988;44(3):837-845.
15. Van Calster B, et al. A calibration hierarchy for risk models. *J Clin Epidemiol*. 2016;74:167-176.
16. Shen K, et al. External validation of pathology AI algorithms: a systematic review. *Lancet Digit Health*. 2024;6(2):e112-e124.
17. Muehlematter UJ, et al. Approval of artificial intelligence and machine learning-based medical devices in the USA and Europe. *JAMA Netw Open*. 2021;4(10):e2128319.
