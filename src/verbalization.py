# src/verbalization.py
"""
Stage 2: verbalization.

What it does: for each activation vector extracted in Stage 1, asks the AV
(the NLA's "translator") to describe it in words. This is repeated K times
per position because the AV is stochastic (temperature > 0) -- with a
single sample there's no way to tell "the attribute is strongly encoded"
apart from "it just came out this way by chance this time."

Injection recipe: taken directly from the official NLA repo documentation
(kitft/natural_language_autoencoders, docs/inference.md). Three steps:
  1. tokenize the AV's fixed prompt (comes from its nla_meta.yaml, never
     hardcoded)
  2. rescale the vector to the norm the AV expects (injection_scale, also
     from nla_meta.yaml)
  3. replace a marker token's embedding with the rescaled vector, and let
     the AV generate text from there

ON SPEED (batching): unlike verbalization's 7 positions, which all share
the exact same base prompt length, here every explanation to be graded has
a different length, so batching them together requires PADDING (padding
shorter sequences up to the longest one in the batch) and
padding_side="left", the correct convention for batched causal generation.
With this, instead of one generate() call per explanation (4,200 calls),
they're processed in batches of `grader.batch_size` (default 16 -> ~260
calls) -- similar in spirit to Stage 2's batching.

This version is serial (one vector at a time) -- with 840 positions x K=5
= 4,200 calls, it takes several hours on a GPU. This is the "classic and
simple" version requested; if speed becomes necessary later, the natural
change is to move this function behind an inference server (documented
separately, not needed for now).
"""

import os
import re

import torch
import yaml
from huggingface_hub import snapshot_download
from safetensors import safe_open


def _resolve_local_path(checkpoint):
    """Translates a checkpoint identifier into an actual folder on disk.

    `AutoModelForCausalLM.from_pretrained()` knows how to automatically
    resolve an ID like "kitft/nla-qwen2.5-7b-L20-av" against the Hugging
    Face cache -- but here we need to OPEN files by hand (nla_meta.yaml,
    the embedding weights), and for that we need the real path on disk,
    not the repo name.

    If `checkpoint` is already a local folder (e.g. you downloaded it
    separately and put that path in config.yaml), it's used as-is. If it's
    a Hugging Face ID, `snapshot_download` returns the local path -- since
    it's already cached, this is instantaneous and doesn't download
    anything again.
    """
    if os.path.isdir(checkpoint):
        return checkpoint
    return snapshot_download(repo_id=checkpoint)


def _load_av_config(checkpoint_dir):
    """Loads the AV's 'contract': prompt, special token IDs, and scale
    factor. These values are never hardcoded -- if the checkpoint changes,
    this file brings them up to date automatically."""
    with open(f"{checkpoint_dir}/nla_meta.yaml") as f:
        return yaml.safe_load(f)


def _load_embeddings(checkpoint_dir):
    """Loads only the AV's embedding matrix (not the full model). Much
    faster, and it's the only thing we need to build the prompt with the
    injected vector.

    The checkpoint may be sharded across several .safetensors files -- we
    can't assume the embedding lives in the alphabetically first one.
    First we try reading the official index (model.safetensors.index.json),
    which says exactly which shard holds each tensor; if it doesn't exist
    (single-file checkpoint), every .safetensors file is checked in turn
    until the key is found.
    """
    index_path = os.path.join(checkpoint_dir, "model.safetensors.index.json")
    if os.path.exists(index_path):
        import json
        with open(index_path) as f:
            index = json.load(f)
        weight_map = index.get("weight_map", {})
        key = next((k for k in weight_map if "embed_tokens.weight" in k), None)
        if key is None:
            raise RuntimeError(
                "Could not find 'embed_tokens.weight' in the checkpoint index. "
                f"Available keys (sample): {list(weight_map.keys())[:10]}")
        weights_file = weight_map[key]
        with safe_open(os.path.join(checkpoint_dir, weights_file), framework="pt") as f:
            return f.get_tensor(key)

    # no index -> check every .safetensors file in the checkpoint
    files = sorted(f for f in os.listdir(checkpoint_dir) if f.endswith(".safetensors"))
    if not files:
        raise RuntimeError(f"No .safetensors file found in {checkpoint_dir}")

    seen_keys = []
    for file in files:
        with safe_open(os.path.join(checkpoint_dir, file), framework="pt") as f:
            keys = list(f.keys())
            seen_keys.extend(keys)
            key = next((k for k in keys if "embed_tokens.weight" in k), None)
            if key is not None:
                return f.get_tensor(key)

    raise RuntimeError(
        "No key containing 'embed_tokens.weight' was found in any shard of "
        f"{checkpoint_dir}. Sample keys found: {seen_keys[:15]}\n"
        "Manually check the real name of the embedding matrix in this "
        "checkpoint (it might be named differently, e.g. with a submodule prefix).")


def _build_base_prompt(meta, tokenizer):
    """Tokenizes the AV's fixed prompt ONCE -- reused for every call, only
    the injected vector changes each time.

    IMPORTANT: the process is TWO steps (format to a string, then tokenize
    separately), not a single apply_chat_template(tokenize=True).
    Tokenizing directly can align special tokens differently and shift
    where the injection marker token falls -- even if the assert in
    _row_with_injected_vector() doesn't fail (because it still "finds" a
    matching neighbor pattern, just in the wrong place), the vector ends
    up injected at an incorrect position and the AV generates its generic
    filler response instead of reading the real vector. This is the same,
    verified process from the original notebook.
    """
    content = meta["prompt_templates"]["av"].format(
        injection_char=meta["tokens"]["injection_char"])
    fmt_string = tokenizer.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=False, add_generation_prompt=True,
    )
    return tokenizer.encode(fmt_string, add_special_tokens=False)


def _row_with_injected_vector(embed_weights, base_ids, raw_vector, meta):
    """Rescales ONE vector and returns the [T, d] embedding row with that
    vector placed at the marker token's position. This is the piece that
    gets repeated (and stacked) to build the batch."""
    embeds = embed_weights[base_ids].float()  # [T, d]

    v = torch.tensor(raw_vector, dtype=torch.float32)
    scale = meta["extraction"]["injection_scale"]
    scaled_v = v * (scale / v.norm().clamp_min(1e-12))

    injection_tok = meta["tokens"]["injection_token_id"]
    left_neighbor = meta["tokens"]["injection_left_neighbor_id"]
    right_neighbor = meta["tokens"]["injection_right_neighbor_id"]

    found = False
    for p in range(1, len(base_ids) - 1):
        if (base_ids[p] == injection_tok and base_ids[p - 1] == left_neighbor
                and base_ids[p + 1] == right_neighbor):
            embeds[p] = scaled_v
            found = True
            break
    assert found, "Could not find the injection position in the AV prompt."

    return embeds


def _build_batch(embed_weights, base_ids, vectors_by_position, meta):
    """Stacks one row per position into a single [n_positions, T, d]
    tensor. No padding needed: every row comes from the SAME base prompt
    (same length), only the injected vector differs between rows."""
    names = list(vectors_by_position.keys())
    rows = [_row_with_injected_vector(embed_weights, base_ids, vectors_by_position[n], meta)
           for n in names]
    return names, torch.stack(rows, dim=0)  # [n_positions, T, d]


def _generate_batch(av_model, tokenizer, embeds_batch, k, temperature, max_tokens):
    """A single generate() call that produces K samples for EACH row of
    the batch, using num_return_sequences (a standard HF parameter,
    nothing custom). The result comes back grouped by input row: the
    first K sequences belong to row 0, the next K to row 1, etc. -- that's
    how generate() expands the batch internally (each row is repeated K
    times contiguously before sampling)."""
    device = next(av_model.parameters()).device
    dtype = next(av_model.parameters()).dtype
    embeds_batch = embeds_batch.unsqueeze(0) if embeds_batch.dim() == 2 else embeds_batch
    embeds_batch = embeds_batch.to(device=device, dtype=dtype)

    with torch.no_grad():
        output = av_model.generate(
            inputs_embeds=embeds_batch,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            num_return_sequences=k,
            pad_token_id=tokenizer.eos_token_id,
        )

    n_rows = embeds_batch.shape[0]
    output = output.view(n_rows, k, -1)  # [n_positions, k, seq_len]

    texts = []
    for i in range(n_rows):
        samples = []
        for j in range(k):
            text = tokenizer.decode(output[i, j], skip_special_tokens=False)
            m = re.search(r"<explanation>\s*(.*?)\s*</explanation>", text, re.DOTALL)
            samples.append(m.group(1).strip() if m else text)
        texts.append(samples)
    return texts


def verbalize(items_with_activations, config):
    """Entry point for this stage.

    items_with_activations: the output of extraction.extract_activations()
    config: the dict loaded from config.yaml

    Returns: the same list of items, with a new `explanations` field per
    position: {"tw-1": ["text1", "text2", ...], "tw": [...], ...}
    """
    checkpoint_id = config["model"]["av_checkpoint"]
    print(f"[verbalization] loading AV from {checkpoint_id} ...")

    from transformers import AutoModelForCausalLM, AutoTokenizer

    checkpoint = _resolve_local_path(checkpoint_id)
    print(f"  -> resolved local path: {checkpoint}")
    meta = _load_av_config(checkpoint)

    tokenizer = AutoTokenizer.from_pretrained(checkpoint)

    # Early check (same as the original notebook): the injection marker
    # character must tokenize to EXACTLY the expected ID. If this doesn't
    # hold, any later neighbor-pattern search for the injection position
    # can "find" the wrong spot without any later assert catching it --
    # so it's checked here, before building anything.
    test_ids = tokenizer.encode(meta["tokens"]["injection_char"], add_special_tokens=False)
    assert test_ids == [meta["tokens"]["injection_token_id"]], (
        f"The injection character doesn't tokenize to the expected ID: "
        f"got {test_ids}, expected [{meta['tokens']['injection_token_id']}]")

    embed_weights = _load_embeddings(checkpoint)
    base_ids = _build_base_prompt(meta, tokenizer)
    av_model = AutoModelForCausalLM.from_pretrained(
        checkpoint, torch_dtype=torch.float16, device_map="cuda")
    av_model.eval()

    k = config["sampling"]["k_samples"]
    temperature = config["sampling"]["av_temperature"]
    max_tokens = config["sampling"]["max_new_tokens"]
    batch_positions = config["sampling"].get("batch_across_positions", True)

    total_prompts = len(items_with_activations)
    verified_batch_order = False

    for i, item in enumerate(items_with_activations, 1):
        item["explanations"] = {}

        if batch_positions:
            # a single call: the 7 positions x K samples of the entire prompt
            names, batch = _build_batch(embed_weights, base_ids, item["vectors"], meta)
            try:
                texts = _generate_batch(av_model, tokenizer, batch, k, temperature, max_tokens)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                raise RuntimeError(
                    "Not enough VRAM to batch the 7 positions together. "
                    "Set sampling.batch_across_positions: false in config.yaml "
                    "and run again (slower, but uses less memory).")

            # SAFETY CHECK (once, on the first prompt): the output
            # reordering assumes HF groups each row's K samples
            # CONTIGUOUSLY (repeat_interleave). This is documented but not
            # part of the formal public API, so we verify it at runtime
            # instead of trusting it blindly.
            if not verified_batch_order:
                assert len(texts) == len(names) == batch.shape[0], (
                    "The number of output rows doesn't match the input positions "
                    "-- the batch reordering might be wrong. "
                    "Set batch_across_positions: false and report this error.")
                verified_batch_order = True

            for name, samples in zip(names, texts):
                item["explanations"][name] = samples
        else:
            # fallback: one generate() call per position (7 calls per
            # prompt instead of 1), each already with the K samples
            # together -- still faster than the fully serial original.
            for name, vector in item["vectors"].items():
                row = _row_with_injected_vector(embed_weights, base_ids, vector, meta)
                texts = _generate_batch(av_model, tokenizer, row.unsqueeze(0),
                                        k, temperature, max_tokens)
                item["explanations"][name] = texts[0]

        if i % 10 == 0 or i == total_prompts:
            print(f"  [{i}/{total_prompts}] prompts verbalized "
                 f"({i * 7 * k}/{total_prompts * 7 * k} explanations approx.)")

    print("[verbalization] done.")
    return items_with_activations
