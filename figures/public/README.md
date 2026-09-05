# Public figures

- `clean_reference_dice.png`: participant-level Standard/Robust paired points
  and Robust − Standard clean-reference Dice differences.
- `mean_volume_drift.png`: corresponding mean absolute volume-drift results.
- `public_qc_contact_sheet.png`: orthogonal T1w slices with segmentation-extent
  overlays for seven representative public runs across all four participants.

The metric figures are generated from
`results/public/subject_level/results.csv` by `scripts/plot_public_results.py`.
The contact sheet is generated from ignored local CC0 OpenNeuro inputs and
outputs by `scripts/plot_public_qc.py`; it contains no restricted-data image.
