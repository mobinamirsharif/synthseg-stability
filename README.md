# SynthSeg robustness and stability study

[![Validate repository](https://github.com/mobinamirsharif/synthseg-stability/actions/workflows/validate.yml/badge.svg)](https://github.com/mobinamirsharif/synthseg-stability/actions/workflows/validate.yml)

This repository studies how standard SynthSeg and SynthSeg-robust respond to
controlled changes in image resolution, Gaussian noise, and synthetic spatial
intensity non-uniformity. Its primary reproducibility interface targets a
pinned, openly accessible OpenNeuro dataset. Earlier controlled-access work is
retained only as restricted-data provenance and permitted cohort aggregates.

> Dice here is agreement with the segmentation produced from the clean image
> by the **same model mode**. It measures segmentation stability, not accuracy
> against manual ground truth.

No manual segmentation ground truth was available for either the public or
restricted track. Internal SynthSeg QC scores are not voxel-wise accuracy
measures.

## Research question

How stable are SynthSeg outputs when the same T1-weighted anatomy is subjected
to controlled acquisition-relevant perturbations, and does robust mode change
spatial agreement or volumetric drift relative to standard mode?

## Data boundary

The project was initially motivated by experiments conducted on authorized
controlled-access imaging data. Participant-level raw and derived outputs from
those experiments are not distributed. Public numerical results and figures in
this repository are generated only from openly accessible data or synthetic
inputs.

ADNI images, participant identifiers, participant-level metrics, QC records,
regional volumes, and single-case Phase 3 results are excluded from Git. The
ignored local scientific files are not removed by this cleanup. Nothing in
`results/restricted/` can reconstruct participant records; it contains
documentation and previously approved cohort aggregates only.

## Public dataset

The exploratory public replication is pinned to OpenNeuro
[`ds005125`, snapshot `1.0.0`](https://openneuro.org/datasets/ds005125/versions/1.0.0),
DOI [`10.18112/openneuro.ds005125.v1.0.0`](https://doi.org/10.18112/openneuro.ds005125.v1.0.0).
The dataset is CC0-1.0 and contains 34 three-dimensional T1w scans acquired on a
3 T Siemens Prisma. The experiment uses `sub-01` through `sub-04`, the first
four available T1w participant IDs in lexical BIDS order. This deterministic
rule is fixed in [`config/public_dataset.json`](config/public_dataset.json).

MRI files are downloaded directly from OpenNeuro's public S3 mirror and never
committed. The downloader records source URLs, file sizes, and local checksums.

## Experimental design

Each public image is processed in standard and robust modes. Every perturbed
segmentation is compared with the clean segmentation from the same mode.

| Family | Condition | Exact operation |
|---|---|---|
| Reference | Clean | Original public T1w image |
| Resolution | 2 mm, 3 mm isotropic | `mri_convert --voxsize … --resample_type cubic` |
| Noise | Mild, moderate | sigma = 0.05 or 0.10 × SD(non-zero voxels), seed 42 |
| Intensity | Moderate bias | Controlled multiplicative field, range 0.60–1.40 |
| Intensity | Strong bias | Controlled one-sided field, range 0.45–1.55 |
| Intensity | Strong bias + N4 | Strong field followed by documented N4 |

The bias field is a **controlled synthetic spatial intensity non-uniformity
perturbation**, not a real coil or scanner artifact. Resolution-condition label
maps are aligned to the clean grid with nearest-neighbor interpolation before
Dice calculation. Background is excluded; 32 foreground labels are expected.
Volume summaries include mean and median absolute percentage drift.

```mermaid
flowchart LR
    A[OpenNeuro T1w] --> B[Clean]
    A --> C[2/3 mm cubic]
    A --> D[Gaussian noise]
    A --> E[Synthetic bias]
    E --> F[N4]
    B & C & D & E & F --> G[Standard and Robust SynthSeg]
    G --> H[Nearest-neighbor label alignment]
    H --> I[Clean-reference Dice and volume drift]
    I --> J[CSV summaries and figures]
```

## Public replication results

All 64 planned runs completed for four public participants, eight conditions,
and two modes. Every completion marker, input/output checksum, 32-label output,
volume table, and QC table passed the local audit. The table reports cohort
means (`n=4`); Dice is shown as a percentage and differences are Robust −
Standard in percentage points.

| Condition | Standard Dice | Robust Dice | Dice difference | Standard volume drift | Robust volume drift | Drift difference |
|---|---:|---:|---:|---:|---:|---:|
| 2 mm | 85.510% | 86.189% | +0.679 | 6.664% | 3.152% | −3.512 |
| 3 mm | 85.036% | 86.368% | +1.331 | 8.741% | 5.870% | −2.871 |
| Noise 5% | 98.847% | 98.906% | +0.059 | 0.384% | 0.323% | −0.061 |
| Noise 10% | 97.548% | 98.100% | +0.553 | 0.994% | 0.719% | −0.274 |
| Moderate bias | 99.502% | 99.304% | −0.198 | 0.283% | 0.379% | +0.096 |
| Strong bias | 98.994% | 98.733% | −0.261 | 0.561% | 0.762% | +0.202 |
| Strong bias + N4 | 99.500% | 99.335% | −0.164 | 0.258% | 0.310% | +0.053 |

In this small public subset, robust mode was more stable under resolution and
noise perturbations, particularly for volume drift. Standard mode was slightly
more stable under the synthetic bias fields. N4 reduced the instability caused
by strong synthetic bias for both modes in this configuration, but this does
not establish a universal benefit for real scanner bias or other datasets.

The source artifacts are the
[`64-row participant-level table`](results/public/subject_level/results.csv),
[`mode-level aggregate table`](results/public/aggregate/summary.csv), and
[`paired cohort summary`](results/public/aggregate/cohort_summary.csv).

![Public clean-reference Dice](figures/public/clean_reference_dice.png)

![Public mean absolute volume drift](figures/public/mean_volume_drift.png)

The metric plots show paired-cohort Standard and Robust means, with the mean
Robust − Standard difference annotated for each condition.

## Restricted-data provenance

Earlier exploratory work used authorized, controlled-access ADNI T1-weighted
MPRAGE data and informed this design. ADNI source images and participant-level
derived outputs are not distributed. Reproducing this restricted track requires
obtaining suitable data separately through an authorized ADNI access route.
The public OpenNeuro results above are a distinct replication layer and do not
replace or disclose the restricted study.

### Restricted Phase 2: aggregate-only results

Restricted Phase 2 evaluated two authorized acquisitions (`n=2`) with 2 mm and
3 mm isotropic resampling and the two deterministic Gaussian-noise levels. The
acquisitions had different native geometries and resolutions and should not be
treated as perfectly matched. Only previously approved condition-level means
are public; participant-level inputs, results, QC, and regional volumes remain
private.

| Condition | Mean Standard Dice | Mean Robust Dice | Difference (pp) |
|---|---:|---:|---:|
| 2 mm | 87.860% | 88.465% | +0.605 |
| 3 mm | 88.645% | 89.485% | +0.840 |
| Noise 5% | 98.875% | 99.070% | +0.195 |
| Noise 10% | 97.745% | 98.310% | +0.565 |

![Restricted Phase 2 aggregate clean-reference macro Dice](figures/restricted/phase2/aggregate_macro_dice.png)

| Condition | Mean Standard drift | Mean Robust drift | Difference (pp) |
|---|---:|---:|---:|
| 2 mm | 3.4060% | 1.8560% | −1.5500 |
| 3 mm | 4.4370% | 4.0010% | −0.4360 |
| Noise 5% | 0.4590% | 0.3110% | −0.1480 |
| Noise 10% | 0.9085% | 0.6230% | −0.2855 |

![Restricted Phase 2 aggregate mean absolute volume drift](figures/restricted/phase2/aggregate_volume_drift.png)

These Dice values are same-mode clean-reference agreement, not ground-truth
accuracy. The volume values are arithmetic means of per-acquisition mean
absolute percentage drift. The corresponding approved aggregate tables are in
[`results/restricted/phase2`](results/restricted/phase2).

### Restricted Phase 3: qualitative only

Restricted Phase 3 was a single-acquisition experiment (`n=1`) using controlled
synthetic, acquisition-relevant spatial intensity non-uniformity, including a
strong-bias input followed by N4 correction. It was not a real scanner or coil
artifact. Both modes remained highly stable in the tested case, but N4 effects
were mode- and metric-dependent. This does not show that N4 universally
improves SynthSeg outputs.

Exact Phase 3 metrics, runtimes, figures, QC, and other participant-level
artifacts are intentionally not published. The qualitative observation is
exploratory and should not be generalized. See
[`results/restricted/README.md`](results/restricted/README.md).

### Method provenance

The configurable wrappers preserve the approved command behavior. Standard
SynthSeg passes `--i`, `--o`, `--vol`, `--qc`, and `--threads 1` to
`mri_synthseg`; robust mode adds only `--robust`. Isotropic resampling uses
`mri_convert INPUT OUTPUT --voxsize 2 2 2 --resample_type cubic` or the
corresponding 3 mm values. Low-resolution label maps are returned to their
same-mode clean grid with
`mri_convert TEST OUTPUT --like CLEAN --resample_type nearest`, preserving
discrete labels before Dice calculation. The Dice utility expects 32 foreground
labels and fails on a mismatch unless exploratory override behavior is
explicitly requested.

## Reproducibility environment

The restricted runs recorded FreeSurfer 8.2.0, SynthSeg 2.0,
SynthSeg-robust 2.0, SimpleITK 2.5.6 / ITK 5.4, WSL Ubuntu 24.04, and
`--threads 1`. The recorded host used an AMD Ryzen 9 5900HS CPU and
approximately 16 GB RAM. The public track targets the same software versions. Python dependencies are
pinned in `requirements.txt`; the audited local interpreter is Python 3.12.3
and CI uses Python 3.11. GPU execution is not
claimed. FreeSurfer installation and licensing are external.

N4 uses an Otsu mask (inside 1, outside 0, 200 bins) and iteration schedule
`[50, 50, 30, 20]`. MRI, segmentations, local work products, and download
manifests are ignored by Git.

## Reproduce

With `mri_convert` and `mri_synthseg` on `PATH`:

```bash
python -m pip install -r requirements.txt
python scripts/download_public_data.py
python -m scripts.run_public_experiment
python scripts/summarize_public_results.py
python scripts/plot_public_results.py
python -m scripts.audit_public_experiment
python -m pytest -q
```

The full run makes 64 SynthSeg calls (4 participants × 8 conditions × 2 modes)
with `--threads 1`; plan runtime accordingly.

## Repository structure

```text
config/                         pinned public dataset manifest
scripts/                        download, perturb, run, measure, and plot
tests/                          synthetic-only tests; no controlled data
results/public/                 public participant and aggregate CSVs
results/restricted/             governance notes and approved aggregates
figures/public/                 metric figures and public visual QC
figures/restricted/             approved restricted-data aggregate figures
experiments/phase1/             legacy non-participant method artifacts
.github/workflows/validate.yml  CI and privacy checks
```

## Interpretation and limitations

- Clean-reference Dice is stability, not ground-truth accuracy.
- Four public scans form an illustrative subset, not a clinical benchmark.
- Synthetic perturbations do not capture every real acquisition failure.
- Within-mode comparisons do not establish which segmentation is anatomically
  more accurate.
- N4 findings are specific to the controlled field and fixed configuration.
- Restricted and public cohorts must not be called equivalent without testing.
- Restricted Phase 2 has only two heterogeneous acquisitions; restricted Phase
  3 is a qualitative single-acquisition observation.
- These exploratory results are not a clinical benchmark and should not be
  interpreted as population-level evidence.

## Data availability, licensing, and citation

Public inputs are obtained from OpenNeuro rather than redistributed. Dataset
`ds005125` is CC0-1.0; that does not automatically license this repository's code.
No repository software license was added because none was previously selected.
FreeSurfer and SynthSeg have separate terms.

- Tarder-Stoll H, Baldassano C, Aly M. *The brain hierarchically represents the
  past and future during multistep anticipation*. OpenNeuro ds005125 v1.0.0.
  <https://doi.org/10.18112/openneuro.ds005125.v1.0.0>
- Billot B, Greve DN, Puonti O, et al. [SynthSeg: Segmentation of brain MRI
  scans of any contrast and resolution without retraining](https://doi.org/10.1016/j.media.2023.102789).
  *Medical Image Analysis*. 2023;86:102789.
- Billot B, Magdamo C, Arnold SE, Das S, Iglesias JE. [Robust machine learning
  segmentation for large-scale analysis of heterogeneous clinical brain MRI
  datasets](https://doi.org/10.1073/pnas.2216399120). *PNAS*. 2023;120(9):e2216399120.

Repository citation metadata are in [`CITATION.cff`](CITATION.cff).
