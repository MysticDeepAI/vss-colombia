# VSS Colombia — Verbalized Salience Score

A quantitative instrument for auditing latent demographic bias in Qwen2.5-7B-Instruct, built on Anthropic's Natural Language Autoencoder (NLA). VSS measures whether a single culturally marked word — read in context — pushes the model's internal representation toward Colombian identity, socioeconomic status, or stereotype content, using a minimal-pair counterfactual design and a causal confabulation filter.

This repository is the companion code for the post *"Before the Model Says It: Latent Colombian Identity in Qwen2.5-7B — and the Instrument We Built to Measure It Without Confabulation,"* the follow-up to an [Apart Research](https://apartresearch.com/) hackathon pilot.

## Key results

Across 30 minimal-pair scenarios (10 per attribute, K = 5 samples per position, 120 prompts total):

| Attribute | Median VSS | Positive / 10 | p (Holm-corrected) | Survives ARS filter |
|---|---|---|---|---|
| Nationality | +0.15 | 7 | 0.0234 | Weakens to the edge of significance |
| Stereotype | +0.20 | 6 | 0.0312 | Holds |
| Socioeconomic status | 0.00 | 3 | — | Null (informative, not disappointing) |

No scenario, in any attribute, produced a negative VSS. Full methodology, statistics, and the confabulation-verification step (ARS) are described in the post.

## Repository structure

```
vss-colombia/
├── main.py                       orchestrates the 5-stage pipeline, saves results.json
├── plot_results.py               reads results.json, generates figures (independent of main.py)
├── config.yaml                   all experiment parameters (layer, K, thresholds, paths)
├── environment.yml               conda environment specification
├── dataset/                      30 minimal-pair scenarios (cue/neutral × ES/EN)
├── src/
│   ├── extraction.py             Stage 1 — Qwen activations at 7 token positions
│   ├── verbalization.py          Stage 2 — the AV describes each activation, K=5 samples
│   ├── grading.py                Stage 3 — grader labels mentions, with verbatim-quote audit
│   ├── ars.py                    Stage 4 — AR-verified salience (confabulation filter)
│   └── metric.py                 Stage 5 — Delta, VSS, and the exact permutation test
├── results/                      results.json, per-stage checkpoints, and figures
├── validate_all_stages.py        end-to-end smoke test on a small subset, all 5 stages
├── inspect_ar_checkpoint.py      one-off: inspects the Reconstructor checkpoint structure
├── diagnose_ar_suffix.py         one-off: verifies the AR's suffix-anchored prompt template
├── smoke_test_ar.py              one-off: empirically validates AR reconstruction quality
├── find_anticipation_cases.py    exploratory: scans for pre-cue demographic anticipation
└── ars_survival_table.py         generates the ARS mention-survival table for the paper
```

## Installation

```bash
conda env create -f environment.yml
conda activate vss-colombia
```

**Known version pin:** `transformers==4.57.6` is required — newer releases in the 5.x series conflict with `huggingface_hub>=1.0` (see `environment.yml` for details). If you hit `AttributeError` or `ImportError` on model loading, confirm your installed version matches this pin.

## Usage

### Running the full pipeline

```bash
python main.py
```

This runs all 5 stages in order, saving a checkpoint after each one (`results/results_stage1.json` through `results_stage4.json`, then the final `results/results.json`). Expect this to take several hours on a single GPU — Stage 2 (verbalization) is the bottleneck, at 4,200 AV calls.

### Running partial stages

If a run is interrupted, resume from the last completed stage instead of starting over:

```bash
python main.py --to extraction                                          # stop after Stage 1
python main.py --from grading --input results/results_stage2.json       # resume from Stage 3
```

Stage names, in order: `extraction`, `verbalization`, `grading`, `ars`, `metric`.

### Generating figures

```bash
python plot_results.py
```

Reads the finished `results.json` and produces the positional-mention curves, the per-scenario VSS bar chart, and — if the ARS stage ran — the primary-vs-filtered comparison table. This is deliberately decoupled from `main.py`: regenerating figures never requires GPU time.

### Enabling the ARS confabulation filter

ARS is off by default (`ars.enabled: false` in `config.yaml`) because it loads a second full model. To include it:

```yaml
ars:
  enabled: true
  ar_checkpoint: "kitft/nla-qwen2.5-7b-L20-ar"
  layer_index: 20
  neutral_percentile: 90
```

### Validating the pipeline before a full run

```bash
python validate_all_stages.py
```

Runs all 5 stages on a 2-scenario subset with explicit assertions at each handoff — the cheapest way to catch a broken configuration before committing to a multi-hour run.

## Diagnostic and one-off scripts

A few scripts in the repo root are not part of the regular pipeline; they were built to resolve specific implementation questions and are kept for reproducibility and for anyone extending this work to a different NLA checkpoint:

- **`inspect_ar_checkpoint.py`** — prints the Reconstructor checkpoint's config, metadata, and safetensors keys. Run this first if you ever swap in a different AR checkpoint; several of its architectural assumptions (no separate reconstruction head, raw layer-20 hidden state as the output) were confirmed empirically this way, not assumed from documentation alone.
- **`diagnose_ar_suffix.py`** — decodes the AR's expected prompt suffix against the actual template output, to catch tokenization mismatches before they silently corrupt reconstructions.
- **`smoke_test_ar.py`** — the empirical check behind the ARS design: reconstructs a known activation from its matching explanation versus an unrelated one, confirming the Reconstructor behaves as expected before trusting it at scale.
- **`find_anticipation_cases.py`** — an exploratory scan of neutral-arm explanations at the pre-cue baseline, looking for demographic content that appears with no lexical trigger present. This is qualitative evidence for a phenomenon VSS is structurally unable to measure (see the post's discussion of pre-cue anticipation).
- **`ars_survival_table.py`** — generates the mention-level ARS survival table (how many grader-flagged mentions per attribute survived the confabulation filter), separate from the scenario-level comparison already in `plot_results.py`.

## Configuration reference

All experiment parameters live in `config.yaml`: which layer to extract (`model.layer`), how many AV samples per position (`sampling.k_samples`), batching behavior, the grader backend (`qwen_local` or `claude_api`), and the ARS threshold percentile. Nothing is hardcoded in the pipeline code — change values there, not in `src/`.

## Dataset

30 base scenarios (10 nationality, 10 socioeconomic status, 10 stereotype), each realized as a minimal pair (cue vs. matched neutral keyword) in both Colombian Spanish and English — 120 prompts total. Every pair is validated programmatically (word-level diff, single contiguous span per language) before use; construction criteria, cue-strength grading, and declared per-pair risks are documented alongside the dataset.

## Reference

This work builds directly on the open-source Natural Language Autoencoder released by Anthropic:
Fraser-Taliente et al. (2026), *Natural Language Autoencoders*. https://github.com/kitft/natural_language_autoencoders

## Authors

Pablo Santiago Potes Velasco¹, María del Mar García Matabanchoy¹, Óscar Julián Pérez Ladino¹, Jhoan Stevan Mosquera Ortiz¹, Nicolás Lozano Mazuera¹, Gilber Alexis Corrales Gallego¹˒²

¹ Universidad Autónoma de Occidente, Cali, Colombia
² GobLab, Universidad Adolfo Ibáñez

Contact: gacorrales@uao.edu.co

## Acknowledgements

We thank Apart Research for hosting the hackathon that initiated this project, and Apart Lab for the compute and support that made the follow-up work possible. This work was carried out in the aftermath of the earthquake that struck Colombia on August 10, 2026; it is dedicated to everyone affected, particularly in Cali, our hometown.
