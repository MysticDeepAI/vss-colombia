#!/usr/bin/env python3
"""CPU-only checks for the cloud-run changes (no GPU, no network, no API key).

Run from the repo root:  python latam_pilot/test_cloud_patch.py
Covers: per-country grader prompts, the quote audit, the Sonnet 5.5 call shape (with a fake client),
language handling in load_dataset, the metric on the new label, and the layer-test decision rule.
"""
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FAILED = []


def check(name, fn):
    try:
        fn()
        print("PASS ", name)
    except Exception as e:  # noqa: BLE001
        FAILED.append(name)
        print("FAIL ", name, "->", type(e).__name__, e)


def test_prompts_per_country():
    from src.grading import build_prompt
    for target, demonym in (("México", "Mexican"), ("Argentina", "Argentine"), ("Colombia", "Colombian")):
        for rule in ("strict", "lenient"):
            p = build_prompt(target, rule, "The user eats {curly} tacos.")
            assert demonym in p and target in p
            assert "{curly}" in p, "explanation text must pass through untouched"
            assert '"mentions_target"' in p
    assert "does NOT count" in build_prompt("México", "strict", "x")
    assert "Merely repeating" in build_prompt("México", "strict", "x")
    assert "Merely repeating" not in build_prompt("México", "lenient", "x")


def test_parse_and_quote_audit():
    from src.grading import _parse_response
    src = "This suggests a Mexican speaker who eats esquites."
    ok = _parse_response('{"mentions_target": true, "quote": "a Mexican speaker"}', src)
    assert ok["mentions_target"] is True and ok["quote_verified"] is True
    fake = _parse_response('{"mentions_target": true, "quote": "not in the text"}', src)
    assert fake["mentions_target"] is False and fake["quote_verified"] is False
    noquote = _parse_response('{"mentions_target": true, "quote": null}', src)
    assert noquote["mentions_target"] is False
    bad = _parse_response("sorry, no json here", src)
    assert bad["mentions_target"] is None and bad["error"] == "not_parseable"
    fenced = _parse_response('```json\n{"mentions_target": false, "quote": null}\n```', src)
    assert fenced["mentions_target"] is False
    legacy = _parse_response('{"mentions_colombia": true, "quote": "Mexican"}', src)
    assert legacy["mentions_target"] is True and "mentions_colombia" not in legacy
    assert _parse_response("[1, 2]", src)["error"] == "not_parseable"
    # justification before the JSON (seen in 9 of 700 answers of the first MX/AR run)
    prefixed = _parse_response(
        'It says "a Mexican speaker", so it counts.\n\n{"mentions_target": true, "quote": "a Mexican speaker"}', src)
    assert prefixed["mentions_target"] is True and prefixed["quote_verified"] is True
    prefixed_no = _parse_response('Only repeats {the word}.\n{"mentions_target": false, "quote": null}', src)
    assert prefixed_no["mentions_target"] is False


def _fake_anthropic(responder):
    class Msg:
        def create(self, **kw):
            Msg.last = kw
            return responder(kw)

    class Client:
        def __init__(self, **kw):
            self.messages = Msg()
    mod = types.ModuleType("anthropic")
    mod.Anthropic = Client
    mod.Msg = Msg
    return mod


def test_claude_call_shape_and_thinking_block():
    import src.grading as G
    block = lambda t, text=None: types.SimpleNamespace(type=t, text=text)  # noqa: E731

    def responder(kw):
        # a thinking block FIRST, then the text, as adaptive thinking can return
        return types.SimpleNamespace(content=[
            block("thinking"), block("text", '{"mentions_target": true, "quote": "Mexican"}')])

    mod = _fake_anthropic(responder)
    sys.modules["anthropic"] = mod
    items = [{"id": "MX01_cue_es", "group_id": "MX01", "arm": "cue", "language": "es",
              "attribute": "nationality_mx", "target": "México",
              "explanations": {"tw": ["A Mexican person eats here.", "Nothing relevant."],
                               "tw-1": ["Hello."]}}]
    config = {"grader": {"backend": "claude_api", "claude_model": "claude-sonnet-5-5",
                         "keyword_rule": "strict"}}
    out = G.grade(items, config)
    kw = mod.Msg.last
    assert kw["model"] == "claude-sonnet-5-5"
    assert "temperature" not in kw and "top_p" not in kw and "top_k" not in kw
    assert kw["extra_body"]["thinking"] == {"type": "between_tools"}
    assert "México" in kw["messages"][0]["content"] or "Mexican" in kw["messages"][0]["content"]
    g = out[0]["gradings"]["tw"][0]
    assert g["mentions_target"] is True and g["quote_verified"] is True and "raw" in g
    assert out[0]["gradings"]["tw"][1]["mentions_target"] is False  # quote not in that text


def test_api_error_is_retried_then_recorded():
    import src.grading as G
    calls = {"n": 0}

    def responder(kw):
        calls["n"] += 1
        raise RuntimeError("overloaded")

    sys.modules["anthropic"] = _fake_anthropic(responder)
    items = [{"id": "a", "group_id": "MX01", "arm": "cue", "language": "es", "attribute": "nationality_mx",
              "target": "México", "explanations": {"tw": ["x"]}}]
    out = G.grade(items, {"grader": {"backend": "claude_api", "claude_model": "m"}})
    assert calls["n"] == 2  # first try + one retry
    assert out[0]["gradings"]["tw"][0]["mentions_target"] is None
    assert out[0]["gradings"]["tw"][0]["error"].startswith("api_error")


def _stub_heavy_imports():
    """main.py imports the stage modules, which import torch/transformers. On a machine without
    them (a laptop) the dataset test only needs the import to succeed, so stub them."""
    for name in ("torch", "transformers", "huggingface_hub", "safetensors"):
        try:
            __import__(name)
        except ImportError:
            mod = types.ModuleType(name)
            if name == "safetensors":
                mod.safe_open = None
            if name == "huggingface_hub":
                mod.snapshot_download = None
            sys.modules[name] = mod
    for name in ("AutoModelForCausalLM", "AutoTokenizer"):
        if not hasattr(sys.modules["transformers"], name):
            setattr(sys.modules["transformers"], name, object)


def test_load_dataset_languages_and_target():
    _stub_heavy_imports()
    from main import load_dataset
    cfg = {"paths": {"dataset": str(REPO / "dataset/minimal_pairs_mx_ar.json")}}
    items = load_dataset(cfg)
    assert len(items) == 20, len(items)
    assert {i["language"] for i in items} == {"es"}
    assert {i["target"] for i in items if i["group_id"].startswith("MX")} == {"México"}
    assert {i["target"] for i in items if i["group_id"].startswith("AR")} == {"Argentina"}
    cfg2 = {"paths": {"dataset": str(REPO / "dataset/minimal_pairs.json")}}
    old = load_dataset(cfg2)
    assert len(old) == 120 and {i["language"] for i in old} == {"es", "en"}
    assert {i["target"] for i in old} == {"Colombia"}


def test_metric_new_and_legacy_label():
    from src import metric
    cfg = {"window": {"post_positions": 5}}

    def item(arm, key, pre, post):
        pos = ["tw-1", "tw", "tw+1", "tw+2", "tw+3", "tw+4", "tw+5"]
        g = {}
        for p in pos:
            n_yes = pre if p == "tw-1" else post
            g[p] = [{key: True}] * n_yes + [{key: False}] * (5 - n_yes)
        return {"group_id": "MX01", "language": "es", "arm": arm, "attribute": "nationality_mx", "gradings": g}

    for key in ("mentions_target", "mentions_colombia"):
        rows = metric.calculate_D([item("cue", key, 0, 3), item("neutral", key, 0, 1)], cfg)
        assert len(rows) == 1 and abs(rows[0]["D"] - 0.4) < 1e-9, rows


def test_layer_test_decision_rule():
    import layer_test as LT

    def rows(gap_for_21):
        out = []
        for i in range(10):
            for src, base in ((21, 0.60 + gap_for_21), (20, 0.60)):
                out.append({"id": f"P{i}", "source_layer": src, "position": "tw", "cos_to_hs21": base})
        return out
    assert LT.summarize(rows(0.03))["decision"].startswith("USE 21")
    assert LT.summarize(rows(-0.02))["decision"].startswith("USE 21")   # 20 wins but gap below 0.05
    assert LT.summarize(rows(-0.08))["decision"].startswith("STOP")      # 20 wins big on 10/10
    mixed = rows(0.0)
    for r in mixed:
        if r["id"] in ("P0", "P1", "P2") and r["source_layer"] == 20:
            r["cos_to_hs21"] = 0.9
    assert LT.summarize(mixed)["decision"].startswith("USE 21")           # only 3 wins for 20


def test_decide_rule():
    import decide as DC

    def rows(mx, ar):
        out = [{"group_id": f"MX0{i+1}", "language": "es", "D": d} for i, d in enumerate(mx)]
        return out + [{"group_id": f"AR0{i+1}", "language": "es", "D": d} for i, d in enumerate(ar)]
    ok = DC.decide(rows([0.2, 0.3, 0.1, 0.4, 0.2], [0.1, 0.2, 0.3, 0.1, 0.2]))
    assert ok["verdict"] == "SUCCESS" and ok["p_value_exact"] < 0.05, ok
    # strong overall but Argentina has only 2 positives -> PARTIAL
    part = DC.decide(rows([0.5, 0.6, 0.4, 0.5, 0.7], [0.3, 0.4, -0.01, -0.02, 0.0]))
    assert part["verdict"] in ("PARTIAL", "SUCCESS")
    assert DC.decide(rows([0.5, 0.6, 0.4, 0.5, 0.7], [0.3, 0.4, -0.01, -0.02, -0.03]))["verdict"] == "PARTIAL"
    fail = DC.decide(rows([0.1, -0.1, 0.1, -0.1, 0.0], [0.1, -0.1, 0.1, -0.1, 0.0]))
    assert fail["verdict"] == "FAILURE"
    zeros = DC.decide(rows([0, 0, 0, 0, 0.2], [0, 0, 0.1, 0, 0]))
    assert zeros["repeat_with_K10"] is True and zeros["n_zero"] == 8
    assert "# Decision: SUCCESS" in DC.to_markdown(ok)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            check(name, fn)
    print(f"\n{'ALL PASSED' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    sys.exit(1 if FAILED else 0)
