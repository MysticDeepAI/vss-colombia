# src/ars.py
"""
Stage 4 (optional): ARS -- AR-verified salience.

Uses the Reconstructor (AR) as a causal verifier of the grader's positive
labels. For every explanation the grader flagged as "mentions_target"
with a valid quote, removes just that claim and asks the AR to reconstruct
the activation from both versions. If removing the claim hurts
reconstruction (higher MSE against the REAL activation from Stage 1),
the claim was capturing genuine information -- not confabulation.

ARS_t(a) = MSE(h, AR(z_without_claim)) - MSE(h, AR(z_original))

Per the NLA paper's own finding: "removing true claims from AV
explanations hurts reconstruction more than removing false claims."
A large positive ARS is evidence the mention was real.

Scoring goes through the official NLACritic (see load_critic), so the
MSE is the direction-only 2(1 - cos) the reconstructor was trained on.
"""

import re

import numpy as np

# From nla_meta.yaml's prompt_templates.ar, VERBATIM (confirmed via
# diagnose_ar_suffix.py -- single spaces, no newlines):
AR_PROMPT_TEMPLATE = "Summary of the following text: <text>{explanation}</text> <summary>"

# From nla_meta.yaml's tokens.critic_suffix_ids -- the AR is
# suffix-anchored (no marker-token scan): it reads the last token of the
# prompt, and this exact tail confirms the prompt is formatted the way
# training expected.
CRITIC_SUFFIX_IDS = [1318, 29, 366, 1708, 29]


def _remove_claim(explanation, quote):
    """Removes ONLY the exact quoted substring from `explanation`, not the
    whole sentence containing it.

    Design decision (caught by testing this function): removing the full
    sentence also deletes any OTHER genuine claim that happens to share
    that sentence with the quoted one (e.g. "...mentions TransMilenio,
    suggesting a Colombian context." -- sentence-level removal would also
    delete "TransMilenio," which may itself be real signal, not
    confabulation). Surgical substring removal keeps the ablation isolated
    to exactly the claim the grader cited, which is what ARS is supposed
    to test."""
    edited = explanation.replace(quote, "")
    edited = re.sub(r"\s{2,}", " ", edited)          # collapse double spaces
    edited = re.sub(r"\s+([.,;:])", r"\1", edited)   # fix " ," -> ","
    return edited.strip()


def load_critic(checkpoint_id, nla_repo):
    """Loads the official reconstructor wrapper (NLACritic from the NLA repo's
    nla_inference.py), the same one latam_pilot/layer_test.py uses.

    The first version of this module loaded the AR as a plain causal LM and
    read hidden_states[20] at the last token. That skipped two parts of the
    trained reconstructor: the value head (value_head.safetensors, a d x d
    linear map on top of the last block) and the direction-only distance
    (both vectors scaled to L2 = sqrt(d) before the MSE, so MSE = 2(1 - cos)).
    NLACritic does both, so ARS now uses it.
    """
    import os
    import sys
    from pathlib import Path

    import torch
    from huggingface_hub import snapshot_download

    sys.path.insert(0, str(Path(nla_repo).expanduser()))
    from nla_inference import NLACritic

    path = checkpoint_id if os.path.isdir(checkpoint_id) else snapshot_download(repo_id=checkpoint_id)
    return NLACritic(path, device="cuda", dtype=torch.bfloat16)


def _control_removal(explanation, quote, seed):
    """Length control: removes a span of the same length as `quote` that does
    NOT overlap the quote, starting at a word boundary, chosen with a fixed
    seed. Returns None if the text has no such span.

    Removing the quoted claim shortens the text; part of any change in MSE
    could come from removing content at all, not from removing that claim.
    The control removes the same amount of other text, so
    ARS - ARS_control isolates the claim."""
    import random

    L = len(quote)
    q0 = explanation.find(quote)
    if q0 < 0 or L == 0:
        return None
    q1 = q0 + L
    starts = [k for k in range(len(explanation) - L + 1)
              if (k == 0 or explanation[k - 1] == " ")
              and (k + L <= q0 or k >= q1)]
    if not starts:
        return None
    k = random.Random(seed).choice(starts)
    edited = explanation[:k] + explanation[k + L:]
    edited = re.sub(r"\s{2,}", " ", edited)
    edited = re.sub(r"\s+([.,;:])", r"\1", edited)
    return edited.strip()


def compute_ars_for_item(item, score_fn):
    """Adds ARS fields to every grading that has mentions_target=True and a
    verified quote. Mutates `item` in place. Returns how many were scored.

    score_fn(text, real_vector) -> direction MSE (NLACritic.score(...)[0]);
    real_vector is the stored extraction vector (hidden_states[21] with the
    current config, the reconstructor's target space).

      ars          = MSE(without the quote)        - MSE(original)
      ars_control  = MSE(without a same-length span elsewhere) - MSE(original)
      ars_net      = ars - ars_control

    Positive ars means the quoted claim helped reconstruct the activation;
    positive ars_net means it helped more than removing the same amount of
    other text. This is our own version built on the official critic, not an
    ARS defined by the NLA authors."""
    import zlib

    n = 0
    for pos, gradings in item["gradings"].items():
        real_vector = np.asarray(item["vectors"][pos], dtype=np.float32)
        for j, g in enumerate(gradings):
            # Defensive check: requires a truthy quote, guarding against
            # already-generated Stage 3 data with quote=None + quote_verified=True.
            if not (g.get("mentions_target") and g.get("quote_verified") and g.get("quote")):
                continue
            text = item["explanations"][pos][j]
            quote = g["quote"]
            mse_original = float(score_fn(text, real_vector))
            mse_edited = float(score_fn(_remove_claim(text, quote), real_vector))
            g["ars_mse_original"] = mse_original
            g["ars_mse_edited"] = mse_edited
            g["ars"] = mse_edited - mse_original

            seed = zlib.crc32(f"{item.get('id', '')}|{pos}|{j}".encode())
            control_text = _control_removal(text, quote, seed)
            if control_text is not None:
                mse_control = float(score_fn(control_text, real_vector))
                g["ars_mse_control"] = mse_control
                g["ars_control"] = mse_control - mse_original
                g["ars_net"] = g["ars"] - g["ars_control"]
            n += 1
    return n


# --- Legacy loader, kept only for smoke_test_ar.py and diagnose_ar_suffix.py -----
# It skips the value head and the direction-only MSE; the pipeline no longer uses it.

def _load_ar(checkpoint_id):
    """Loads the AR (Reconstructor).

    Confirmed from inspecting the actual checkpoint (kitft/nla-qwen2.5-7b-L20-ar):
      - 21 layers present (indices 0-20), matching extraction_layer_index=20.
      - The only large weight matrix is model.embed_tokens.weight
        (152064, 3584) -- the standard Qwen vocabulary table. NO separate
        reconstruction head exists anywhere in the checkpoint.
      - d_model (3584) equals Qwen2.5-7B's hidden_size exactly.

    Conclusion: there is no extra learned affine head to load. The
    reconstruction is simply the truncated model's own final hidden state
    at the suffix-anchored last token position.
    """
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import os
    import torch

    path = checkpoint_id if os.path.isdir(checkpoint_id) else snapshot_download(repo_id=checkpoint_id)
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(
        path, torch_dtype=torch.float16, device_map="cuda")
    model.eval()
    return model, tokenizer


def _reconstruct(ar_model, tokenizer, explanation_text, critic_suffix_ids, layer_index=20):
    """Runs one explanation through the AR and returns the reconstructed
    activation vector (numpy, [d_model]).

    Uses hidden_states[layer_index] (the RAW output of decoder layer
    `layer_index`), NOT hidden_states[-1] -- the final RMSNorm
    (model.norm) that HF applies to produce hidden_states[-1] is
    RANDOMLY INITIALIZED in this checkpoint (confirmed by the loader's
    own warning), so using it would corrupt the reconstruction.
    """
    import torch

    prompt = AR_PROMPT_TEMPLATE.format(explanation=explanation_text)
    ids = tokenizer(prompt, return_tensors="pt").input_ids.to(ar_model.device)

    tail = ids[0, -len(critic_suffix_ids):].tolist()
    assert tail == critic_suffix_ids, (
        f"AR prompt does not end in the expected suffix. "
        f"Got {tail}, expected {critic_suffix_ids}. "
        f"Check AR_PROMPT_TEMPLATE against nla_meta.yaml's prompt_templates.ar.")

    with torch.no_grad():
        out = ar_model(input_ids=ids, output_hidden_states=True)
    last_token_hidden = out.hidden_states[layer_index][0, -1]  # raw layer output, last token
    return last_token_hidden.float().cpu().numpy()


def calibrate_threshold(items, percentile=90):
    """Calibrates tau as the Nth percentile of ARS values computed on the
    NEUTRAL arm (where, by design, there should be no real Colombian
    content -- any 'necessity' the AR assigns there is noise floor, not
    signal)."""
    neutral_ars = [
        g["ars"]
        for item in items if item["arm"] == "neutral"
        for gradings in item["gradings"].values()
        for g in gradings if "ars" in g
    ]
    if not neutral_ars:
        return None
    return float(np.percentile(neutral_ars, percentile))


def apply_ars_filter(items, tau):
    """Adds 'mentions_target_ars_verified': label survives only if
    ars > tau. Leaves the original grader label untouched (both are kept
    for the sensitivity analysis)."""
    for item in items:
        for gradings in item["gradings"].values():
            for g in gradings:
                if "ars" in g:
                    g["mentions_target_ars_verified"] = g["ars"] > tau
