#!/usr/bin/env python3
"""Layer check: should the pipeline read hidden_states[20] or hidden_states[21]?

Why: the NLA checkpoint for Qwen2.5-7B is "layer 20". The official NLA examples say layer 20 =
HF hidden_states[21] (the output of block 20, because hidden_states[0] is the embedding). The NLA
README's minimal snippet, and src/extraction.py, use hidden_states[20] (the output of block 19).
This script settles it with the official reconstructor (NLACritic), as follows:

  1. Run Qwen on the cue prompts and keep hidden_states[20] and [21] at the 7 window positions.
  2. Let the AV describe each vector (near-greedy: temperature 0.01, one sample).
  3. Reconstruct each description with the official NLACritic and measure the cosine to the
     activation. The AR was trained to rebuild the output of block 20 = hidden_states[21], so
     descriptions made from the right vector should reconstruct hidden_states[21] better.

Decision rule (fixed before running, from the 13 Nov plan):
  - index 21 is the default (it is what the official examples say);
  - if descriptions from [20] beat those from [21] on 8 or more of the prompts AND the mean cosine
    gap is above 0.05, STOP and review the extraction code before anything else;
  - otherwise use 21.

Models are loaded one at a time (Qwen, then the AV, then the AR), so a 24 GB GPU is enough.

Usage, from the repo root, with the NLA repo cloned somewhere:
  python latam_pilot/layer_test.py --nla-repo ~/natural_language_autoencoders
Writes latam_pilot/layer_test.csv and latam_pilot/layer_test_summary.json.
"""
import argparse
import csv
import gc
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

LAYERS = (20, 21)
WIN_GAP = 0.05
WIN_COUNT = 8


def free_gpu():
    import torch
    gc.collect()
    torch.cuda.empty_cache()


def load_prompts(dataset_path, arm, language, n):
    data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    prompts = []
    for pair in data["pairs"]:
        if language in pair["prompts"]:
            prompts.append({"id": f"{pair['id']}_{arm}_{language}",
                            "keyword": pair["keyword"][f"{arm}_{language}"],
                            "prompt": pair["prompts"][language][arm]})
    return prompts[:n]


def extract_two_layers(prompts, config):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from src.extraction import _build_window, _find_keyword_span

    tok = AutoTokenizer.from_pretrained(config["model"]["qwen_path"])
    model = AutoModelForCausalLM.from_pretrained(
        config["model"]["qwen_path"], torch_dtype=torch.float16, device_map="cuda").eval()
    out = []
    for p in prompts:
        ids = tok.apply_chat_template([{"role": "user", "content": p["prompt"]}], tokenize=True,
                                      add_generation_prompt=True, return_tensors="pt").to("cuda")
        t0, t1 = _find_keyword_span(tok, ids[0].tolist(), p["keyword"])
        assert t0 is not None, f"keyword not found in {p['id']}"
        with torch.no_grad():
            hs = model(input_ids=ids, output_hidden_states=True).hidden_states
        pos = _build_window(t0, t1, ids.shape[1], config["window"]["post_positions"])
        vec = {L: {name: hs[L][0, idx].float().cpu().numpy() for name, idx in pos.items()}
               for L in LAYERS}
        out.append({"id": p["id"], "vec": vec})
    del model
    free_gpu()
    return out


def describe_vectors(extracted, config, temperature):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from src import verbalization as V

    ckpt = V._resolve_local_path(config["model"]["av_checkpoint"])
    meta = V._load_av_config(ckpt)
    tok = AutoTokenizer.from_pretrained(ckpt)
    embed = V._load_embeddings(ckpt)
    base_ids = V._build_base_prompt(meta, tok)
    av = AutoModelForCausalLM.from_pretrained(
        ckpt, torch_dtype=torch.float16, device_map="cuda").eval()
    for e in extracted:
        e["text"] = {}
        for L in LAYERS:
            names, batch = V._build_batch(embed, base_ids, e["vec"][L], meta)
            texts = V._generate_batch(av, tok, batch, 1, temperature,
                                      config["sampling"]["max_new_tokens"])
            e["text"][L] = {n: t[0] for n, t in zip(names, texts)}
    del av
    free_gpu()


def score_with_official_critic(extracted, config, nla_repo):
    import torch
    sys.path.insert(0, str(Path(nla_repo).expanduser()))
    from huggingface_hub import snapshot_download
    from nla_inference import NLACritic

    ar = config["ars"]["ar_checkpoint"]
    path = ar if os.path.isdir(ar) else snapshot_download(repo_id=ar)
    critic = NLACritic(path, device="cuda", dtype=torch.bfloat16)  # asserts value_head.safetensors exists
    rows = []
    for e in extracted:
        for src in LAYERS:
            for name, text in e["text"][src].items():
                _, cos21 = critic.score(text, e["vec"][21][name])
                _, cos20 = critic.score(text, e["vec"][20][name])
                rows.append({"id": e["id"], "source_layer": src, "position": name,
                             "cos_to_hs21": cos21, "cos_to_hs20": cos20, "text": text})
    return rows


def summarize(rows):
    """Decision from the rows. Pure function, tested without a GPU."""
    ids = sorted({r["id"] for r in rows})
    per = {}
    for i in ids:
        for src in LAYERS:
            vals = [r["cos_to_hs21"] for r in rows if r["id"] == i and r["source_layer"] == src]
            per[(i, src)] = float(np.mean(vals))
    gaps = [per[(i, 21)] - per[(i, 20)] for i in ids]  # > 0 means [21] reconstructs hs[21] better
    wins20 = sum(1 for g in gaps if g < 0)
    wins21 = sum(1 for g in gaps if g > 0)
    mean_gap = float(np.mean(gaps))
    if wins20 >= WIN_COUNT and -mean_gap > WIN_GAP:
        decision = ("STOP: descriptions made from hidden_states[20] reconstruct better. "
                    "Review the extraction code before running anything else.")
    else:
        decision = "USE 21: set model.layer to 21 in config.yaml (hidden_states[21] = output of block 20)."
    return {"n_prompts": len(ids), "wins_for_21": wins21, "wins_for_20": wins20,
            "mean_cos_gap_21_minus_20": mean_gap,
            "mean_cos_source21": float(np.mean([per[(i, 21)] for i in ids])),
            "mean_cos_source20": float(np.mean([per[(i, 20)] for i in ids])),
            "decision": decision}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dataset", default="dataset/minimal_pairs_mx_ar.json")
    ap.add_argument("--arm", default="cue")
    ap.add_argument("--language", default="es")
    ap.add_argument("--n-prompts", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=0.01)
    ap.add_argument("--nla-repo", required=True, help="path to a clone of kitft/natural_language_autoencoders")
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()

    import yaml
    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    prompts = load_prompts(args.dataset, args.arm, args.language, args.n_prompts)
    print(f"[layer_test] {len(prompts)} prompts from {args.dataset}")

    extracted = extract_two_layers(prompts, config)
    describe_vectors(extracted, config, args.temperature)
    rows = score_with_official_critic(extracted, config, args.nla_repo)

    out_dir = Path(args.out_dir)
    with open(out_dir / "layer_test.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = summarize(rows)
    (out_dir / "layer_test_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
