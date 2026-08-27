#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_ar_checkpoint.py -- run this FIRST, before trusting any ARS code.

Lesson from this weekend: never assume how a checkpoint is structured.
This script inspects kitft/nla-qwen2.5-7b-L20-ar and prints everything
needed to write a correct loader: the config (how many layers does it
actually keep?), the nla_meta.yaml (is there an AR-specific prompt
template? a reconstruction head key?), and the safetensors key names
(is there a separate "value_head" / "critic_head" tensor alongside the
truncated transformer weights?).

Run this on the server (needs network access to fetch the checkpoint,
no GPU needed for just inspecting metadata).
"""

import json
import os

from huggingface_hub import snapshot_download
from safetensors import safe_open

CHECKPOINT_ID = "kitft/nla-qwen2.5-7b-L20-ar"


def main():
    print(f"Downloading/locating {CHECKPOINT_ID} ...")
    path = snapshot_download(repo_id=CHECKPOINT_ID)
    print(f"Local path: {path}\n")

    print("=== Files in checkpoint ===")
    for f in sorted(os.listdir(path)):
        size = os.path.getsize(os.path.join(path, f))
        print(f"  {f}  ({size:,} bytes)")

    print("\n=== config.json (look for num_hidden_layers) ===")
    with open(os.path.join(path, "config.json")) as f:
        cfg = json.load(f)
    for key in ("num_hidden_layers", "hidden_size", "architectures", "model_type"):
        if key in cfg:
            print(f"  {key}: {cfg[key]}")

    print("\n=== nla_meta.yaml (look for AR prompt template, head info) ===")
    meta_path = os.path.join(path, "nla_meta.yaml")
    if os.path.exists(meta_path):
        import yaml
        with open(meta_path) as f:
            meta = yaml.safe_load(f)
        print(json.dumps(meta, indent=2, default=str))
    else:
        print("  No nla_meta.yaml found in this checkpoint (unexpected -- check manually).")

    print("\n=== safetensors keys (look for anything NOT matching standard Qwen "
          "layer names -- that's likely the reconstruction head) ===")
    index_path = os.path.join(path, "model.safetensors.index.json")
    all_keys = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
        all_keys = list(index["weight_map"].keys())
    else:
        st_files = [f for f in os.listdir(path) if f.endswith(".safetensors")]
        for st_file in st_files:
            with safe_open(os.path.join(path, st_file), framework="pt") as f:
                all_keys.extend(f.keys())

    standard_qwen_patterns = ("model.layers.", "model.embed_tokens", "model.norm",
                              "lm_head")
    non_standard = [k for k in all_keys
                   if not any(p in k for p in standard_qwen_patterns)]
    print(f"  Total keys: {len(all_keys)}")
    print(f"  Non-standard keys (likely the reconstruction head): {non_standard}")

    # highest layer index actually present, to confirm truncation
    layer_indices = set()
    for k in all_keys:
        if "model.layers." in k:
            try:
                idx = int(k.split("model.layers.")[1].split(".")[0])
                layer_indices.add(idx)
            except (ValueError, IndexError):
                pass
    if layer_indices:
        print(f"  Layer indices present: {min(layer_indices)} to {max(layer_indices)} "
             f"({len(layer_indices)} layers total)")


if __name__ == "__main__":
    main()
