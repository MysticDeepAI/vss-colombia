#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnose_ar_suffix.py -- decodes critic_suffix_ids (from nla_meta.yaml)
and our current AR_PROMPT_TEMPLATE's tail into readable text, side by
side, to find the exact formatting mismatch instead of guessing again.
"""

import sys

sys.path.insert(0, ".")
from src.ars import AR_PROMPT_TEMPLATE
from src.verbalization import _load_av_config, _resolve_local_path
from transformers import AutoTokenizer

CRITIC_SUFFIX_IDS = [1318, 29, 366, 1708, 29]


def main():
    path = _resolve_local_path("kitft/nla-qwen2.5-7b-L20-ar")
    tokenizer = AutoTokenizer.from_pretrained(path)

    print("=== What critic_suffix_ids actually decodes to ===")
    for tid in CRITIC_SUFFIX_IDS:
        print(f"  {tid}: {tokenizer.decode([tid])!r}")
    full_suffix_text = tokenizer.decode(CRITIC_SUFFIX_IDS)
    print(f"  Full suffix as text: {full_suffix_text!r}")

    print("\n=== What our current template produces ===")
    prompt = AR_PROMPT_TEMPLATE.format(explanation="EXAMPLE_EXPLANATION_TEXT")
    ids = tokenizer(prompt, return_tensors="pt").input_ids[0].tolist()
    tail = ids[-5:]
    print(f"  Template: {AR_PROMPT_TEMPLATE!r}")
    print(f"  Full prompt (repr): {prompt!r}")
    print(f"  Last 5 token ids: {tail}")
    for tid in tail:
        print(f"    {tid}: {tokenizer.decode([tid])!r}")

    print("\n=== nla_meta.yaml's own prompt_templates.ar (ground truth) ===")
    meta = _load_av_config(path)
    print(repr(meta["prompt_templates"]["ar"]))


if __name__ == "__main__":
    main()
