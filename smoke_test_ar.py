#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_test_ar.py -- empirically validates the _load_ar / _reconstruct
hypothesis in src/ars.py BEFORE trusting it for the full pipeline.

The hypothesis (from inspecting the checkpoint): the AR has no separate
reconstruction head; its own final hidden state at the suffix-anchored
last token IS the reconstruction. This script tests that hypothesis the
same way we validated the AV all weekend: run it on a REAL explanation
whose corresponding REAL activation we already have (from
results_stage1.json), and check whether the reconstruction is
meaningfully closer to the real vector than to an unrelated one.

If MSE(real, reconstruction_of_matching_explanation) is clearly smaller
than MSE(real, reconstruction_of_UNRELATED_explanation), the AR is doing
something sensible and the hypothesis holds. If both are similar, the
"no head" hypothesis is probably wrong and needs revisiting.
"""

import json
import sys

import numpy as np

sys.path.insert(0, ".")
from src.ars import _load_ar, _reconstruct, AR_PROMPT_TEMPLATE, CRITIC_SUFFIX_IDS


def main():
    with open("results/results_stage1.json") as f:
        items = json.load(f)
    with open("results/results_stage2.json") as f:
        items_with_explanations = json.load(f)

    # use the N02 (TransMilenio) item we already validated all weekend
    item1 = next(it for it in items if it["id"] == "N02_cue_es")
    item2 = next(it for it in items_with_explanations if it["id"] == "N02_cue_es")
    real_vector = np.asarray(item1["vectors"]["tw"])
    matching_explanation = item2["explanations"]["tw"][0]

    # an unrelated explanation, from a totally different item/position, as
    # a negative control -- reconstruction should NOT match real_vector well
    other_item = next(it for it in items_with_explanations if it["id"] != "N02_cue_es")
    unrelated_explanation = other_item["explanations"]["tw-1"][0]

    print("Loading AR ...")
    ar_model, tokenizer = _load_ar("kitft/nla-qwen2.5-7b-L20-ar")

    print(f"\nAR prompt template: {AR_PROMPT_TEMPLATE!r}")
    print(f"Expected suffix token ids: {CRITIC_SUFFIX_IDS}")

    print("\nReconstructing from the MATCHING explanation ...")
    h_hat_matching = _reconstruct(ar_model, tokenizer, matching_explanation,
                                  CRITIC_SUFFIX_IDS)

    print("Reconstructing from an UNRELATED explanation ...")
    h_hat_unrelated = _reconstruct(ar_model, tokenizer, unrelated_explanation,
                                   CRITIC_SUFFIX_IDS)

    mse_matching = float(np.mean((real_vector - h_hat_matching) ** 2))
    mse_unrelated = float(np.mean((real_vector - h_hat_unrelated) ** 2))

    print(f"\nReal vector norm: {np.linalg.norm(real_vector):.3f}")
    print(f"Reconstruction (matching) norm: {np.linalg.norm(h_hat_matching):.3f}")
    print(f"Reconstruction (unrelated) norm: {np.linalg.norm(h_hat_unrelated):.3f}")
    print(f"\nMSE(real, matching reconstruction):   {mse_matching:.4f}")
    print(f"MSE(real, unrelated reconstruction):  {mse_unrelated:.4f}")

    if mse_matching < mse_unrelated:
        ratio = mse_unrelated / max(mse_matching, 1e-9)
        print(f"\nHYPOTHESIS SUPPORTED: the matching explanation reconstructs "
             f"{ratio:.2f}x closer to the real vector than the unrelated one.")
        print("Safe to proceed with the full ARS pipeline.")
    else:
        print("\nHYPOTHESIS NOT SUPPORTED: the matching explanation does NOT "
             "reconstruct meaningfully better than an unrelated one.")
        print("The 'no separate head' assumption is likely wrong -- "
             "do not trust ARS results until this is resolved.")


if __name__ == "__main__":
    main()
