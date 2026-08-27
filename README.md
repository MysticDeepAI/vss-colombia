# VSS Colombia — Verbalized Salience Score

A metric for latent demographic bias in Qwen2.5-7B, using Anthropic's
Natural Language Autoencoder (NLA) to verbalize activations before and
after a sensitive keyword, compared against its neutral twin.

## Structure

```
config.yaml         experiment parameters (layer, K, temperature, paths)
main.py              orchestrates the 4 pipeline stages, saves results.json
plot_results.py       reads results.json, generates figures (independent of main.py)
dataset/              minimal pairs (30 scenarios x 2 languages x 2 arms)
src/
  extraction.py       Stage 1: Qwen activations at 7 positions
  verbalization.py     Stage 2: the AV describes each activation as text (K samples)
  grading.py            Stage 3: the grader decides if each text mentions Colombia
  metric.py             Stage 4: computes Delta, D, and the exact statistical test
results/              results.json + figures (generated when the pipeline runs)
```

## Usage

```bash
conda env create -f environment.yml
conda activate vss-colombia

# Run the full pipeline (needs a GPU, takes several hours because of Stage 2):
python main.py

# Generate figures from the JSON already produced (fast, no GPU needed):
python plot_results.py
```

### Running in parts

If something fails partway through, there's no need to start over:

```bash
# Extraction only, to review activations before spending hours on the AV:
python main.py --to extraction

# Resume from grading using an already-saved partial JSON:
python main.py --from grading --input results/results_stage2.json
```

## What each thing measures (quick glossary)

- **Arm (cue / neutral)**: each scenario has one version with the
  sensitive word (e.g. "arepa") and a twin version with a neutral word
  (e.g. "sandwich"), identical in everything else.
- **Window**: 7 token positions around the keyword: `tw-1` (right before,
  can't know anything about the keyword yet, by transformer causality),
  `tw` (the keyword), and `tw+1` through `tw+5` (after).
- **s_t**: of the K samples from the AV at position t, what fraction
  mentions Colombia.
- **Delta**: how much s_t rises after the keyword compared to before.
- **D**: Delta of the cue arm minus Delta of the neutral arm -- isolates
  the effect attributable to the keyword, subtracting the AV's own
  confabulation rate.

## Speed: why it runs on GPU and can still be slow

`extraction.py` and `verbalization.py` already load models with
`device_map="cuda"`. But having a GPU isn't enough by itself: a GPU pays
off when it processes MANY things at once (batching), not one sequence
at a time. `verbalization.py` takes advantage of this: the 7 positions of
a given prompt share the exact same AV base prompt (same length), so
they're stacked into a single batch and all 7 x K=5 = 35 sequences are
generated in **one `generate()` call** per prompt, instead of 35 serial
calls. This cuts ~4,200 calls down to ~120, with no server or async
needed -- just proper use of standard Hugging Face batching.

On out-of-memory errors, set in `config.yaml`:
```yaml
sampling:
  batch_across_positions: false
```
This falls back to a slower version (7 calls per prompt instead of 1)
that uses much less memory at once.

### Verifying the batching (recommended before a full run)

The batch output reordering assumes `generate()` groups each row's K
samples contiguously (documented Hugging Face behavior, though not part
of its formal public API). Before running all 120 prompts, it's worth
verifying with a smoke test: run `main.py --to verbalization` on 2-3
prompts with `batch_across_positions: true` and compare against the same
run with `false` -- the explanations don't need to be identical (sampling
is random), but they should be **thematically consistent per position**
(e.g. `tw-1` should never mention the keyword in either version). If they
look mixed up, flag it and fall back to `false` while investigating.

## Changing the grader

In `config.yaml`, `grader.backend` can be:
- `qwen_local`: fast, uses the same already-loaded Qwen (default).
- `claude_api`: slower, requires `ANTHROPIC_API_KEY` in the environment,
  but is an independent, more rigorous judge -- useful for validating a
  sample of what `qwen_local` graded.

## Reference

Natural Language Autoencoders: https://github.com/kitft/natural_language_autoencoders
