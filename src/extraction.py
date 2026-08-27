# src/extraction.py
"""
Stage 1: activation extraction.

What it does: for each prompt in the dataset, runs the text through Qwen
ONCE (forward pass, no generation) and saves the activation vector of the
configured layer at 7 positions around the keyword:

    tw-1 (right before the keyword) -> tw (the keyword) -> tw+1 ... tw+5

Why tw-1 is special: a transformer is causal, so the activation at that
position CANNOT contain any information about the keyword yet (the model
hasn't read it). That makes it a clean "before" reference photo.

This version is deliberately simple: a plain for-loop, no parallelism.
With 120 prompts and a single forward pass per prompt, this stage is fast
(minutes) even on a modest single GPU -- not worth complicating.
"""

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def _find_keyword_span(tokenizer, full_ids, keyword):
    """Finds which tokens the keyword falls on WITHIN THE ACTUAL SEQUENCE
    that gets passed to the model (full_ids, already chat-templated --
    system message, <|im_start|> markers, etc.).

    HISTORICAL BUG FIXED HERE: the earlier version tokenized the user
    prompt IN ISOLATION (without the template), computed a position over
    that short sequence, and used that number directly as an index into
    the full tensor -- but the real tensor has ~12 tokens of system
    message ("You are Qwen... You are a helpful assistant.") BEFORE the
    user's text even starts. That meant extracting the activation of the
    word "assistant" from the system prompt, never the user's real
    keyword. Now the search happens directly on full_ids, the exact same
    sequence given to the model.

    We can't search for the keyword as if it were a single token, since
    the tokenizer may split it into several subtokens (e.g. "TransMilenio"
    isn't necessarily one token). So the search is done by CHARACTERS:
    each token is decoded, the full text is reconstructed, the keyword's
    substring is located there, and that character position is translated
    back into token indices.
    """
    token_texts = [tokenizer.decode([tid]) for tid in full_ids]

    char_pos = 0
    token_start_char = []
    for t in token_texts:
        token_start_char.append(char_pos)
        char_pos += len(t)

    reconstructed_text = "".join(token_texts)
    start_idx = reconstructed_text.find(keyword)
    if start_idx == -1:
        return None, None  # keyword not found -- flagged and skipped

    end_idx = start_idx + len(keyword)

    t_start = 0
    for i, c in enumerate(token_start_char):
        if c <= start_idx:
            t_start = i
    t_end = t_start
    for i, c in enumerate(token_start_char):
        if c < end_idx:
            t_end = i

    return t_start, t_end


def _build_window(t_start, t_end, total_tokens, post_positions):
    """Builds the {position_name: token_index} dictionary.

    If the keyword sits too close to the end of the prompt and there
    aren't 5 tokens left after it, the window is trimmed (flagged, never
    invented).
    """
    positions = {}
    if t_start - 1 >= 0:
        positions["tw-1"] = t_start - 1
    positions["tw"] = t_end

    available_tokens = min(post_positions, total_tokens - 1 - t_end)
    for k in range(1, available_tokens + 1):
        positions[f"tw+{k}"] = t_end + k

    return positions


def extract_activations(items, config):
    """Entry point for this stage.

    items: list of dicts with at least {id, prompt, keyword, ...}
           (already flattened from dataset/minimal_pairs.json by main.py)
    config: the dict loaded from config.yaml

    Returns: list of dicts, one per item, with their activation vectors
    (numpy arrays) and window metadata.

    IMPORTANT -- extraction mechanism: uses output_hidden_states=True and
    takes hidden_states[layer], EXACTLY as shown in the official NLA repo
    recipe (README, minimal extraction example). This is deliberately
    different from hooking model.model.layers[layer]: hidden_states[0] is
    the embedding BEFORE any layer, so hidden_states[20] means "after 20
    full layers" -- while model.model.layers[20] (0-indexed) is the output
    of layer NUMBER 21. These are two conventions that differ by exactly
    one layer. The first implementation of this file used a hook on
    layers[layer], which systematically read one layer deeper than what
    the AV was trained to interpret -- one of the confirmed root causes
    from this weekend's debugging.
    """
    print(f"[extraction] loading {config['model']['qwen_path']} ...")
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["qwen_path"])
    model = AutoModelForCausalLM.from_pretrained(
        config["model"]["qwen_path"],
        torch_dtype=torch.float16,
        device_map="cuda",
    )
    model.eval()

    layer = config["model"]["layer"]
    post_positions = config["window"]["post_positions"]

    results = []
    for i, item in enumerate(items, 1):
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": item["prompt"]}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to("cuda")

        t_start, t_end = _find_keyword_span(tokenizer, ids[0].tolist(), item["keyword"])
        if t_start is None:
            print(f"  [{i}/{len(items)}] {item['id']}: keyword not found -> SKIP")
            continue

        with torch.no_grad():
            model_output = model(input_ids=ids, output_hidden_states=True)
        # hidden_states[layer]: after `layer` full transformer blocks --
        # index 0 = raw embedding, before any layer. [0] at the end
        # drops the batch dimension.
        layer_activation = model_output.hidden_states[layer][0].float().cpu()

        positions = _build_window(t_start, t_end, ids.shape[1], post_positions)
        vectors = {name: layer_activation[idx].numpy()
                  for name, idx in positions.items()}

        results.append({**item, "positions_idx": positions, "vectors": vectors})

        if i % 20 == 0 or i == len(items):
            print(f"  [{i}/{len(items)}] processed")

    print(f"[extraction] done: {len(results)}/{len(items)} prompts with activations.")
    return results


# Note for the future: if the dataset grew to hundreds/thousands of
# prompts, the natural change here is NOT parallelism -- it's simply
# writing each `vectors` entry to disk as soon as it's computed (instead
# of accumulating everything in the `results` list), to allow resuming if
# the process is interrupted. With 120 prompts, keeping it in memory is
# simpler and the extra complexity isn't worth it yet.
