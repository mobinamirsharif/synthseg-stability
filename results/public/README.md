# Public replication results

These results come exclusively from four CC0 OpenNeuro `ds005125` v1.0.0 T1w
images (`sub-01` through `sub-04`). They do not contain ADNI-derived values.

- `subject_level/results.csv`: 64 rows, one per participant × condition × mode.
- `aggregate/summary.csv`: 16 mode-level summaries, each with `n=4`.
- `aggregate/cohort_summary.csv`: eight condition-level Standard/Robust means
  and paired Robust − Standard differences.

`clean_reference_macro_dice` is within-mode segmentation stability, not
manual-ground-truth accuracy. Volume-drift columns are absolute percentage
changes relative to the same-mode clean reference. Runtime values are measured
wall-clock seconds; the first retained run uses the 440-second timing printed
by SynthSeg before checkpoint support was added.

All 64 segmentations had 32 foreground labels. Resolution-condition label maps
were aligned to their same-mode clean grids with nearest-neighbor interpolation
before Dice calculation.
