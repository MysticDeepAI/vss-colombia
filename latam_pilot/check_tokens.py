"""Token check for minimal pairs (Spanish arm), done the way the pipeline does it.

For each pair and arm: apply Qwen's chat template, then find the keyword with the
same character search as src/extraction.py::_find_keyword_span. Reports:
  - whether the keyword is found (a keyword that is not found is skipped by the run);
  - the keyword's tokens in cue and neutral, and the gap between them;
  - whether the token before the keyword (tw-1) and the 5 tokens after it (tw+1..tw+5)
    are the same in cue and neutral;
  - whether the window is cut short at the end of the prompt.

Needs only the tokenizer (pip install transformers jinja2; no torch, no GPU).
Usage, from the repo root:
  python latam_pilot/check_tokens.py dataset/minimal_pairs_mx_ar.json
"""
import json
import sys

from transformers import AutoTokenizer

MODEL = "Qwen/Qwen2.5-7B-Instruct"
POST = 5  # config window.post_positions


def find_keyword_span(tokenizer, full_ids, keyword):
    # same logic as src/extraction.py::_find_keyword_span
    token_texts = [tokenizer.decode([tid]) for tid in full_ids]
    char_pos = 0
    token_start_char = []
    for t in token_texts:
        token_start_char.append(char_pos)
        char_pos += len(t)
    reconstructed_text = "".join(token_texts)
    start_idx = reconstructed_text.find(keyword)
    if start_idx == -1:
        return None, None
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


def encode(tok, prompt):
    out = tok.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=True, add_generation_prompt=True,
    )
    if hasattr(out, "keys"):
        out = out["input_ids"]
    if out and isinstance(out[0], list):
        out = out[0]
    return list(out)


def check_arm(tok, pair, arm, lang):
    kw = pair["keyword"][f"{arm}_{lang}"]
    ids = encode(tok, pair["prompts"][lang][arm])
    s, e = find_keyword_span(tok, ids, kw)
    if s is None:
        return None
    dec = lambda i: tok.decode([ids[i]])
    return {
        "kw": kw,
        "n_kw": e - s + 1,
        "kw_toks": [dec(i) for i in range(s, e + 1)],
        "before": dec(s - 1),
        "before_id": ids[s - 1],
        "post_ids": ids[e + 1:e + 1 + POST],
        "post_toks": [dec(i) for i in range(e + 1, min(e + 1 + POST, len(ids)))],
        "n_post": min(POST, len(ids) - 1 - e),
        "total": len(ids),
    }


def main(path, lang="es"):
    sys.stdout.reconfigure(encoding="utf-8")
    tok = AutoTokenizer.from_pretrained(MODEL)
    data = json.load(open(path, encoding="utf-8"))
    problems = 0
    print(f"tokenizer: {MODEL}   dataset: {path}   language: {lang}\n")
    for pair in data["pairs"]:
        c = check_arm(tok, pair, "cue", lang)
        n = check_arm(tok, pair, "neutral", lang)
        flags = []
        if c is None or n is None:
            flags.append("KEYWORD NOT FOUND in " + ("cue" if c is None else "neutral"))
        else:
            if c["post_ids"] != n["post_ids"]:
                flags.append("tokens after keyword DIFFER")
            if c["before_id"] != n["before_id"]:
                flags.append("token before keyword DIFFERS")
            if c["n_post"] < POST or n["n_post"] < POST:
                flags.append("window cut short")
        problems += bool(flags)
        print(f"== {pair['id']}  {'OK' if not flags else 'PROBLEM: ' + '; '.join(flags)}")
        for arm, r in (("cue", c), ("neutral", n)):
            if r is None:
                print(f"   {arm:8s} keyword not found")
                continue
            print(f"   {arm:8s} {r['kw']!r:24s} {r['n_kw']} tok {r['kw_toks']}  | total {r['total']}")
        if c and n:
            print(f"   before keyword: {c['before']!r}   after keyword (tw+1..tw+5): {c['post_toks']}")
            print(f"   keyword token gap (cue - neutral): {c['n_kw'] - n['n_kw']:+d}")
    print(f"\n{len(data['pairs'])} pairs checked, {problems} with problems.")
    return problems


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
