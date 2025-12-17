## deepfake-detection-review

# Deepfake Detection – Literature Review Protocol and Data

This repository documents the end-to-end process used to scope, retrieve, and clean a corpus for a PhD literature review on **deepfake detection** with a focus on facial content. It includes the exact query sets, per-database exports, and the de-duplication workflow that produces the final screening list.

---

## 1) Scope and sources

Primary databases:

* **Scopus**
* **ScienceDirect**
* **IEEE Xplore**

Discovery only (not used for quantitative counts nor inclusion decisions):

* **Google Scholar** (useful for seeding, novelty spotting, and snowballing)

Rationale: the review prioritizes venues and indexes with stable metadata and peer review. Scholar often surfaces preprints, partial notes, or repositories. When Scholar points to a citable item, it is usually indexed in Scopus, ScienceDirect, or IEEE Xplore.

---

## 2) Query sets

Four Boolean sets were defined. Set 0 frames the domain; Sets A–C target specific method families.

```
Set 0 (domain scoping)
"deepfake detection" AND ("face" OR "faces")

Set A (physiological and geometric cues)
"deepfake detection" AND ("head pose" OR "eye blinking" OR "lip-sync" OR "facial landmarks" OR "physiological signals")

Set B (spectral domain and artifacts)
"deepfake detection" AND ("frequency domain" OR "spectral artifacts" OR "compression artifacts" OR "color filter array" OR "noise patterns")

Set C (video dynamics and graphs)
"deepfake detection" AND ("optical flow" OR "temporal consistency" OR "LSTM" OR "graph neural networks" OR "spatio-temporal")
```

---

## 3) Scoping counts

Used only to frame the size of the space, not for screening.

| Engine         |  Set 0 | Set A | Set B | Set C |
| -------------- | -----: | ----: | ----: | ----: |
| Google Scholar | 11,600 | 3,640 | 3,340 | 5,290 |

---

## 4) Targeted retrieval by database (fielded queries)

Matches constrained to article keywords and related metadata.

| Database       | Set 0 | Set A | Set B | Set C |
| -------------- | ----: | ----: | ----: | ----: |
| Scopus         |   379 |    19 |    71 |   105 |
| ScienceDirect  |    75 |    30 |    30 |    51 |
| IEEE Xplore    |   395 |    41 |   161 |   243 |
| Google Scholar | 6,670 | 2,180 | 1,900 | 3,410 |

From the screening stage onward, **Google Scholar is excluded** from the primary corpus. It remains a discovery channel.

---

## 5) De-duplication workflow

Two levels:

1. **Within each set (A, B, C)** across Scopus, ScienceDirect, IEEE Xplore
2. **Across sets** by merging the three within-set lists

### Identity keys

* Primary: **DOI**, normalized by stripping protocol prefixes and trailing punctuation, then lowercasing.
* Fallback: **Title**, normalized with Unicode NFKD, lowercased, punctuation removed, and single-space collapsed.

### Retention precedence

When duplicates refer to the same work, keep the record with the most stable metadata:

**Scopus** > **IEEE Xplore** > **ScienceDirect**

### Results

**Per set**

| Scope                        | Input | Duplicates removed | Unique |
| ---------------------------- | ----: | -----------------: | -----: |
| Query A (physio/geometry)    |    90 |                  6 |     84 |
| Query B (spectral/artifacts) |   262 |                 25 |    237 |
| Query C (spatio-temporal)    |   399 |                 76 |    323 |

**Cross-set merge (A + B + C)**

* Initial combined input: **644**
* Cross-set duplicates removed: **26**
* **Final unique records for screening: 618**

Intersections between method families:

* A ∩ B = 21
* A ∩ C = 3
* B ∩ C = 2
* A ∩ B ∩ C = 0

These small overlaps are consistent with the targeted design of Sets A–C.

---

## 6) Other sources

A small number of items reached the author through professional activities and ancillary channels (seminars, collaborations, challenge or dataset sites that link to citable papers). These are tracked as **Other** in the PRISMA-style diagram and were admitted only if they satisfied the same inclusion and exclusion criteria as database-retrieved records. Preprints are retained if they are the authoritative reference for a dataset or benchmark, or until a peer reviewed version appears.

---

## 7) Repository layout

Suggested structure for this repo:

```
/raw/
  query-0_Scopus_379.csv
  query-0_ScienceDirect_75.txt
  query-0_IEEEXplore_395.csv
  query-A_Scopus_19.csv
  query-A_ScienceDirect_30.txt
  query-A_IEEEXplore_41.csv
  query-B_Scopus_71.csv
  query-B_ScienceDirect_30.txt
  query-B_IEEEXplore_161.csv
  query-C_Scopus_105.csv
  query-C_ScienceDirect_51.txt
  query-C_IEEEXplore_243.csv

/processed/
  query-A_merged_deduplicated.csv
  query-B_merged_deduplicated.csv
  query-C_merged_deduplicated.csv
  query-ABC_merged_deduplicated.csv

/scripts/
  deduplicate.py
  parse_sciencedirect.py
  make_abc.py
```

---

## 8) Reproduction notes

Normalization helpers (Python):

```python
import re, unicodedata

def norm_doi(s):
    if not s:
        return ""
    s = s.strip().lower()
    s = s.replace("https://doi.org/","").replace("http://doi.org/","").strip().strip(".")
    m = re.search(r"(10\.\d{4,9}/\S+)", s)
    return m.group(1).rstrip(".,;)") if m else ""

def norm_title(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
```

* Primary key: `norm_doi(record) or norm_title(record)`
* Precedence for ties: Scopus > IEEE Xplore > ScienceDirect
* CSV parsing of ScienceDirect exports may need a simple text parser because some exports are TXT blocks. The repository includes `parse_sciencedirect.py` with a DOI-anchored extractor.

---

## 9) Using the outputs

* Use `processed/query-ABC_merged_deduplicated.csv` (618 records) for screening and synthesis.
* The PRISMA-style flow in the thesis references these counts. The final box in that diagram points to the evidence map table in the thesis.

---

## 10) Citation

If you use this material, please cite the thesis and this repository. Suggested citation:

```
Stile, V. (2025). Deepfake Detection – Literature Review, Queries Data.
GitHub repository, https://github.com/vstile/deepfake-detection-review
```

---

## 11) Privacy and reuse policy

* This repository contains bibliographic metadata and exported references. No personal data are included.
* **Reuse is permitted provided that you cite the author and this work.**
* Recommended license: **Creative Commons Attribution 4.0 International (CC BY 4.0)**. You are free to share and adapt the material for any purpose, even commercially, as long as appropriate credit is given, a link to the license is provided, and any changes are indicated.

Short attribution text you can include in derivative works:

```
This material reuses data and methods from:
Stile, V. (2025). Deepfake Detection – Literature Review, Queries Data.
GitHub repository, https://github.com/vstile/deepfake-detection-review
Licensed under CC BY 4.0.
```

---

**Availability of materials.** The complete search logs, per-database exports, deduplicated corpora for Sets A–C, the cross-set merged list, and the parsing and reconciliation scripts are publicly available in this repository.
