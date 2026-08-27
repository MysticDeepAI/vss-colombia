# src/ars.py
"""
Stage 4 (optional): ARS -- AR-verified salience.

Uses the Reconstructor (AR) as a causal verifier of the grader's positive
labels. For every explanation the grader flagged as "mentions_colombia"
with a valid quote, removes just that claim and asks the AR to reconstruct
the activation from both versions. If removing the claim hurts
reconstruction (higher MSE against the REAL activation from Stage 1),
the claim was capturing genuine information -- not confabulation.

ARS_t(a) = MSE(h, AR(z_without_claim)) - MSE(h, AR(z_original))

Per the NLA paper's own finding: "removing true claims from AV
explanations hurts reconstruction more than removing false claims."
A large positive ARS is evidence the mention was real.

Empirically validated against a real Stage-1 vector (smoke_test_ar.py):
the matching explanation reconstructs ~2.8x closer to the real vector
than an unrelated one, confirming the loading approach below is sound.
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


def compute_ars_for_item(item, ar_model, tokenizer, critic_suffix_ids):
    """Adds an 'ars' field to every grading that has mentions_colombia=True
    and a verified quote. Mutates `item` in place."""
    for pos, gradings in item["gradings"].items():
        real_vector = np.asarray(item["vectors"][pos])
        for j, g in enumerate(gradings):
            # Defensive check: requires a truthy quote, guarding against
            # already-generated Stage 3 data with quote=None + quote_verified=True.
            if not (g.get("mentions_colombia") and g.get("quote_verified") and g.get("quote")):
                continue
            text = item["explanations"][pos][j]
            quote = g["quote"]
            edited_text = _remove_claim(text, quote)

            h_hat_original = _reconstruct(ar_model, tokenizer, text, critic_suffix_ids)
            h_hat_edited = _reconstruct(ar_model, tokenizer, edited_text, critic_suffix_ids)

            mse_original = float(np.mean((real_vector - h_hat_original) ** 2))
            mse_edited = float(np.mean((real_vector - h_hat_edited) ** 2))
            g["ars"] = mse_edited - mse_original


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
    """Adds 'mentions_colombia_ars_verified': label survives only if
    ars > tau. Leaves the original grader label untouched (both are kept
    for the sensitivity analysis)."""
    for item in items:
        for gradings in item["gradings"].values():
            for g in gradings:
                if "ars" in g:
                    g["mentions_colombia_ars_verified"] = g["ars"] > tau
